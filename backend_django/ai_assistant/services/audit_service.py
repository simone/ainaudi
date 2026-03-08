"""
Audit logging service for AI-driven operations.
"""
import logging

logger = logging.getLogger(__name__)


class AuditService:
    """Encapsulates audit trail writes."""

    @staticmethod
    def log(user, action: str, target_model: str, target_id: str, details: dict):
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user_email=user.email,
                action=action,
                target_model=target_model,
                target_id=target_id,
                details=details,
            )
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    @staticmethod
    def log_incident(user, action: str, incident, details: dict):
        AuditService.log(
            user, action, "IncidentReport", str(incident.id), details
        )

    @staticmethod
    def log_scrutinio(user, action: str, sezione_id: int, details: dict):
        AuditService.log(
            user, action, "DatiSezione", str(sezione_id), details
        )

    @staticmethod
    def track_incident_changes(incident, changes: dict, user):
        """Create an IncidentComment documenting what changed."""
        from incidents.models import IncidentComment

        lines = [f"**Modifica tramite AI chat** da {user.email}:"]
        for field, (old_val, new_val) in changes.items():
            old_display = str(old_val)[:100] if old_val else "(vuoto)"
            new_display = str(new_val)[:100] if new_val else "(vuoto)"
            lines.append(f"- **{field}**: {old_display} -> {new_display}")

        IncidentComment.objects.create(
            incident=incident,
            author=user,
            content="\n".join(lines),
            is_internal=True,
        )
