"""
Incident persistence service.

All DB writes for incidents go through here.
"""
import logging
from typing import Optional

from .audit_service import AuditService

logger = logging.getLogger(__name__)

# Valid enum values
VALID_CATEGORIES = [
    "PROCEDURAL", "ACCESS", "MATERIALS", "INTIMIDATION",
    "IRREGULARITY", "TECHNICAL", "OTHER",
]
VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

CATEGORY_LABELS = {
    "PROCEDURAL": "Procedurale",
    "ACCESS": "Accesso al seggio",
    "MATERIALS": "Materiali",
    "INTIMIDATION": "Intimidazione",
    "IRREGULARITY": "Irregolarita",
    "TECHNICAL": "Tecnico",
    "OTHER": "Altro",
}
SEVERITY_LABELS = {
    "LOW": "Bassa",
    "MEDIUM": "Media",
    "HIGH": "Alta",
    "CRITICAL": "Critica",
}


def _resolve_sezione(sezione_numero_raw, user_sections_list=None):
    """Resolve sezione from user-provided number string."""
    from territory.models import SezioneElettorale

    sezione = None
    sezione_numero = str(sezione_numero_raw or "").strip().replace(".", "").replace(" ", "")
    sezione_not_found = False
    if sezione_numero:
        try:
            numero_int = int(sezione_numero)
            if user_sections_list:
                for s in user_sections_list:
                    if s.get("numero") == numero_int and s.get("sezione_id"):
                        sezione = SezioneElettorale.objects.filter(
                            id=s["sezione_id"], is_attiva=True
                        ).first()
                        if sezione:
                            return sezione, sezione_numero, False

            sezione = SezioneElettorale.objects.filter(
                numero=numero_int, is_attiva=True
            ).first()
            if not sezione:
                sezione_not_found = True
        except (ValueError, TypeError):
            sezione_not_found = True
    return sezione, sezione_numero, sezione_not_found


def _format_incident_message(incident, action: str, sezione, sezione_numero: str) -> str:
    sezione_text = (
        f"Sezione {sezione.numero} - {sezione.comune.nome}"
        if sezione
        else f"Sezione {sezione_numero} (non censita)"
        if sezione_numero
        else "Generale"
    )
    return (
        f"**Segnalazione #{incident.id} {action}!**\n\n"
        f"**Titolo:** {incident.title}\n"
        f"**Descrizione:** {incident.description[:200]}"
        f"{'...' if len(incident.description) > 200 else ''}\n"
        f"**Categoria:** {CATEGORY_LABELS.get(incident.category, incident.category)}\n"
        f"**Gravita:** {SEVERITY_LABELS.get(incident.severity, incident.severity)}\n"
        f"**Sezione:** {sezione_text}\n"
        f"**Verbalizzato:** {'Si' if incident.is_verbalizzato else 'No'}"
    )


class IncidentService:
    """Handles all incident persistence operations."""

    @staticmethod
    def create_or_update(
        args: dict,
        session,
        user,
        user_sections_list: Optional[list] = None,
    ) -> dict:
        """
        Create a new incident or update if one already exists in this session.

        Returns: dict with 'message' and 'data' keys.
        """
        from incidents.models import IncidentReport
        from elections.models import ConsultazioneElettorale

        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
        if not consultazione:
            return {"message": "Non c'e una consultazione attiva al momento.", "data": None}

        sezione, sezione_numero, sezione_not_found = _resolve_sezione(
            args.get("sezione_numero", ""), user_sections_list
        )

        title = args.get("title", "Segnalazione da chat")[:200]
        description = args.get("description", "")
        category = args.get("category", "OTHER").upper()
        severity = args.get("severity", "HIGH").upper()
        is_verbalizzato = args.get("is_verbalizzato", False)

        if category not in VALID_CATEGORIES:
            category = "OTHER"
        if severity not in VALID_SEVERITIES:
            severity = "HIGH"

        if sezione_not_found and sezione_numero:
            description = f"{description}\n\n[Sezione indicata dall'utente: {sezione_numero} - non trovata nel sistema]"

        existing_incident_id = (session.metadata or {}).get("incident_id")
        if existing_incident_id:
            try:
                incident = IncidentReport.objects.get(
                    id=existing_incident_id, reporter=user
                )
                changes = {}
                if incident.title != title:
                    changes["titolo"] = (incident.title, title)
                if incident.description != description:
                    changes["descrizione"] = (incident.description[:80], description[:80])
                if incident.category != category:
                    changes["categoria"] = (incident.category, category)
                if incident.severity != severity:
                    changes["gravita"] = (incident.severity, severity)
                if incident.sezione != sezione:
                    changes["sezione"] = (
                        str(incident.sezione.numero) if incident.sezione else None,
                        str(sezione.numero) if sezione else sezione_numero or None,
                    )

                incident.title = title
                incident.description = description
                incident.category = category
                incident.severity = severity
                incident.sezione = sezione
                incident.is_verbalizzato = is_verbalizzato
                incident.save()
                action = "aggiornata"

                if changes:
                    AuditService.track_incident_changes(incident, changes, user)
                AuditService.log_incident(user, "UPDATE", incident, {
                    "source": "ai_chat",
                    "session_id": session.id,
                    "changes": {
                        k: {"old": str(v[0])[:100], "new": str(v[1])[:100]}
                        for k, v in changes.items()
                    },
                })
                logger.info(
                    "Incident #%d UPDATED via chat (create called again) by %s",
                    incident.id, user.email,
                )
            except IncidentReport.DoesNotExist:
                existing_incident_id = None

        if not existing_incident_id:
            incident = IncidentReport.objects.create(
                consultazione=consultazione,
                sezione=sezione,
                title=title,
                description=description,
                category=category,
                severity=severity,
                reporter=user,
                is_verbalizzato=is_verbalizzato,
            )
            action = "creata"
            AuditService.log_incident(user, "CREATE", incident, {
                "source": "ai_chat",
                "session_id": session.id,
                "title": title,
                "category": category,
                "severity": severity,
                "sezione_numero": sezione_numero or None,
            })
            logger.info("Incident #%d CREATED via chat by %s", incident.id, user.email)

        session.metadata = session.metadata or {}
        session.metadata["incident_id"] = incident.id
        session.title = f"Segnalazione: {title[:40]}"
        session.save()

        message = _format_incident_message(incident, action, sezione, sezione_numero)
        return {"message": message, "data": {"incident_id": incident.id}}

    @staticmethod
    def update(
        args: dict,
        session,
        user,
        user_sections_list: Optional[list] = None,
    ) -> dict:
        """
        Update an existing incident in this session.

        Returns: dict with 'message' and 'data' keys.
        """
        from incidents.models import IncidentReport

        existing_incident_id = (session.metadata or {}).get("incident_id")
        if not existing_incident_id:
            return {
                "message": "Non c'e nessuna segnalazione da aggiornare in questa sessione. Vuoi crearne una nuova?",
                "data": None,
            }

        try:
            incident = IncidentReport.objects.select_related("sezione").get(
                id=existing_incident_id, reporter=user
            )
        except IncidentReport.DoesNotExist:
            return {
                "message": "La segnalazione precedente non e stata trovata. Vuoi crearne una nuova?",
                "data": None,
            }

        changes = {}

        if "title" in args and args["title"]:
            new_title = args["title"][:200]
            if incident.title != new_title:
                changes["titolo"] = (incident.title, new_title)
                incident.title = new_title

        if "description" in args and args["description"]:
            new_desc = args["description"]
            if incident.description != new_desc:
                changes["descrizione"] = (incident.description[:80], new_desc[:80])
                incident.description = new_desc

        if "category" in args and args["category"]:
            cat = args["category"].upper()
            if cat in VALID_CATEGORIES and incident.category != cat:
                changes["categoria"] = (incident.category, cat)
                incident.category = cat

        if "severity" in args and args["severity"]:
            sev = args["severity"].upper()
            if sev in VALID_SEVERITIES and incident.severity != sev:
                changes["gravita"] = (incident.severity, sev)
                incident.severity = sev

        if "sezione_numero" in args and args["sezione_numero"]:
            sezione, sezione_numero, sezione_not_found = _resolve_sezione(
                args["sezione_numero"], user_sections_list
            )
            if incident.sezione != sezione:
                changes["sezione"] = (
                    str(incident.sezione.numero) if incident.sezione else None,
                    str(sezione.numero) if sezione else sezione_numero,
                )
                incident.sezione = sezione
            if sezione_not_found and sezione_numero:
                incident.description = (
                    f"{incident.description}\n\n"
                    f"[Sezione aggiornata dall'utente: {sezione_numero} - non trovata nel sistema]"
                )

        if "is_verbalizzato" in args:
            new_verb = args["is_verbalizzato"]
            if incident.is_verbalizzato != new_verb:
                changes["verbalizzato"] = (incident.is_verbalizzato, new_verb)
                incident.is_verbalizzato = new_verb

        if not changes:
            message = _format_incident_message(
                incident,
                "invariata (nessuna modifica)",
                incident.sezione,
                str(incident.sezione.numero) if incident.sezione else "",
            )
            return {"message": message, "data": {"incident_id": incident.id}}

        incident.save()

        AuditService.track_incident_changes(incident, changes, user)
        AuditService.log_incident(user, "UPDATE", incident, {
            "source": "ai_chat",
            "session_id": session.id,
            "changes": {
                k: {"old": str(v[0])[:100], "new": str(v[1])[:100]}
                for k, v in changes.items()
            },
        })

        logger.info(
            "Incident #%d UPDATED via update_incident_report by %s: %s",
            incident.id, user.email, list(changes.keys()),
        )

        sezione_numero = str(incident.sezione.numero) if incident.sezione else ""
        message = _format_incident_message(incident, "aggiornata", incident.sezione, sezione_numero)
        return {"message": message, "data": {"incident_id": incident.id}}

    @staticmethod
    def build_preview(args: dict, user_sections_list: Optional[list] = None) -> dict:
        """Build a preview of what would be created/updated without persisting."""
        sezione, sezione_numero, _ = _resolve_sezione(
            args.get("sezione_numero", ""), user_sections_list
        )
        title = args.get("title", "Segnalazione da chat")[:200]
        category = args.get("category", "OTHER").upper()
        severity = args.get("severity", "HIGH").upper()
        if category not in VALID_CATEGORIES:
            category = "OTHER"
        if severity not in VALID_SEVERITIES:
            severity = "HIGH"

        sezione_text = (
            f"Sezione {sezione.numero} - {sezione.comune.nome}"
            if sezione
            else f"Sezione {sezione_numero}"
            if sezione_numero
            else "Generale"
        )

        return {
            "message": (
                f"**ANTEPRIMA** (non salvata - fuori finestra elettorale):\n\n"
                f"**Titolo:** {title}\n"
                f"**Descrizione:** {args.get('description', '')[:200]}\n"
                f"**Categoria:** {CATEGORY_LABELS.get(category, category)}\n"
                f"**Gravita:** {SEVERITY_LABELS.get(severity, severity)}\n"
                f"**Sezione:** {sezione_text}\n\n"
                f"_La segnalazione sara creata quando la finestra elettorale sara attiva._"
            ),
            "data": None,
        }
