"""
Ticketing Agent.

Creates, updates, and manages incident tickets.
Specialized for ticketing only - does not handle general data entry.

Actual persistence happens through IncidentService.
"""
import logging
from typing import Optional

from ai_assistant.models_typed.types import (
    AgentResponse,
    PolicyDecision,
    PolicyVerdict,
)
from ai_assistant.services.incident_service import IncidentService

logger = logging.getLogger(__name__)


class TicketingAgent:
    """
    Specialist for incident/ticket management.

    Handles create and update operations with policy enforcement.
    """

    def handle_create(
        self,
        args: dict,
        session,
        user,
        policy_decision: PolicyDecision,
        user_sections_list: Optional[list] = None,
    ) -> AgentResponse:
        """
        Handle create_incident_report with policy enforcement.

        If policy is PREVIEW_ONLY, builds a preview without persisting.
        If ALLOW, delegates to IncidentService.
        """
        logger.info(
            "TicketingAgent: create_incident_report args=%s policy=%s",
            args,
            policy_decision.verdict.value,
        )

        if policy_decision.verdict == PolicyVerdict.DENY:
            return AgentResponse(
                answer=f"Operazione non consentita: {policy_decision.reason}",
                function_result={"message": policy_decision.reason, "data": None},
            )

        if policy_decision.verdict == PolicyVerdict.PREVIEW_ONLY:
            preview = IncidentService.build_preview(args, user_sections_list)
            return AgentResponse(
                answer=preview["message"],
                function_result=preview,
            )

        # ALLOW: persist
        try:
            result = IncidentService.create_or_update(
                args, session, user, user_sections_list
            )
            return AgentResponse(
                answer=result["message"],
                function_result=result,
            )
        except Exception as e:
            logger.error("TicketingAgent: create failed: %s", e, exc_info=True)
            return AgentResponse(
                answer=f"Errore nella creazione della segnalazione: {str(e)}",
                function_result={"message": str(e), "data": None},
            )

    def handle_update(
        self,
        args: dict,
        session,
        user,
        policy_decision: PolicyDecision,
        user_sections_list: Optional[list] = None,
    ) -> AgentResponse:
        """
        Handle update_incident_report with policy enforcement.

        If policy is PREVIEW_ONLY, returns info that update was not executed.
        If ALLOW, delegates to IncidentService.
        """
        logger.info(
            "TicketingAgent: update_incident_report args=%s policy=%s",
            args,
            policy_decision.verdict.value,
        )

        if policy_decision.verdict == PolicyVerdict.DENY:
            return AgentResponse(
                answer=f"Operazione non consentita: {policy_decision.reason}",
                function_result={"message": policy_decision.reason, "data": None},
            )

        if policy_decision.verdict == PolicyVerdict.PREVIEW_ONLY:
            preview = IncidentService.build_preview(args, user_sections_list)
            return AgentResponse(
                answer=preview["message"],
                function_result=preview,
            )

        # ALLOW: persist
        try:
            result = IncidentService.update(
                args, session, user, user_sections_list
            )
            return AgentResponse(
                answer=result["message"],
                function_result=result,
            )
        except Exception as e:
            logger.error("TicketingAgent: update failed: %s", e, exc_info=True)
            return AgentResponse(
                answer=f"Errore nell'aggiornamento della segnalazione: {str(e)}",
                function_result={"message": str(e), "data": None},
            )
