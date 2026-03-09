"""
Deterministic election policy guard.

Evaluates date/time, election calendar, and action type to decide
whether an operation should be ALLOWED, DENIED, or PREVIEW_ONLY.

This is NOT an agent. It contains no LLM calls, no conversation logic.
"""
import logging
from datetime import date
from typing import Optional

from ai_assistant.models_typed.types import (
    ActionType,
    PolicyDecision,
    PolicyVerdict,
    RequestedAction,
    SectionDataPayload,
)

logger = logging.getLogger(__name__)

# Preliminary-only fields: can be entered on day 21 and 22
PRELIMINARY_FIELDS = {
    "schede_ricevute",
    "schede_autenticate",
    "elettori_maschi",
    "elettori_femmine",
}

# Scrutiny fields: only on day 23
SCRUTINY_FIELDS = {
    "votanti_maschi",
    "votanti_femmine",
    "schede_bianche",
    "schede_nulle",
    "schede_contestate",
    "voti_si",
    "voti_no",
}


class ElectionPolicyGuard:
    """
    Centralized deterministic policy layer.

    Election dates: 21, 22, 23 of the election month.
    - 21 & 22: only preliminary data entry (ballot counts, voter rolls)
    - 23: scrutiny data entry allowed
    - Section-related tickets: only during 21-23
    - Outside the window: PREVIEW_ONLY or DENY
    """

    def evaluate(
        self,
        action: RequestedAction,
        today: Optional[date] = None,
        election_start: Optional[date] = None,
        election_end: Optional[date] = None,
        payload: Optional[SectionDataPayload] = None,
    ) -> PolicyDecision:
        """
        Evaluate whether an action is allowed given the current context.

        Args:
            action: The requested action with type and args
            today: Current date (defaults to date.today())
            election_start: First election day (day 21)
            election_end: Last election day (day 23, scrutiny day)
            payload: Parsed data payload (for data entry actions)

        Returns:
            PolicyDecision with verdict and reason
        """
        import os
        if os.environ.get("AI_POLICY_BYPASS", "").lower() == "true":
            logger.info("PolicyGuard: BYPASSED by AI_POLICY_BYPASS env var")
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="Policy bypass enabled (AI_POLICY_BYPASS=true).",
            )

        if today is None:
            today = date.today()

        decision = self._evaluate_internal(
            action, today, election_start, election_end, payload
        )

        logger.info(
            "PolicyGuard: action=%s verdict=%s reason='%s' today=%s election=%s-%s",
            action.action_type.value,
            decision.verdict.value,
            decision.reason,
            today,
            election_start,
            election_end,
        )

        return decision

    def _evaluate_internal(
        self,
        action: RequestedAction,
        today: date,
        election_start: Optional[date],
        election_end: Optional[date],
        payload: Optional[SectionDataPayload],
    ) -> PolicyDecision:
        # Read-only actions are always allowed
        if action.action_type == ActionType.GET_SCRUTINIO:
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="Read-only action, always permitted.",
            )

        # If no election dates configured, allow everything (admin override / testing)
        if election_start is None or election_end is None:
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                reason="No election dates configured, allowing by default.",
            )

        in_election_window = election_start <= today <= election_end
        is_scrutiny_day = today == election_end  # Day 23
        is_preliminary_day = election_start <= today < election_end  # Days 21-22

        # --- Ticket operations ---
        if action.action_type in (ActionType.CREATE_INCIDENT, ActionType.UPDATE_INCIDENT):
            if in_election_window:
                return PolicyDecision(
                    verdict=PolicyVerdict.ALLOW,
                    reason="Section tickets allowed during election window.",
                )
            else:
                return PolicyDecision(
                    verdict=PolicyVerdict.PREVIEW_ONLY,
                    reason=(
                        "Section ticket operations are only executed during the "
                        f"election window ({election_start} to {election_end}). "
                        "Showing preview only."
                    ),
                )

        # --- Data entry (save scrutinio) ---
        if action.action_type == ActionType.SAVE_SCRUTINIO:
            if not in_election_window:
                return PolicyDecision(
                    verdict=PolicyVerdict.PREVIEW_ONLY,
                    reason=(
                        "Data entry is only executed during the election window "
                        f"({election_start} to {election_end}). Showing preview only."
                    ),
                )

            if is_scrutiny_day:
                # Day 23: all fields allowed
                return PolicyDecision(
                    verdict=PolicyVerdict.ALLOW,
                    reason="Scrutiny day: all data entry permitted.",
                )

            if is_preliminary_day:
                # Days 21-22: only preliminary fields
                if payload and not payload.is_preliminary:
                    # Check which fields are blocked
                    blocked = []
                    if payload.votanti_maschi is not None:
                        blocked.append("votanti_maschi")
                    if payload.votanti_femmine is not None:
                        blocked.append("votanti_femmine")
                    if payload.schede_bianche is not None:
                        blocked.append("schede_bianche")
                    if payload.schede_nulle is not None:
                        blocked.append("schede_nulle")
                    if payload.schede_contestate is not None:
                        blocked.append("schede_contestate")
                    if payload.voti_si is not None:
                        blocked.append("voti_si")
                    if payload.voti_no is not None:
                        blocked.append("voti_no")

                    return PolicyDecision(
                        verdict=PolicyVerdict.PREVIEW_ONLY,
                        reason=(
                            f"Before scrutiny day ({election_end}), only preliminary "
                            "data is allowed (schede_ricevute, schede_autenticate, "
                            "elettori). Blocked fields: "
                            + ", ".join(blocked) + ". Showing preview only."
                        ),
                        allowed_fields=list(PRELIMINARY_FIELDS),
                    )

                return PolicyDecision(
                    verdict=PolicyVerdict.ALLOW,
                    reason="Preliminary day: preliminary data entry permitted.",
                    allowed_fields=list(PRELIMINARY_FIELDS),
                )

        # Fallback: deny unknown actions
        return PolicyDecision(
            verdict=PolicyVerdict.DENY,
            reason=f"Unknown action type: {action.action_type}",
        )
