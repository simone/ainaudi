"""
Conversation Orchestrator.

The single conversational entry point. Receives user messages, classifies
intent via LLM tool-calling, routes to specialist agents, enforces policy,
and composes the final response.

Does NOT directly persist data, open/update tickets, or contain deep
business logic. All side effects happen through specialist agents and services.
"""
import logging
from datetime import date
from typing import Optional

from ai_assistant.agents.knowledge import KnowledgeBaseAgent
from ai_assistant.agents.data_capture import DataCaptureAgent
from ai_assistant.agents.ticketing import TicketingAgent
from ai_assistant.models_typed.types import (
    ActionType,
    AgentResponse,
    ConversationContext,
    PolicyVerdict,
    RequestedAction,
)
from ai_assistant.policy.election_guard import ElectionPolicyGuard
from ai_assistant.orchestrator.context import build_user_profile_context

logger = logging.getLogger(__name__)

# Singletons
_knowledge_agent = KnowledgeBaseAgent()
_data_capture_agent = DataCaptureAgent()
_ticketing_agent = TicketingAgent()
_policy_guard = ElectionPolicyGuard()

# Map function names to action types
_FUNCTION_ACTION_MAP = {
    "get_scrutinio_status": ActionType.GET_SCRUTINIO,
    "save_scrutinio_data": ActionType.SAVE_SCRUTINIO,
    "create_incident_report": ActionType.CREATE_INCIDENT,
    "update_incident_report": ActionType.UPDATE_INCIDENT,
}


class ConversationOrchestrator:
    """
    Main orchestrator. Routes user messages to the correct specialist agent
    based on LLM intent classification (via tool/function calling).
    """

    def generate_response(
        self,
        request,
        session,
        message: str,
        attachment_data: Optional[list[dict]] = None,
    ) -> dict:
        """
        Process a user message and return a response.

        This is the main entry point, replacing the old generate_ai_response.

        Args:
            request: HTTP request (for user, META)
            session: ChatSession instance
            message: User message text
            attachment_data: Optional multimodal attachments

        Returns:
            dict compatible with the existing API:
            {
                'answer': str,
                'sources': list,
                'retrieved_docs': int,
                'function_result': dict or None,
                'user_sections_list': list,
            }
        """
        from ai_assistant.tools import all_ai_tools
        from ai_assistant.vertex_service import vertex_ai_service
        from ai_assistant.models import KnowledgeSource
        from django.conf import settings
        from pgvector.django import CosineDistance

        user = request.user

        # 1. Build conversation context
        logger.info(
            "Orchestrator: processing message for session=%d user=%s",
            session.id, user.email,
        )

        history_messages = session.messages.order_by("created_at")
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in history_messages
        ]

        profile_text, user_sections_list = build_user_profile_context(user, session)

        # 2. Retrieve RAG documents
        context_docs_list = []
        try:
            query_embedding = vertex_ai_service.generate_embedding(message)
            context_docs = (
                KnowledgeSource.objects.filter(is_active=True)
                .annotate(distance=CosineDistance("embedding", query_embedding))
                .filter(distance__lte=(1 - settings.RAG_SIMILARITY_THRESHOLD))
                .order_by("distance")[: settings.RAG_TOP_K]
            )
            context_docs_list = list(context_docs)

            if context_docs_list:
                rag_parts = [
                    f"[{doc.source_type}] {doc.title}\n{doc.content[:2000]}"
                    for doc in context_docs_list
                ]
                context_text = profile_text + "\n\n" + "\n\n---\n\n".join(rag_parts)
            else:
                context_text = profile_text
        except Exception as e:
            logger.warning("Orchestrator: RAG retrieval failed: %s", e)
            context_text = profile_text

        logger.info(
            "Orchestrator: context built session=%d profile=%d chars rag_docs=%d history=%d msgs",
            session.id,
            len(profile_text),
            len(context_docs_list),
            len(conversation_history),
        )

        # 3. Call LLM with tools to classify intent
        ai_response = vertex_ai_service.generate_with_tools(
            conversation_history=conversation_history,
            context=context_text,
            tools=all_ai_tools,
            attachments=attachment_data,
        )

        # 4. Route based on LLM response
        if ai_response["function_call"]:
            return self._handle_function_call(
                ai_response["function_call"],
                session=session,
                request=request,
                user_sections_list=user_sections_list,
            )
        else:
            # Guard: never return 🤷 in the middle of a conversation
            content = (ai_response.get("content") or "").strip()
            if content == "🤷" and len(conversation_history) > 2:
                logger.warning(
                    "Orchestrator: blocked 🤷 in active conversation (history=%d msgs), retrying",
                    len(conversation_history),
                )
                # Retry with explicit instruction appended to context
                retry_context = (
                    context_text
                    + "\n\nIMPORTANTE: NON rispondere con 🤷. "
                    "Questa e una conversazione attiva. "
                    "Rispondi nel merito del messaggio dell'utente, "
                    "anche se non hai documenti pertinenti. "
                    "Se non puoi eseguire l'azione richiesta, spiega perche."
                )
                retry_response = vertex_ai_service.generate_with_tools(
                    conversation_history=conversation_history,
                    context=retry_context,
                    tools=all_ai_tools,
                    attachments=attachment_data,
                )
                if retry_response.get("content") and retry_response["content"].strip() != "🤷":
                    ai_response = retry_response
                    logger.info("Orchestrator: retry succeeded, got meaningful response")
                else:
                    # Fallback: generic contextual response
                    ai_response["content"] = (
                        "Non ho capito bene. Puoi riformulare la domanda? "
                        "Sono qui per aiutarti con le procedure elettorali, "
                        "lo scrutinio e le segnalazioni."
                    )
                    logger.info("Orchestrator: retry also returned 🤷, using fallback")

            # Text response = knowledge/conversational intent
            logger.info("Orchestrator: routing to text response (knowledge/conversational)")
            return self._build_text_response(
                ai_response, context_docs_list, user_sections_list
            )

    def _handle_function_call(
        self,
        function_call: dict,
        session,
        request,
        user_sections_list: list,
    ) -> dict:
        """Route a function call to the appropriate specialist agent."""
        function_name = function_call["name"]
        function_args = function_call["args"]
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")

        logger.info(
            "Orchestrator: function_call=%s routing to specialist agent",
            function_name,
        )

        action_type = _FUNCTION_ACTION_MAP.get(function_name)
        if not action_type:
            logger.warning("Orchestrator: unknown function %s", function_name)
            return {
                "answer": f"Funzione sconosciuta: {function_name}",
                "sources": [],
                "retrieved_docs": 0,
                "function_result": {"message": f"Funzione sconosciuta: {function_name}", "data": None},
                "user_sections_list": user_sections_list,
            }

        # Build action for policy evaluation
        action = RequestedAction(action_type=action_type, args=function_args)

        # Get election dates for policy evaluation
        election_start, election_end = self._get_election_dates()

        # Evaluate policy
        payload = None
        if action_type == ActionType.SAVE_SCRUTINIO:
            payload = DataCaptureAgent.parse_payload(function_args)

        policy_decision = _policy_guard.evaluate(
            action=action,
            election_start=election_start,
            election_end=election_end,
            payload=payload,
        )

        logger.info(
            "Orchestrator: policy verdict=%s for action=%s",
            policy_decision.verdict.value,
            action_type.value,
        )

        # Route to specialist agent
        agent_response = self._dispatch_to_agent(
            action_type=action_type,
            args=function_args,
            session=session,
            user=user,
            ip_address=ip_address,
            policy_decision=policy_decision,
            user_sections_list=user_sections_list,
        )

        return {
            "answer": agent_response.answer,
            "sources": agent_response.sources,
            "retrieved_docs": agent_response.retrieved_docs,
            "function_result": agent_response.function_result,
            "user_sections_list": user_sections_list,
        }

    def _dispatch_to_agent(
        self,
        action_type: ActionType,
        args: dict,
        session,
        user,
        ip_address: str,
        policy_decision,
        user_sections_list: list,
    ) -> AgentResponse:
        """Dispatch to the correct specialist agent."""

        if action_type == ActionType.GET_SCRUTINIO:
            return _data_capture_agent.handle_get_status(
                args, user, user_sections_list
            )

        if action_type == ActionType.SAVE_SCRUTINIO:
            return _data_capture_agent.handle_save(
                args, session, user, ip_address,
                policy_decision, user_sections_list,
            )

        if action_type == ActionType.CREATE_INCIDENT:
            return _ticketing_agent.handle_create(
                args, session, user,
                policy_decision, user_sections_list,
            )

        if action_type == ActionType.UPDATE_INCIDENT:
            return _ticketing_agent.handle_update(
                args, session, user,
                policy_decision, user_sections_list,
            )

        return AgentResponse(
            answer=f"Azione non gestita: {action_type}",
            function_result={"message": f"Azione non gestita: {action_type}", "data": None},
        )

    def _build_text_response(
        self,
        ai_response: dict,
        context_docs_list: list,
        user_sections_list: list,
    ) -> dict:
        """Build response for text (non-function-call) LLM output."""
        relevant_sources = []
        if context_docs_list and context_docs_list[0].distance <= 0.35:
            doc = context_docs_list[0]
            relevant_sources = [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "type": doc.source_type,
                    "url": (
                        doc.source_url.strip()
                        if doc.source_url and doc.source_url.strip()
                        else None
                    ),
                }
            ]

        return {
            "answer": ai_response["content"],
            "sources": relevant_sources,
            "retrieved_docs": len(context_docs_list),
            "function_result": None,
            "user_sections_list": user_sections_list,
        }

    @staticmethod
    def _get_election_dates() -> tuple[Optional[date], Optional[date]]:
        """Get the active election start/end dates."""
        try:
            from elections.models import ConsultazioneElettorale

            consultazione = ConsultazioneElettorale.objects.filter(
                is_attiva=True
            ).first()
            if consultazione and consultazione.data_inizio and consultazione.data_fine:
                return consultazione.data_inizio, consultazione.data_fine
        except Exception as e:
            logger.warning("Orchestrator: failed to get election dates: %s", e)
        return None, None
