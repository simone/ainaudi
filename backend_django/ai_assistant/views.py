"""
Views for AI Assistant endpoints with RAG implementation.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
import logging

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from core.permissions import CanAskToAIAssistant
from .models import KnowledgeSource, ChatSession, ChatMessage, ChatAttachment

logger = logging.getLogger(__name__)


def _resolve_sezione(sezione_numero_raw, user_sections_list=None):
    """
    Resolve sezione from user-provided number string.
    First tries to match against user's assigned sections (precise),
    then falls back to global lookup.
    Returns (sezione, sezione_numero, not_found).
    """
    from territory.models import SezioneElettorale

    sezione = None
    sezione_numero = str(sezione_numero_raw or '').strip().replace('.', '').replace(' ', '')
    sezione_not_found = False
    if sezione_numero:
        try:
            numero_int = int(sezione_numero)

            # First: match against user's assigned sections (these have unique sezione PKs)
            if user_sections_list:
                for s in user_sections_list:
                    if s.get('numero') == numero_int and s.get('sezione_id'):
                        sezione = SezioneElettorale.objects.filter(
                            id=s['sezione_id'], is_attiva=True
                        ).first()
                        if sezione:
                            logger.info(f"Sezione {sezione_numero} matched via user assignment: pk={sezione.id}")
                            return sezione, sezione_numero, False

            # Fallback: global lookup by numero (may be ambiguous across comuni)
            sezione = SezioneElettorale.objects.filter(
                numero=numero_int,
                is_attiva=True
            ).first()
            if not sezione:
                sezione_not_found = True
                logger.warning(f"Sezione {sezione_numero} not found in DB")
        except (ValueError, TypeError):
            sezione_not_found = True
            logger.warning(f"Invalid sezione_numero: {sezione_numero}")
    return sezione, sezione_numero, sezione_not_found


def _format_incident_message(incident, action, sezione, sezione_numero):
    """Format a confirmation message for an incident create/update."""
    category_labels = {
        'PROCEDURAL': 'Procedurale', 'ACCESS': 'Accesso al seggio',
        'MATERIALS': 'Materiali', 'INTIMIDATION': 'Intimidazione',
        'IRREGULARITY': 'Irregolarita', 'TECHNICAL': 'Tecnico', 'OTHER': 'Altro',
    }
    severity_labels = {
        'LOW': 'Bassa', 'MEDIUM': 'Media', 'HIGH': 'Alta', 'CRITICAL': 'Critica',
    }
    sezione_text = (
        f"Sezione {sezione.numero} - {sezione.comune.nome}" if sezione
        else f"Sezione {sezione_numero} (non censita)" if sezione_numero
        else "Generale"
    )
    return (
        f"**Segnalazione #{incident.id} {action}!**\n\n"
        f"**Titolo:** {incident.title}\n"
        f"**Descrizione:** {incident.description[:200]}{'...' if len(incident.description) > 200 else ''}\n"
        f"**Categoria:** {category_labels.get(incident.category, incident.category)}\n"
        f"**Gravita:** {severity_labels.get(incident.severity, incident.severity)}\n"
        f"**Sezione:** {sezione_text}\n"
        f"**Verbalizzato:** {'Si' if incident.is_verbalizzato else 'No'}"
    )


def _audit_log(user, action, incident, details):
    """Write an AuditLog entry for AI operations (incidents, scrutinio, etc.)."""
    try:
        from core.models import AuditLog
        target_model = 'IncidentReport' if incident else 'DatiSezione'
        target_id = str(incident.id) if incident else str(details.get('sezione_id', ''))
        AuditLog.objects.create(
            user_email=user.email,
            action=action,
            target_model=target_model,
            target_id=target_id,
            details=details,
        )
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def _track_changes(incident, changes, user):
    """Create an IncidentComment documenting what changed and by whom."""
    from incidents.models import IncidentComment

    lines = [f"**Modifica tramite AI chat** da {user.email}:"]
    for field, (old_val, new_val) in changes.items():
        old_display = str(old_val)[:100] if old_val else '(vuoto)'
        new_display = str(new_val)[:100] if new_val else '(vuoto)'
        lines.append(f"- **{field}**: {old_display} → {new_display}")

    IncidentComment.objects.create(
        incident=incident,
        author=user,
        content="\n".join(lines),
        is_internal=True,
    )


def _parse_int(value):
    """Parse integer from function call arg (may be string, float, or int)."""
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def _match_scheda(scheda_nome, schede_qs):
    """
    Find the best matching SchedaElettorale from a queryset.
    Tries: exact match, contains match, numeric suffix match.
    Returns (scheda, error_message).
    """
    import re

    if not scheda_nome:
        # If only one scheda, use it
        if schede_qs.count() == 1:
            return schede_qs.first(), None
        return None, None

    nome_lower = scheda_nome.lower().strip()
    schede_list = list(schede_qs)

    # Exact match (case-insensitive)
    for s in schede_list:
        if s.nome.lower() == nome_lower:
            return s, None

    # Contains match
    for s in schede_list:
        if nome_lower in s.nome.lower() or s.nome.lower() in nome_lower:
            return s, None

    # Number extraction (e.g., "3" or "referendum 3" matches "Referendum abrogativo n.3")
    numbers = re.findall(r'\d+', scheda_nome)
    if numbers:
        target_num = numbers[-1]
        for s in schede_list:
            scheda_nums = re.findall(r'\d+', s.nome)
            if scheda_nums and scheda_nums[-1] == target_num:
                return s, None

    nomi_disponibili = ", ".join([s.nome for s in schede_list])
    return None, f"Scheda '{scheda_nome}' non trovata. Schede disponibili: {nomi_disponibili}"


def _handle_get_scrutinio_status(args, request, user_sections_list):
    """Handle get_scrutinio_status function call."""
    from territory.models import SezioneElettorale
    from elections.models import ConsultazioneElettorale, SchedaElettorale
    from data.models import DatiSezione, DatiScheda
    from delegations.permissions import can_enter_section_data

    sezione, sezione_numero, not_found = _resolve_sezione(
        args.get('sezione_numero', ''), user_sections_list
    )
    if not sezione:
        if not_found:
            return {'message': f'Sezione {sezione_numero} non trovata.', 'data': None}
        return {'message': 'Numero sezione non specificato.', 'data': None}

    consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
    if not consultazione:
        return {'message': 'Nessuna consultazione attiva.', 'data': None}

    if not can_enter_section_data(request.user, sezione, consultazione.id):
        return {'message': f'Non hai i permessi per accedere alla sezione {sezione.numero}.', 'data': None}

    # Get or create DatiSezione
    dati_sezione, _ = DatiSezione.objects.get_or_create(
        sezione=sezione, consultazione=consultazione,
        defaults={'inserito_da_email': request.user.email}
    )

    # Build formatted response
    loc = f"Sezione {sezione.numero} ({sezione.comune.nome}"
    if sezione.indirizzo:
        loc += f", {sezione.indirizzo}"
    if sezione.denominazione:
        loc += f" - {sezione.denominazione}"
    loc += ")"

    lines = [f"**Stato scrutinio — {loc}**\n"]

    # Dati Seggio
    lines.append("**Dati Seggio:**")
    seggio_fields = [
        ('Elettori maschi', dati_sezione.elettori_maschi),
        ('Elettori femmine', dati_sezione.elettori_femmine),
        ('Votanti maschi', dati_sezione.votanti_maschi),
        ('Votanti femmine', dati_sezione.votanti_femmine),
    ]
    for label, val in seggio_fields:
        lines.append(f"  {label}: {val if val is not None else '—'}")

    if dati_sezione.totale_elettori is not None:
        lines.append(f"  _Totale elettori: {dati_sezione.totale_elettori}_")
    if dati_sezione.affluenza_percentuale is not None:
        lines.append(f"  _Affluenza: {dati_sezione.affluenza_percentuale}%_")

    # Schede
    schede = SchedaElettorale.objects.filter(
        tipo_elezione__consultazione=consultazione
    ).order_by('ordine')

    for scheda in schede:
        try:
            ds = DatiScheda.objects.get(dati_sezione=dati_sezione, scheda=scheda)
            has_data = any([
                ds.schede_ricevute is not None, ds.schede_autenticate is not None,
                ds.voti, ds.schede_bianche is not None
            ])
            if has_data:
                lines.append(f"\n**{scheda.nome}:**")
                if ds.schede_ricevute is not None:
                    lines.append(f"  Schede ricevute: {ds.schede_ricevute}")
                if ds.schede_autenticate is not None:
                    lines.append(f"  Schede autenticate: {ds.schede_autenticate}")
                if ds.voti:
                    if 'si' in ds.voti:
                        lines.append(f"  Voti SI: {ds.voti['si']} | NO: {ds.voti.get('no', '—')}")
                    else:
                        lines.append(f"  Voti: {ds.voti}")
                for lbl, field in [('Bianche', ds.schede_bianche), ('Nulle', ds.schede_nulle), ('Contestate', ds.schede_contestate)]:
                    if field is not None:
                        lines.append(f"  {lbl}: {field}")
            else:
                lines.append(f"\n**{scheda.nome}:** nessun dato")
        except DatiScheda.DoesNotExist:
            lines.append(f"\n**{scheda.nome}:** nessun dato")

    if dati_sezione.updated_by_email:
        lines.append(f"\n_Ultimo aggiornamento: {dati_sezione.updated_by_email}, {dati_sezione.updated_at.strftime('%d/%m/%Y %H:%M') if dati_sezione.updated_at else '—'}_")

    lines.append("\nDimmi quali dati vuoi inserire o aggiornare.")

    return {'message': "\n".join(lines), 'data': {'sezione_id': sezione.id}}


def _handle_save_scrutinio_data(args, session, request, user_sections_list):
    """Handle save_scrutinio_data function call with partial update and audit trail."""
    from django.db import transaction
    from django.db.models import F
    from django.utils import timezone
    from territory.models import SezioneElettorale
    from elections.models import ConsultazioneElettorale, SchedaElettorale
    from data.models import DatiSezione, DatiScheda, SectionDataHistory
    from delegations.permissions import can_enter_section_data

    logger.info(f"save_scrutinio_data called with args: {args}")

    sezione, sezione_numero, not_found = _resolve_sezione(
        args.get('sezione_numero', ''), user_sections_list
    )
    if not sezione:
        if not_found:
            return {'message': f'Sezione {sezione_numero} non trovata nel sistema.', 'data': None}
        return {'message': 'Numero sezione non specificato.', 'data': None}

    consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
    if not consultazione:
        return {'message': 'Nessuna consultazione attiva.', 'data': None}

    if not can_enter_section_data(request.user, sezione, consultazione.id):
        return {'message': f'Non hai i permessi per inserire dati nella sezione {sezione.numero}.', 'data': None}

    ip_address = request.META.get('REMOTE_ADDR')
    changes = []  # [(campo, old, new, dati_scheda_or_None)]

    try:
        with transaction.atomic():
            # Get or create + lock DatiSezione
            dati_sezione, created = DatiSezione.objects.get_or_create(
                sezione=sezione, consultazione=consultazione,
                defaults={'inserito_da_email': request.user.email, 'inserito_at': timezone.now()}
            )
            if not created:
                dati_sezione = DatiSezione.objects.select_for_update().get(pk=dati_sezione.pk)

            # --- Update DatiSezione (turnout) fields ---
            seggio_fields = {
                'elettori_maschi': 'Elettori maschi',
                'elettori_femmine': 'Elettori femmine',
                'votanti_maschi': 'Votanti maschi',
                'votanti_femmine': 'Votanti femmine',
            }
            seggio_changed = False
            for field_name, label in seggio_fields.items():
                if field_name in args and args[field_name] is not None:
                    new_val = _parse_int(args[field_name])
                    if new_val is not None:
                        old_val = getattr(dati_sezione, field_name)
                        if old_val != new_val:
                            changes.append((label, old_val, new_val, None))
                            SectionDataHistory.objects.create(
                                dati_sezione=dati_sezione,
                                campo=field_name,
                                valore_precedente=str(old_val) if old_val is not None else None,
                                valore_nuovo=str(new_val),
                                modificato_da_email=request.user.email,
                                ip_address=ip_address,
                            )
                            setattr(dati_sezione, field_name, new_val)
                            seggio_changed = True

            if seggio_changed:
                dati_sezione.version = F('version') + 1
                dati_sezione.updated_by_email = request.user.email
                dati_sezione.inserito_da_email = dati_sezione.inserito_da_email or request.user.email
                dati_sezione.inserito_at = dati_sezione.inserito_at or timezone.now()
                dati_sezione.save()
                dati_sezione.refresh_from_db()

            # --- Update DatiScheda (ballot-specific) fields ---
            scheda_field_names = ['schede_ricevute', 'schede_autenticate', 'schede_bianche',
                                  'schede_nulle', 'schede_contestate', 'voti_si', 'voti_no']
            has_scheda_data = any(
                field in args and args[field] is not None
                for field in scheda_field_names
            )

            if has_scheda_data:
                schede_qs = SchedaElettorale.objects.filter(
                    tipo_elezione__consultazione=consultazione
                ).order_by('ordine')

                matched_scheda, match_error = _match_scheda(args.get('scheda_nome'), schede_qs)

                if match_error:
                    return {'message': match_error, 'data': None}
                if not matched_scheda:
                    nomi = ", ".join([s.nome for s in schede_qs])
                    return {
                        'message': f'Quale scheda vuoi aggiornare? Schede disponibili: {nomi}',
                        'data': None
                    }

                # Get or create + lock DatiScheda
                dati_scheda, _ = DatiScheda.objects.get_or_create(
                    dati_sezione=dati_sezione, scheda=matched_scheda
                )
                dati_scheda = DatiScheda.objects.select_for_update().get(pk=dati_scheda.pk)

                scheda_fields = {
                    'schede_ricevute': 'Schede ricevute',
                    'schede_autenticate': 'Schede autenticate',
                    'schede_bianche': 'Schede bianche',
                    'schede_nulle': 'Schede nulle',
                    'schede_contestate': 'Schede contestate',
                }
                scheda_changed = False
                for field_name, label in scheda_fields.items():
                    if field_name in args and args[field_name] is not None:
                        new_val = _parse_int(args[field_name])
                        if new_val is not None:
                            old_val = getattr(dati_scheda, field_name)
                            if old_val != new_val:
                                changes.append((f"{label} ({matched_scheda.nome})", old_val, new_val, dati_scheda))
                                SectionDataHistory.objects.create(
                                    dati_sezione=dati_sezione,
                                    dati_scheda=dati_scheda,
                                    campo=field_name,
                                    valore_precedente=str(old_val) if old_val is not None else None,
                                    valore_nuovo=str(new_val),
                                    modificato_da_email=request.user.email,
                                    ip_address=ip_address,
                                )
                                setattr(dati_scheda, field_name, new_val)
                                scheda_changed = True

                # Handle voti (SI/NO for referendum)
                voti_si = _parse_int(args.get('voti_si'))
                voti_no = _parse_int(args.get('voti_no'))
                if voti_si is not None or voti_no is not None:
                    old_voti = dati_scheda.voti or {}
                    new_voti = dict(old_voti)
                    if voti_si is not None:
                        old_si = old_voti.get('si')
                        new_voti['si'] = voti_si
                        if old_si != voti_si:
                            changes.append((f"Voti SI ({matched_scheda.nome})", old_si, voti_si, dati_scheda))
                            scheda_changed = True
                    if voti_no is not None:
                        old_no = old_voti.get('no')
                        new_voti['no'] = voti_no
                        if old_no != voti_no:
                            changes.append((f"Voti NO ({matched_scheda.nome})", old_no, voti_no, dati_scheda))
                            scheda_changed = True
                    if scheda_changed:
                        dati_scheda.voti = new_voti
                        SectionDataHistory.objects.create(
                            dati_sezione=dati_sezione,
                            dati_scheda=dati_scheda,
                            campo='voti',
                            valore_precedente=str(old_voti) if old_voti else None,
                            valore_nuovo=str(new_voti),
                            modificato_da_email=request.user.email,
                            ip_address=ip_address,
                        )

                if scheda_changed:
                    dati_scheda.validate_data()
                    dati_scheda.version = F('version') + 1
                    dati_scheda.updated_by_email = request.user.email
                    dati_scheda.inserito_at = dati_scheda.inserito_at or timezone.now()
                    dati_scheda.save()

            # Invalidate cache
            if changes:
                ConsultazioneElettorale.objects.filter(id=consultazione.id).update(
                    data_version=timezone.now()
                )

    except Exception as e:
        logger.error(f"Error in save_scrutinio_data: {e}", exc_info=True)
        return {'message': f'Errore nel salvataggio: {str(e)}', 'data': None}

    if not changes:
        return {'message': 'Nessun dato da aggiornare (i valori sono gli stessi).', 'data': None}

    # Format confirmation
    loc = f"Sezione {sezione.numero} ({sezione.comune.nome})"
    lines = [f"**Dati salvati per {loc}:**\n"]
    for campo, old_val, new_val, _ in changes:
        old_str = str(old_val) if old_val is not None else '—'
        lines.append(f"  {campo}: {old_str} -> **{new_val}**")

    # Audit log
    _audit_log(request.user, 'SCRUTINIO_UPDATE', None, {
        'source': 'ai_chat',
        'session_id': session.id,
        'sezione_id': sezione.id,
        'sezione_numero': sezione.numero,
        'changes': [{
            'campo': c[0], 'old': str(c[1]) if c[1] is not None else None, 'new': str(c[2])
        } for c in changes],
    })

    logger.info(
        f"Scrutinio data saved for sezione {sezione.numero} by {request.user.email}: "
        f"{len(changes)} changes via AI chat"
    )

    return {'message': "\n".join(lines), 'data': {'sezione_id': sezione.id, 'changes': len(changes)}}


def execute_ai_function(function_name: str, args: dict, session, request, user_sections_list=None) -> dict:
    """Execute an AI-requested function and return the result."""

    valid_categories = ['PROCEDURAL', 'ACCESS', 'MATERIALS', 'INTIMIDATION', 'IRREGULARITY', 'TECHNICAL', 'OTHER']
    valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

    # --- Scrutinio functions ---
    if function_name == 'get_scrutinio_status':
        return _handle_get_scrutinio_status(args, request, user_sections_list)

    if function_name == 'save_scrutinio_data':
        return _handle_save_scrutinio_data(args, session, request, user_sections_list)

    # --- Incident functions ---
    if function_name == 'create_incident_report':
        try:
            from incidents.models import IncidentReport
            from elections.models import ConsultazioneElettorale

            logger.info(f"create_incident_report called with args: {args}")

            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return {'message': 'Non c\'e una consultazione attiva al momento.', 'data': None}

            sezione, sezione_numero, sezione_not_found = _resolve_sezione(
                args.get('sezione_numero', ''), user_sections_list
            )

            title = args.get('title', 'Segnalazione da chat')[:200]
            description = args.get('description', '')
            category = args.get('category', 'OTHER').upper()
            severity = args.get('severity', 'HIGH').upper()
            is_verbalizzato = args.get('is_verbalizzato', False)

            if category not in valid_categories:
                category = 'OTHER'
            if severity not in valid_severities:
                severity = 'HIGH'

            if sezione_not_found and sezione_numero:
                description = f"{description}\n\n[Sezione indicata dall'utente: {sezione_numero} - non trovata nel sistema]"

            # If session already has an incident, UPDATE it instead of creating a duplicate
            existing_incident_id = (session.metadata or {}).get('incident_id')
            if existing_incident_id:
                try:
                    incident = IncidentReport.objects.get(id=existing_incident_id, reporter=request.user)
                    # Track what changed
                    changes = {}
                    if incident.title != title:
                        changes['titolo'] = (incident.title, title)
                    if incident.description != description:
                        changes['descrizione'] = (incident.description[:80], description[:80])
                    if incident.category != category:
                        changes['categoria'] = (incident.category, category)
                    if incident.severity != severity:
                        changes['gravita'] = (incident.severity, severity)
                    if incident.sezione != sezione:
                        changes['sezione'] = (
                            str(incident.sezione.numero) if incident.sezione else None,
                            str(sezione.numero) if sezione else sezione_numero or None
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
                        _track_changes(incident, changes, request.user)
                    _audit_log(request.user, 'UPDATE', incident, {
                        'source': 'ai_chat', 'session_id': session.id,
                        'changes': {k: {'old': str(v[0])[:100], 'new': str(v[1])[:100]} for k, v in changes.items()}
                    })
                    logger.info(f"Incident #{incident.id} UPDATED via chat (create called again) by {request.user.email}")
                except IncidentReport.DoesNotExist:
                    existing_incident_id = None  # Fall through to create

            if not existing_incident_id:
                incident = IncidentReport.objects.create(
                    consultazione=consultazione,
                    sezione=sezione,
                    title=title,
                    description=description,
                    category=category,
                    severity=severity,
                    reporter=request.user,
                    is_verbalizzato=is_verbalizzato,
                )
                action = "creata"
                _audit_log(request.user, 'CREATE', incident, {
                    'source': 'ai_chat', 'session_id': session.id,
                    'title': title, 'category': category, 'severity': severity,
                    'sezione_numero': sezione_numero or None,
                })
                logger.info(f"Incident #{incident.id} CREATED via chat by {request.user.email}")

            session.metadata = session.metadata or {}
            session.metadata['incident_id'] = incident.id
            session.title = f"Segnalazione: {title[:40]}"
            session.save()

            message = _format_incident_message(incident, action, sezione, sezione_numero)
            return {'message': message, 'data': {'incident_id': incident.id}}

        except Exception as e:
            logger.error(f"Error in create_incident_report: {e}", exc_info=True)
            return {'message': f'Errore nella creazione della segnalazione: {str(e)}', 'data': None}

    elif function_name == 'update_incident_report':
        try:
            from incidents.models import IncidentReport

            logger.info(f"update_incident_report called with args: {args}")

            existing_incident_id = (session.metadata or {}).get('incident_id')
            if not existing_incident_id:
                return {'message': 'Non c\'e nessuna segnalazione da aggiornare in questa sessione. Vuoi crearne una nuova?', 'data': None}

            try:
                incident = IncidentReport.objects.select_related('sezione').get(
                    id=existing_incident_id, reporter=request.user
                )
            except IncidentReport.DoesNotExist:
                return {'message': 'La segnalazione precedente non e stata trovata. Vuoi crearne una nuova?', 'data': None}

            # Track changes for audit + comment
            changes = {}

            if 'title' in args and args['title']:
                new_title = args['title'][:200]
                if incident.title != new_title:
                    changes['titolo'] = (incident.title, new_title)
                    incident.title = new_title

            if 'description' in args and args['description']:
                new_desc = args['description']
                if incident.description != new_desc:
                    changes['descrizione'] = (incident.description[:80], new_desc[:80])
                    incident.description = new_desc

            if 'category' in args and args['category']:
                cat = args['category'].upper()
                if cat in valid_categories and incident.category != cat:
                    changes['categoria'] = (incident.category, cat)
                    incident.category = cat

            if 'severity' in args and args['severity']:
                sev = args['severity'].upper()
                if sev in valid_severities and incident.severity != sev:
                    changes['gravita'] = (incident.severity, sev)
                    incident.severity = sev

            if 'sezione_numero' in args and args['sezione_numero']:
                sezione, sezione_numero, sezione_not_found = _resolve_sezione(
                    args['sezione_numero'], user_sections_list
                )
                if incident.sezione != sezione:
                    changes['sezione'] = (
                        str(incident.sezione.numero) if incident.sezione else None,
                        str(sezione.numero) if sezione else sezione_numero
                    )
                    incident.sezione = sezione
                if sezione_not_found and sezione_numero:
                    incident.description = f"{incident.description}\n\n[Sezione aggiornata dall'utente: {sezione_numero} - non trovata nel sistema]"

            if 'is_verbalizzato' in args:
                new_verb = args['is_verbalizzato']
                if incident.is_verbalizzato != new_verb:
                    changes['verbalizzato'] = (incident.is_verbalizzato, new_verb)
                    incident.is_verbalizzato = new_verb

            if not changes:
                message = _format_incident_message(
                    incident, "invariata (nessuna modifica)",
                    incident.sezione, str(incident.sezione.numero) if incident.sezione else ''
                )
                return {'message': message, 'data': {'incident_id': incident.id}}

            incident.save()

            # Log changes as internal comment + audit
            _track_changes(incident, changes, request.user)
            _audit_log(request.user, 'UPDATE', incident, {
                'source': 'ai_chat', 'session_id': session.id,
                'changes': {k: {'old': str(v[0])[:100], 'new': str(v[1])[:100]} for k, v in changes.items()}
            })

            logger.info(f"Incident #{incident.id} UPDATED via update_incident_report by {request.user.email}: {list(changes.keys())}")

            sezione_numero = str(incident.sezione.numero) if incident.sezione else ''
            message = _format_incident_message(incident, "aggiornata", incident.sezione, sezione_numero)
            return {'message': message, 'data': {'incident_id': incident.id}}

        except Exception as e:
            logger.error(f"Error in update_incident_report: {e}", exc_info=True)
            return {'message': f'Errore nell\'aggiornamento della segnalazione: {str(e)}', 'data': None}

    else:
        logger.warning(f"Unknown function called: {function_name} with args: {args}")
        return {'message': f'Funzione sconosciuta: {function_name}', 'data': None}


def generate_session_title(first_message: str) -> str:
    """Generate a short title from the first user message using Gemini."""
    from .vertex_service import vertex_ai_service

    prompt = f"""Genera un titolo brevissimo (max 6 parole) per questa conversazione, basandoti sulla domanda dell'utente.
Il titolo deve essere descrittivo ma conciso, in italiano.

Domanda utente: "{first_message}"

Rispondi SOLO con il titolo, senza virgolette, senza punteggiatura finale.
Esempi:
- "Come si compila la scheda?" → "Compilazione scheda elettorale"
- "Cosa fare se vedo irregolarità?" → "Gestione irregolarità"
- "Quali sono i miei diritti?" → "Diritti e doveri RDL"
"""

    try:
        title = vertex_ai_service.generate_response(prompt, context=None)
        # Clean up title
        title = title.strip().strip('"').strip("'").strip('.')
        # Limit length
        if len(title) > 60:
            title = title[:57] + '...'
        return title
    except Exception as e:
        logger.error(f"Title generation failed: {e}")
        # Fallback: use first words of message
        words = first_message.split()[:6]
        return ' '.join(words) + ('...' if len(words) == 6 else '')


def generate_ai_response(request, session, message, attachment_data=None):
    """
    Shared AI generation logic used by both ChatView and ChatBranchView.

    Builds user profile context, retrieves RAG docs, calls Vertex AI with tools.

    Args:
        request: HTTP request
        session: ChatSession instance
        message: User message text
        attachment_data: Optional list of dicts with 'data' (bytes) and 'mime_type' (str)

    Returns:
        dict: {
            'answer': str,
            'sources': list[dict],
            'retrieved_docs': int,
            'function_result': dict or None,
            'user_sections_list': list,
        }
    """
    from .tools import all_ai_tools
    from .vertex_service import vertex_ai_service

    # Get conversation history
    history_messages = session.messages.order_by('created_at')
    conversation_history = [
        {'role': msg.role, 'content': msg.content}
        for msg in history_messages
    ]

    # Build user profile context (passed to AI every call)
    user_profile_context = ""
    user_sections_list = []
    try:
        from delegations.models import DesignazioneRDL, Delegato, SubDelega
        from elections.models import ConsultazioneElettorale
        from django.db.models import Q
        from datetime import datetime

        user = request.user
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        now = datetime.now()

        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()

        # Determine user role
        user_role = "RDL"
        role_description = "Rappresentante di Lista"
        if consultazione:
            is_delegato = Delegato.objects.filter(
                consultazione=consultazione, email=user.email
            ).exists()
            is_subdelegato = SubDelega.objects.filter(
                delegato__consultazione=consultazione, email=user.email
            ).exists()
            if is_delegato:
                user_role = "DELEGATO"
                role_description = "Delegato di Lista (supervisiona RDL nel suo territorio)"
            elif is_subdelegato:
                user_role = "SUBDELEGATO"
                role_description = "Sub-Delegato (supervisiona RDL nel suo territorio)"

        # Build user profile
        profile_parts = [
            f"DATA E ORA: {now.strftime('%A %d %B %Y, ore %H:%M')}",
            f"PROFILO UTENTE: {user_name} ({user.email})",
            f"RUOLO: {role_description}",
        ]

        if consultazione:
            # Compute temporal relationship to consultazione
            today = now.date()
            data_inizio = consultazione.data_inizio
            data_fine = consultazione.data_fine

            if data_inizio and data_fine:
                if today < data_inizio:
                    days_until = (data_inizio - today).days
                    fase = f"PRIMA della consultazione. Mancano {days_until} giorni all'inizio."
                elif today > data_fine:
                    days_since = (today - data_fine).days
                    fase = f"DOPO la consultazione. Terminata da {days_since} giorni."
                else:
                    fase = "IN CORSO. Siamo nel periodo della consultazione."
            else:
                fase = "Date non disponibili."

            tipi_elezione = consultazione.tipi_elezione.all()
            tipi_names = ", ".join([t.get_tipo_display() if hasattr(t, 'get_tipo_display') else str(t) for t in tipi_elezione[:5]]) if tipi_elezione else ""

            consultazione_info = (
                f"L'UNICA CONSULTAZIONE ATTIVA E': {consultazione.nome}"
                f"{' (' + tipi_names + ')' if tipi_names else ''}\n"
                f"  Si vota dal {data_inizio.strftime('%A %d %B %Y') if data_inizio else '?'} "
                f"al {data_fine.strftime('%A %d %B %Y') if data_fine else '?'}\n"
                f"  {fase}\n"
                f"  Qualsiasi domanda su scrutinio, seggi, voto, schede si riferisce a QUESTA consultazione."
            )
            if consultazione.descrizione:
                consultazione_info += f"\n  Dettagli: {consultazione.descrizione[:300]}"
            profile_parts.append(consultazione_info)

            # Get assigned sections (for RDL)
            designazioni = DesignazioneRDL.objects.filter(
                Q(effettivo_email=user.email) | Q(supplente_email=user.email),
                processo__consultazione=consultazione,
                is_attiva=True,
            ).select_related('sezione', 'sezione__comune', 'sezione__municipio')

            for des in designazioni:
                sez = des.sezione
                if sez:
                    section_info = {
                        'sezione_id': sez.id,  # DB PK for precise lookup
                        'id': sez.numero, 'numero': sez.numero,
                        'comune': sez.comune.nome,
                        'municipio': sez.municipio.nome if sez.municipio else None,
                        'indirizzo': sez.indirizzo,
                        'denominazione': sez.denominazione
                    }
                    user_sections_list.append(section_info)

            if user_sections_list:
                sections_text = "\n".join([
                    f"  - Sezione {s['numero']} di {s['comune']}{' ('+s['municipio']+')' if s['municipio'] else ''}{' - '+s['indirizzo'] if s['indirizzo'] else ''}"
                    for s in user_sections_list
                ])
                if user_role == "RDL":
                    profile_parts.append(f"LE TUE SEZIONI ASSEGNATE (ACCETTA SOLO QUESTE per segnalazioni):\n{sections_text}")
                else:
                    profile_parts.append(f"SEZIONI ASSEGNATE COME RDL:\n{sections_text}")
            else:
                if user_role == "RDL":
                    profile_parts.append("SEZIONI: Nessuna sezione ancora assegnata")
                else:
                    profile_parts.append("NOTA: Come delegato, puoi segnalare per qualsiasi sezione del tuo territorio")
        else:
            profile_parts.append("CONSULTAZIONE: Nessuna consultazione attiva al momento")

        # Add scrutinio status for user's sections
        if user_sections_list and consultazione:
            try:
                from data.models import DatiSezione, DatiScheda
                from elections.models import SchedaElettorale

                # Get schede for this consultazione
                schede = list(SchedaElettorale.objects.filter(
                    tipo_elezione__consultazione=consultazione
                ).order_by('ordine'))
                if schede:
                    schede_names = ", ".join([s.nome for s in schede])
                    profile_parts.append(f"SCHEDE NELLA CONSULTAZIONE: {schede_names}")

                # Get scrutinio data for user's sections (compact)
                sezione_ids = [s['sezione_id'] for s in user_sections_list if s.get('sezione_id')]
                if sezione_ids:
                    dati_sezioni = {
                        ds.sezione_id: ds
                        for ds in DatiSezione.objects.filter(
                            sezione_id__in=sezione_ids, consultazione=consultazione
                        ).select_related('sezione')
                    }

                    scrutinio_lines = []
                    for sec_info in user_sections_list:
                        sez_id = sec_info.get('sezione_id')
                        ds = dati_sezioni.get(sez_id)
                        if not ds:
                            scrutinio_lines.append(f"  Sez.{sec_info['numero']}: nessun dato inserito")
                            continue

                        # Compact summary of seggio data
                        parts = []
                        if ds.elettori_maschi is not None or ds.elettori_femmine is not None:
                            em = ds.elettori_maschi if ds.elettori_maschi is not None else '?'
                            ef = ds.elettori_femmine if ds.elettori_femmine is not None else '?'
                            parts.append(f"elettori M={em}/F={ef}")
                        if ds.votanti_maschi is not None or ds.votanti_femmine is not None:
                            vm = ds.votanti_maschi if ds.votanti_maschi is not None else '?'
                            vf = ds.votanti_femmine if ds.votanti_femmine is not None else '?'
                            parts.append(f"votanti M={vm}/F={vf}")

                        # Schede status
                        schede_dati = {
                            sd.scheda_id: sd
                            for sd in DatiScheda.objects.filter(dati_sezione=ds)
                        }
                        schede_complete = 0
                        schede_details = []
                        for scheda in schede:
                            sd = schede_dati.get(scheda.id)
                            if sd and any([sd.schede_ricevute is not None, sd.voti]):
                                schede_complete += 1
                                voti_str = ""
                                if sd.voti and 'si' in sd.voti:
                                    voti_str = f" SI={sd.voti['si']}/NO={sd.voti.get('no', '?')}"
                                detail = f"ric={sd.schede_ricevute or '?'}/aut={sd.schede_autenticate or '?'}{voti_str}"
                                if sd.schede_bianche is not None:
                                    detail += f" bia={sd.schede_bianche}"
                                if sd.schede_nulle is not None:
                                    detail += f" nul={sd.schede_nulle}"
                                schede_details.append(f"    {scheda.nome}: {detail}")
                            else:
                                schede_details.append(f"    {scheda.nome}: vuoto")

                        if parts:
                            summary = ", ".join(parts)
                            summary += f" | schede: {schede_complete}/{len(schede)}"
                        else:
                            summary = "nessun dato inserito"

                        scrutinio_lines.append(f"  Sez.{sec_info['numero']}: {summary}")
                        scrutinio_lines.extend(schede_details)

                    if scrutinio_lines:
                        profile_parts.append(
                            "DATI SCRUTINIO ATTUALI (usa save_scrutinio_data per aggiornare):\n"
                            + "\n".join(scrutinio_lines)
                        )
            except Exception as e:
                logger.warning(f"Error loading scrutinio context: {e}", exc_info=True)

        # Add existing incident info if session has one
        existing_incident_id = (session.metadata or {}).get('incident_id')
        if existing_incident_id:
            try:
                from incidents.models import IncidentReport
                incident = IncidentReport.objects.get(id=existing_incident_id)
                profile_parts.append(
                    f"SEGNALAZIONE GIA APERTA IN QUESTA SESSIONE (ID #{incident.id}):\n"
                    f"  Titolo: {incident.title}\n"
                    f"  Descrizione: {incident.description[:200]}\n"
                    f"  Categoria: {incident.category}\n"
                    f"  Gravita: {incident.severity}\n"
                    f"  Sezione: {incident.sezione.numero if incident.sezione else 'Generale'}\n"
                    f"  → Per modificarla, usa update_incident_report. NON creare una nuova."
                )
            except Exception:
                pass

        user_profile_context = "\n".join(profile_parts)
        logger.debug(f"User profile context:\n{user_profile_context}")
    except Exception as e:
        logger.warning(f"Error retrieving user context: {e}", exc_info=True)
        user_profile_context = f"PROFILO UTENTE: {request.user.email}"

    # Get RAG context (retrieve similar documents)
    from pgvector.django import CosineDistance
    context_docs_list = []
    try:
        query_embedding = vertex_ai_service.generate_embedding(message)
        context_docs = (
            KnowledgeSource.objects
            .filter(is_active=True)
            .annotate(distance=CosineDistance('embedding', query_embedding))
            .filter(distance__lte=(1 - settings.RAG_SIMILARITY_THRESHOLD))
            .order_by('distance')
            [:settings.RAG_TOP_K]
        )
        context_docs_list = list(context_docs)

        if context_docs_list:
            context_parts = [f"[{doc.source_type}] {doc.title}\n{doc.content[:2000]}" for doc in context_docs_list]
            context_text = user_profile_context + "\n\n" + "\n\n---\n\n".join(context_parts)
        else:
            context_text = user_profile_context
    except Exception as e:
        logger.warning(f"Error retrieving context: {e}")
        context_text = user_profile_context

    # Log full context for debugging (truncated)
    logger.info(
        f"AI context for session={session.id}: "
        f"profile={user_profile_context[:500]} | "
        f"rag_docs={len(context_docs_list)} | "
        f"history_msgs={len(conversation_history)}"
    )

    # Generate with tools - may return text OR function call
    ai_response = vertex_ai_service.generate_with_tools(
        conversation_history=conversation_history,
        context=context_text,
        tools=all_ai_tools,
        attachments=attachment_data,
    )

    # Handle function call if present
    if ai_response['function_call']:
        function_name = ai_response['function_call']['name']
        function_args = ai_response['function_call']['args']
        logger.info(f"AI called function: {function_name} with args: {function_args}")

        function_result = execute_ai_function(
            function_name,
            function_args,
            session=session,
            request=request,
            user_sections_list=user_sections_list,
        )

        return {
            'answer': function_result['message'],
            'sources': [],
            'retrieved_docs': 0,
            'function_result': function_result,
            'user_sections_list': user_sections_list,
        }
    else:
        # Normal text response (only 1 most relevant source IF highly relevant)
        relevant_sources = []
        if context_docs_list and context_docs_list[0].distance <= 0.35:
            doc = context_docs_list[0]
            relevant_sources = [{
                'id': doc.id,
                'title': doc.title,
                'type': doc.source_type,
                'url': doc.source_url.strip() if doc.source_url and doc.source_url.strip() else None
            }]

        return {
            'answer': ai_response['content'],
            'sources': relevant_sources,
            'retrieved_docs': len(context_docs_list),
            'function_result': None,
            'user_sections_list': user_sections_list,
        }


class ChatView(APIView):
    """
    Send a message to the AI assistant or retrieve session history.

    POST /api/ai/chat/
    JSON: {"session_id": 1, "message": "...", "context": "SCRUTINY"}
    Multipart: message (text), session_id (text), attachment (file)

    GET /api/ai/chat/?session_id=1
    Returns all messages in the session
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """Retrieve messages from a session."""
        session_id = request.query_params.get('session_id')

        if not session_id:
            return Response(
                {'error': 'session_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = ChatSession.objects.get(
                id=session_id,
                user_email=request.user.email
            )
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        # Get all messages in chronological order with attachments prefetched
        messages = session.messages.order_by('created_at').prefetch_related('attachments')

        return Response({
            'session_id': session.id,
            'title': session.title or 'Nuova conversazione',
            'incident_id': session.metadata.get('incident_id') if session.metadata else None,
            'messages': [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at,
                    'sources': [
                        {
                            'id': src.id,
                            'title': src.title,
                            'type': src.source_type,
                            'url': src.source_url.strip() if src.source_url and src.source_url.strip() else None,
                        }
                        for src in KnowledgeSource.objects.filter(id__in=msg.sources_cited)
                    ] if msg.sources_cited else [],
                    'attachments': [
                        {
                            'id': att.id,
                            'filename': att.filename,
                            'file_type': att.file_type,
                            'mime_type': att.mime_type,
                            'file_size': att.file_size,
                            'url': att.file.url if att.file else None,
                        }
                        for att in msg.attachments.all()
                    ]
                }
                for msg in messages
            ]
        })

    def post(self, request):
        # Check feature flag
        if not settings.FEATURE_FLAGS.get('AI_ASSISTANT', False):
            return Response(
                {'error': 'AI Assistant non abilitato'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        session_id = request.data.get('session_id')
        message = request.data.get('message')
        context = request.data.get('context')

        logger.info(f"ChatView.post: user={request.user.email} session_id={session_id} context={context} message='{message[:80] if message else None}'")

        if not message:
            return Response(
                {'error': 'message required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Message length validation (2000 chars)
        if len(message) > 2000:
            return Response(
                {'error': 'Message too long (max 2000 characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(
                    id=session_id,
                    user_email=request.user.email
                )
                logger.debug(f"ChatView.post: existing session={session.id}")
            except ChatSession.DoesNotExist:
                logger.warning(f"ChatView.post: session {session_id} not found for user={request.user.email}")
                return Response({'error': 'Session not found'}, status=404)
        else:
            session = ChatSession.objects.create(
                user_email=request.user.email,
                context=context
            )
            logger.info(f"ChatView.post: new session={session.id}")

        # Handle file attachment
        attachment_data = None
        attachment_file = request.FILES.get('attachment')
        if attachment_file:
            mime_type = attachment_file.content_type or ''
            supported_types = ChatAttachment.SUPPORTED_IMAGE_TYPES | ChatAttachment.SUPPORTED_AUDIO_TYPES
            if mime_type not in supported_types:
                return Response(
                    {'error': f'Tipo file non supportato: {mime_type}. Supportati: immagini (JPEG, PNG, GIF, WebP) e audio (MP3, WAV, OGG, AAC, FLAC, M4A).'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if attachment_file.size > ChatAttachment.MAX_FILE_SIZE:
                max_mb = ChatAttachment.MAX_FILE_SIZE // (1024 * 1024)
                return Response(
                    {'error': f'File troppo grande (max {max_mb}MB).'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Read file bytes for Gemini
            file_bytes = attachment_file.read()
            attachment_file.seek(0)  # Reset for saving
            attachment_data = [{'data': file_bytes, 'mime_type': mime_type}]
            logger.info(f"ChatView.post: attachment {attachment_file.name} ({mime_type}, {attachment_file.size} bytes)")

        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message
        )

        # Save attachment if present
        saved_attachment = None
        if attachment_file:
            saved_attachment = ChatAttachment.objects.create(
                message=user_message,
                file=attachment_file,
                file_type=ChatAttachment.detect_file_type(attachment_file.content_type or ''),
                mime_type=attachment_file.content_type or '',
                filename=attachment_file.name or 'attachment',
                file_size=attachment_file.size,
            )
            logger.info(f"ChatView.post: saved attachment {saved_attachment.id} for message {user_message.id}")

        # === RAG with AGENTIC TOOLS (Function Calling) ===
        try:
            logger.debug(f"ChatView.post: calling AI for session={session.id}")

            rag_result = generate_ai_response(request, session, message, attachment_data=attachment_data)

            # Save assistant response
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=rag_result['answer'],
                sources_cited=[s['id'] for s in rag_result['sources']]
            )

            # Generate title if this is the first user message
            if session.messages.count() == 2 and not session.title:  # 1 user + 1 assistant
                try:
                    title = generate_session_title(message)
                    session.title = title
                    session.save(update_fields=['title'])
                except Exception as e:
                    logger.warning(f"ChatView.post: title generation failed: {e}")

            logger.info(f"ChatView.post: OK session={session.id} assistant_msg={assistant_message.id}")
            user_msg_data = {
                'id': user_message.id,
                'role': user_message.role,
                'content': user_message.content,
            }
            if saved_attachment:
                user_msg_data['attachments'] = [{
                    'id': saved_attachment.id,
                    'filename': saved_attachment.filename,
                    'file_type': saved_attachment.file_type,
                    'mime_type': saved_attachment.mime_type,
                    'file_size': saved_attachment.file_size,
                    'url': saved_attachment.file.url if saved_attachment.file else None,
                }]
            return Response({
                'session_id': session.id,
                'title': session.title,
                'user_message': user_msg_data,
                'message': {
                    'id': assistant_message.id,
                    'role': assistant_message.role,
                    'content': assistant_message.content,
                    'sources': rag_result['sources'],
                    'retrieved_docs': rag_result['retrieved_docs'],
                }
            })

        except Exception as e:
            logger.error(
                f"ChatView.post FAILED: user={request.user.email} session={session.id} "
                f"message='{message[:100]}' error={type(e).__name__}: {e}",
                exc_info=True
            )

            # Save a friendly error message as assistant response so the conversation stays coherent
            error_content = (
                "🙈 Scusa, Ainaudino è un po' sovraccarico in questo momento e non riesce a rispondere. "
                "Riprova tra qualche secondo! Se il problema persiste, prova ad aprire una nuova conversazione."
            )
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=error_content,
                sources_cited=[]
            )

            return Response({
                'session_id': session.id,
                'title': session.title,
                'user_message': {
                    'id': user_message.id,
                    'role': user_message.role,
                    'content': user_message.content,
                },
                'message': {
                    'id': 0,  # Placeholder
                    'role': 'assistant',
                    'content': error_content,
                    'sources': [],
                    'retrieved_docs': 0,
                }
            })


class ChatBranchView(APIView):
    """
    Create a new chat branch by editing a message.

    POST /api/ai/chat/branch/
    {
        "session_id": 1,
        "message_id": 5,  // ID of the message to edit (USER message)
        "new_message": "Edited question text"
    }

    Creates a new session with:
    - All messages up to (but not including) the edited message
    - The edited message
    - New AI response
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

    def post(self, request):
        session_id = request.data.get('session_id')
        message_id = request.data.get('message_id')
        new_message = request.data.get('new_message')

        logger.info(
            f"ChatBranchView.post: user={request.user.email} session_id={session_id} "
            f"message_id={message_id} new_message='{new_message[:80] if new_message else None}'"
        )

        if not all([session_id, message_id, new_message]):
            return Response(
                {'error': 'session_id, message_id, and new_message required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            original_session = ChatSession.objects.get(
                id=session_id,
                user_email=request.user.email
            )
        except ChatSession.DoesNotExist:
            logger.warning(f"ChatBranchView.post: session {session_id} not found for user={request.user.email}")
            return Response({'error': 'Session not found'}, status=404)

        try:
            edit_message = ChatMessage.objects.get(
                id=message_id,
                session=original_session,
                role=ChatMessage.Role.USER
            )
        except ChatMessage.DoesNotExist:
            logger.warning(f"ChatBranchView.post: message {message_id} not found in session {session_id}")
            return Response({'error': 'Message not found or not a user message'}, status=404)

        # Generate title for new branch based on edited message
        try:
            new_title = generate_session_title(new_message)
        except Exception as e:
            logger.warning(f"ChatBranchView.post: title generation failed: {e}")
            new_title = f"Branch: {new_message[:50]}..."

        # Create new branch session (copy metadata and sezione from parent)
        new_session = ChatSession.objects.create(
            user_email=request.user.email,
            title=new_title,
            context=original_session.context,
            parent_session=original_session,
            sezione=original_session.sezione,
            metadata=original_session.metadata.copy() if original_session.metadata else {}
        )
        logger.debug(f"ChatBranchView.post: created branch session={new_session.id} from session={session_id}, copied metadata={bool(original_session.metadata)}")

        # Copy all messages BEFORE the edited one
        messages_before = original_session.messages.filter(
            created_at__lt=edit_message.created_at
        ).order_by('created_at')
        logger.debug(f"ChatBranchView.post: copying {messages_before.count()} messages before message_id={message_id}")

        for msg in messages_before:
            ChatMessage.objects.create(
                session=new_session,
                role=msg.role,
                content=msg.content,
                sources_cited=msg.sources_cited
            )

        # Add the edited user message
        ChatMessage.objects.create(
            session=new_session,
            role=ChatMessage.Role.USER,
            content=new_message
        )

        # Generate AI response for the edited message (same pipeline as ChatView)
        try:
            logger.debug(f"ChatBranchView.post: calling AI for branch session={new_session.id}")

            rag_result = generate_ai_response(request, new_session, new_message)

            assistant_message = ChatMessage.objects.create(
                session=new_session,
                role=ChatMessage.Role.ASSISTANT,
                content=rag_result['answer'],
                sources_cited=[s['id'] for s in rag_result['sources']]
            )

            logger.info(f"ChatBranchView.post: OK branch session={new_session.id} assistant_msg={assistant_message.id}")
            return Response({
                'session_id': new_session.id,
                'title': new_session.title,
                'parent_session_id': original_session.id,
                'message': {
                    'id': assistant_message.id,
                    'role': assistant_message.role,
                    'content': assistant_message.content,
                    'sources': rag_result['sources'],
                    'retrieved_docs': rag_result['retrieved_docs'],
                }
            })

        except Exception as e:
            logger.error(
                f"ChatBranchView.post FAILED: user={request.user.email} original_session={session_id} "
                f"branch_session={new_session.id} message_id={message_id} "
                f"new_message='{new_message[:100]}' error={e}",
                exc_info=True
            )
            new_session.delete()
            return Response(
                {'error': 'Errore durante la generazione della risposta'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatSessionsView(APIView):
    """
    List user's chat sessions.

    GET /api/ai/sessions/
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

    def get(self, request):
        sessions = ChatSession.objects.filter(user_email=request.user.email).order_by('-updated_at')[:50]
        return Response([
            {
                'id': s.id,
                'title': s.title or 'Nuova conversazione',
                'context': s.context,
                'created_at': s.created_at,
                'updated_at': s.updated_at,
                'message_count': s.messages.count(),
                'has_branches': s.branches.exists(),
            }
            for s in sessions
        ])


class KnowledgeSourcesView(APIView):
    """
    List knowledge sources (for admin/debugging).

    GET /api/ai/knowledge/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Staff only'}, status=403)

        sources = KnowledgeSource.objects.filter(is_active=True)
        return Response([
            {
                'id': s.id,
                'title': s.title,
                'source_type': s.source_type,
                'content_preview': s.content[:200],
            }
            for s in sources
        ])
