"""
Knowledge Base Agent.

Answers informational questions using the RDL knowledge base.
Strictly read-only: no DB writes, no ticket creation, no side effects.
"""
import logging
from typing import Optional

from ai_assistant.models_typed.types import AgentResponse, ConversationContext

logger = logging.getLogger(__name__)


class KnowledgeBaseAgent:
    """
    Read-only specialist for knowledge-base Q&A.

    Uses the RAG pipeline (embedding similarity search + LLM generation)
    to answer informational questions.
    """

    def handle(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """
        Answer an informational question using the RAG pipeline
        with tool-calling support for conversational flow.

        Args:
            message: User question
            context: Full conversation context (history, profile, RAG docs)

        Returns:
            AgentResponse with answer and sources
        """
        from ai_assistant.vertex_service import vertex_ai_service
        from ai_assistant.models import KnowledgeSource
        from django.conf import settings
        from pgvector.django import CosineDistance

        logger.info(
            "KnowledgeBaseAgent: handling message for session=%d",
            context.session_id,
        )

        # Retrieve RAG documents
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
        except Exception as e:
            logger.warning("KnowledgeBaseAgent: RAG retrieval failed: %s", e)

        # Build full context text
        if context_docs_list:
            rag_parts = [
                f"[{doc.source_type}] {doc.title}\n{doc.content[:2000]}"
                for doc in context_docs_list
            ]
            full_context = (
                context.profile_text + "\n\n" + "\n\n---\n\n".join(rag_parts)
            )
        else:
            full_context = context.profile_text

        # Generate response with tools (knowledge agent uses no tools, just context)
        ai_response = vertex_ai_service.generate_with_tools(
            conversation_history=context.history,
            context=full_context,
            tools=None,
            attachments=context.attachment_data,
        )

        # Build sources list
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

        logger.info(
            "KnowledgeBaseAgent: response generated, %d RAG docs, %d sources",
            len(context_docs_list),
            len(relevant_sources),
        )

        return AgentResponse(
            answer=ai_response["content"] or "",
            sources=relevant_sources,
            retrieved_docs=len(context_docs_list),
        )
