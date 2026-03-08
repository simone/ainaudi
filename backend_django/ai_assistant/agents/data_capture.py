"""
Data Capture Agent.

Handles structured data entry for election section data (scrutinio).
Validates fields, detects missing/ambiguous data, prepares payloads.

Actual persistence happens through ScrutinioService.
"""
import logging
from typing import Optional

from ai_assistant.models_typed.types import (
    ActionType,
    AgentResponse,
    ConversationContext,
    PolicyDecision,
    PolicyVerdict,
    SectionDataPayload,
)
from ai_assistant.services.scrutinio_service import ScrutinioService

logger = logging.getLogger(__name__)


def _parse_int(value):
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


class DataCaptureAgent:
    """
    Specialist for election section data entry.

    Transforms function call args into structured payloads,
    validates fields, and delegates persistence to ScrutinioService.
    """

    def handle_get_status(
        self,
        args: dict,
        user,
        user_sections_list: Optional[list] = None,
    ) -> AgentResponse:
        """Handle get_scrutinio_status: read-only, always allowed."""
        logger.info("DataCaptureAgent: get_scrutinio_status args=%s", args)

        result = ScrutinioService.get_status(args, user, user_sections_list)
        return AgentResponse(
            answer=result["message"],
            function_result=result,
        )

    def handle_save(
        self,
        args: dict,
        session,
        user,
        ip_address: str,
        policy_decision: PolicyDecision,
        user_sections_list: Optional[list] = None,
    ) -> AgentResponse:
        """
        Handle save_scrutinio_data with policy enforcement.

        If policy is PREVIEW_ONLY, builds a preview without persisting.
        If ALLOW, delegates to ScrutinioService.save_data.
        If DENY, returns denial message.
        """
        logger.info(
            "DataCaptureAgent: save_scrutinio_data args=%s policy=%s",
            args,
            policy_decision.verdict.value,
        )

        if policy_decision.verdict == PolicyVerdict.DENY:
            return AgentResponse(
                answer=f"Operazione non consentita: {policy_decision.reason}",
                function_result={"message": policy_decision.reason, "data": None},
            )

        if policy_decision.verdict == PolicyVerdict.PREVIEW_ONLY:
            preview = ScrutinioService.build_preview(
                args, policy_decision.reason, user_sections_list
            )
            return AgentResponse(
                answer=preview["message"],
                function_result=preview,
            )

        # ALLOW: persist
        result = ScrutinioService.save_data(
            args, session, user, ip_address, user_sections_list
        )
        return AgentResponse(
            answer=result["message"],
            function_result=result,
        )

    @staticmethod
    def parse_payload(args: dict) -> SectionDataPayload:
        """Parse function call args into a typed SectionDataPayload."""
        return SectionDataPayload(
            sezione_numero=str(args.get("sezione_numero", "")).strip(),
            elettori_maschi=_parse_int(args.get("elettori_maschi")),
            elettori_femmine=_parse_int(args.get("elettori_femmine")),
            votanti_maschi=_parse_int(args.get("votanti_maschi")),
            votanti_femmine=_parse_int(args.get("votanti_femmine")),
            scheda_nome=args.get("scheda_nome"),
            schede_ricevute=_parse_int(args.get("schede_ricevute")),
            schede_autenticate=_parse_int(args.get("schede_autenticate")),
            schede_bianche=_parse_int(args.get("schede_bianche")),
            schede_nulle=_parse_int(args.get("schede_nulle")),
            schede_contestate=_parse_int(args.get("schede_contestate")),
            voti_si=_parse_int(args.get("voti_si")),
            voti_no=_parse_int(args.get("voti_no")),
        )
