"""
Tests for ElectionPolicyGuard.

Validates the deterministic policy rules:
- Scrutiny data: only on day 23
- Preliminary data (ballot signatures): allowed on days 21-22
- Section tickets: only during 21-23 window
- Outside window: PREVIEW_ONLY
- Read-only actions: always ALLOW
"""
from datetime import date

from django.test import TestCase

from ai_assistant.models_typed.types import (
    ActionType,
    PolicyVerdict,
    RequestedAction,
    SectionDataPayload,
)
from ai_assistant.policy.election_guard import ElectionPolicyGuard


class ElectionPolicyGuardTest(TestCase):
    def setUp(self):
        self.guard = ElectionPolicyGuard()
        self.election_start = date(2026, 6, 21)
        self.election_end = date(2026, 6, 23)

    def _evaluate(self, action_type, today, payload=None):
        action = RequestedAction(action_type=action_type)
        return self.guard.evaluate(
            action=action,
            today=today,
            election_start=self.election_start,
            election_end=self.election_end,
            payload=payload,
        )

    # --- Read-only actions ---

    def test_get_scrutinio_always_allowed(self):
        for day in [date(2026, 6, 15), date(2026, 6, 21), date(2026, 6, 23), date(2026, 7, 1)]:
            decision = self._evaluate(ActionType.GET_SCRUTINIO, day)
            self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    # --- Scrutinio data entry ---

    def test_scrutiny_data_allowed_on_day_23(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            voti_si=300,
            voti_no=200,
            schede_bianche=5,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 23), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    def test_scrutiny_data_preview_on_day_21(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            voti_si=300,
            voti_no=200,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 21), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    def test_scrutiny_data_preview_on_day_22(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            schede_bianche=5,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 22), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    def test_preliminary_data_allowed_on_day_21(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            schede_autenticate=75,
            schede_ricevute=100,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 21), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    def test_preliminary_data_allowed_on_day_22(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            elettori_maschi=500,
            elettori_femmine=520,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 22), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    def test_data_entry_preview_before_election(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            schede_autenticate=75,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 15), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    def test_data_entry_preview_after_election(self):
        payload = SectionDataPayload(
            sezione_numero="42",
            voti_si=300,
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 7, 1), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    # --- Ticket operations ---

    def test_ticket_create_allowed_during_election(self):
        for day in [date(2026, 6, 21), date(2026, 6, 22), date(2026, 6, 23)]:
            decision = self._evaluate(ActionType.CREATE_INCIDENT, day)
            self.assertEqual(decision.verdict, PolicyVerdict.ALLOW, f"Failed for {day}")

    def test_ticket_create_preview_before_election(self):
        decision = self._evaluate(ActionType.CREATE_INCIDENT, date(2026, 6, 15))
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    def test_ticket_create_preview_after_election(self):
        decision = self._evaluate(ActionType.CREATE_INCIDENT, date(2026, 7, 1))
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    def test_ticket_update_allowed_during_election(self):
        decision = self._evaluate(ActionType.UPDATE_INCIDENT, date(2026, 6, 22))
        self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    def test_ticket_update_preview_outside_election(self):
        decision = self._evaluate(ActionType.UPDATE_INCIDENT, date(2026, 6, 20))
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)

    # --- No election dates configured ---

    def test_no_election_dates_allows_everything(self):
        action = RequestedAction(action_type=ActionType.SAVE_SCRUTINIO)
        decision = self.guard.evaluate(
            action=action,
            today=date(2026, 6, 15),
            election_start=None,
            election_end=None,
        )
        self.assertEqual(decision.verdict, PolicyVerdict.ALLOW)

    # --- Mixed payload on preliminary day ---

    def test_mixed_payload_on_day_22_blocked(self):
        """A payload with both preliminary and scrutiny fields on day 22."""
        payload = SectionDataPayload(
            sezione_numero="42",
            schede_autenticate=75,  # preliminary: OK
            voti_si=300,  # scrutiny: blocked
        )
        decision = self._evaluate(ActionType.SAVE_SCRUTINIO, date(2026, 6, 22), payload)
        self.assertEqual(decision.verdict, PolicyVerdict.PREVIEW_ONLY)
        self.assertIn("voti_si", decision.reason)

    def test_payload_is_preliminary_property(self):
        """Test the is_preliminary helper on SectionDataPayload."""
        prelim = SectionDataPayload(
            sezione_numero="42",
            schede_autenticate=75,
            schede_ricevute=100,
        )
        self.assertTrue(prelim.is_preliminary)

        scrutiny = SectionDataPayload(
            sezione_numero="42",
            voti_si=300,
        )
        self.assertFalse(scrutiny.is_preliminary)

        mixed = SectionDataPayload(
            sezione_numero="42",
            schede_autenticate=75,
            schede_bianche=5,
        )
        self.assertFalse(mixed.is_preliminary)
