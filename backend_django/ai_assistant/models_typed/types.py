"""
Typed domain models for the multi-agent AI assistant architecture.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    KNOWLEDGE = "knowledge"
    DATA_ENTRY = "data_entry"
    DATA_QUERY = "data_query"
    TICKET_CREATE = "ticket_create"
    TICKET_UPDATE = "ticket_update"
    TRIVIAL = "trivial"
    OFF_TOPIC = "off_topic"


class PolicyVerdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    PREVIEW_ONLY = "PREVIEW_ONLY"


class ActionType(str, Enum):
    SAVE_SCRUTINIO = "save_scrutinio_data"
    GET_SCRUTINIO = "get_scrutinio_status"
    CREATE_INCIDENT = "create_incident_report"
    UPDATE_INCIDENT = "update_incident_report"


class TicketCommandType(str, Enum):
    CREATE = "create"
    UPDATE = "update"


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

class ClassifiedIntent(BaseModel):
    intent: IntentType
    action_type: Optional[ActionType] = None
    confidence: float = 1.0
    raw_function_call: Optional[dict] = None


# ---------------------------------------------------------------------------
# Context models
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    email: str
    full_name: str = ""
    role: str = "RDL"
    role_description: str = "Rappresentante di Lista"
    sections: list[dict] = Field(default_factory=list)
    consultazione_id: Optional[int] = None
    consultazione_nome: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class ConversationContext(BaseModel):
    session_id: int
    history: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    profile_text: str = ""
    rag_context: str = ""
    attachment_data: Optional[list[dict]] = None


# ---------------------------------------------------------------------------
# Action requests
# ---------------------------------------------------------------------------

class RequestedAction(BaseModel):
    action_type: ActionType
    args: dict = Field(default_factory=dict)
    source: str = "ai_function_call"


# ---------------------------------------------------------------------------
# Policy decision
# ---------------------------------------------------------------------------

class PolicyDecision(BaseModel):
    verdict: PolicyVerdict
    reason: str = ""
    allowed_fields: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Data payloads
# ---------------------------------------------------------------------------

class SectionDataPayload(BaseModel):
    sezione_numero: str
    elettori_maschi: Optional[int] = None
    elettori_femmine: Optional[int] = None
    votanti_maschi: Optional[int] = None
    votanti_femmine: Optional[int] = None
    scheda_nome: Optional[str] = None
    schede_ricevute: Optional[int] = None
    schede_autenticate: Optional[int] = None
    schede_bianche: Optional[int] = None
    schede_nulle: Optional[int] = None
    schede_contestate: Optional[int] = None
    voti_si: Optional[int] = None
    voti_no: Optional[int] = None

    @property
    def has_seggio_data(self) -> bool:
        return any([
            self.elettori_maschi is not None,
            self.elettori_femmine is not None,
            self.votanti_maschi is not None,
            self.votanti_femmine is not None,
        ])

    @property
    def has_scheda_data(self) -> bool:
        return any([
            self.schede_ricevute is not None,
            self.schede_autenticate is not None,
            self.schede_bianche is not None,
            self.schede_nulle is not None,
            self.schede_contestate is not None,
            self.voti_si is not None,
            self.voti_no is not None,
        ])

    @property
    def is_preliminary(self) -> bool:
        """True if only contains preliminary fields (schede_autenticate, schede_ricevute)."""
        scrutiny_fields = [
            self.schede_bianche, self.schede_nulle, self.schede_contestate,
            self.voti_si, self.voti_no,
            self.votanti_maschi, self.votanti_femmine,
        ]
        return not any(f is not None for f in scrutiny_fields)


class TicketCommand(BaseModel):
    command_type: TicketCommandType
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    sezione_numero: Optional[str] = None
    is_verbalizzato: Optional[bool] = None
    existing_incident_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class NormalizedContent(BaseModel):
    """Content extracted from files/audio/documents."""
    text: str
    source_type: str = "unknown"
    mime_type: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class PreviewResult(BaseModel):
    """Result when policy is PREVIEW_ONLY."""
    message: str
    payload: Optional[dict] = None
    would_execute: str = ""


class ExecutionResult(BaseModel):
    """Result of an actual operation."""
    success: bool
    message: str
    data: Optional[dict] = None


class AgentResponse(BaseModel):
    """Unified response from any specialist agent."""
    answer: str
    sources: list[dict] = Field(default_factory=list)
    retrieved_docs: int = 0
    function_result: Optional[dict] = None
    preview: Optional[PreviewResult] = None
    user_sections_list: list[dict] = Field(default_factory=list)
