"""
Views for AI Assistant endpoints with RAG implementation.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
import logging

from core.permissions import CanAskToAIAssistant
from .models import KnowledgeSource, ChatSession, ChatMessage
from .rag_service import rag_service

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
    """Write an AuditLog entry for incident operations."""
    try:
        from core.models import AuditLog
        AuditLog.objects.create(
            user_email=user.email,
            action=action,
            target_model='IncidentReport',
            target_id=str(incident.id),
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


def execute_ai_function(function_name: str, args: dict, session, request, user_sections_list=None) -> dict:
    """Execute an AI-requested function and return the result."""

    valid_categories = ['PROCEDURAL', 'ACCESS', 'MATERIALS', 'INTIMIDATION', 'IRREGULARITY', 'TECHNICAL', 'OTHER']
    valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

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


class ChatView(APIView):
    """
    Send a message to the AI assistant or retrieve session history.

    POST /api/ai/chat/
    {
        "session_id": 1,  // optional, creates new if not provided
        "message": "Come si compila la scheda del referendum?",
        "context": "SCRUTINY"  // optional
    }

    GET /api/ai/chat/?session_id=1
    Returns all messages in the session
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

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

        # Get all messages in chronological order
        messages = session.messages.order_by('created_at')

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
                    ] if msg.sources_cited else []
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

        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message
        )

        # === RAG with AGENTIC TOOLS (Function Calling) ===
        try:
            logger.debug(f"ChatView.post: calling RAG with tools for session={session.id}")

            from .tools import incident_management_tools
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
                from delegations.models import DesignazioneRDL, DelegatoDiLista, SubDelega
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
                    is_delegato = DelegatoDiLista.objects.filter(
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
                    profile_parts.append(f"CONSULTAZIONE ATTIVA: {consultazione.nome} (dal {consultazione.data_inizio.strftime('%d/%m/%Y') if consultazione.data_inizio else '?'} al {consultazione.data_fine.strftime('%d/%m/%Y') if consultazione.data_fine else '?'})")

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
            except Exception as e:
                logger.warning(f"Error retrieving user context: {e}")
                user_profile_context = f"PROFILO UTENTE: {request.user.email}"

            # Get RAG context (retrieve similar documents)
            from pgvector.django import CosineDistance
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
                context_docs_list = []
                context_text = user_profile_context

            # Generate with tools - may return text OR function call
            ai_response = vertex_ai_service.generate_with_tools(
                conversation_history=conversation_history,
                context=context_text,
                tools=incident_management_tools
            )

            # Handle function call if present
            if ai_response['function_call']:
                function_name = ai_response['function_call']['name']
                function_args = ai_response['function_call']['args']
                logger.info(f"AI called function: {function_name} with args: {function_args}")

                # Execute the function
                function_result = execute_ai_function(
                    function_name,
                    function_args,
                    session=session,
                    request=request,
                    user_sections_list=user_sections_list,
                )

                # Save function result as assistant message
                assistant_message = ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=function_result['message'],
                    sources_cited=[]
                )

                rag_result = {
                    'answer': function_result['message'],
                    'sources': [],
                    'retrieved_docs': 0
                }
            else:
                # Normal text response (only 1 most relevant source IF highly relevant)
                # Only show source if distance <= 0.35 (similarity >= 65%) to avoid irrelevant citations
                relevant_sources = []
                if context_docs_list and context_docs_list[0].distance <= 0.35:
                    doc = context_docs_list[0]
                    relevant_sources = [{
                        'id': doc.id,
                        'title': doc.title,
                        'type': doc.source_type,
                        'url': doc.source_url.strip() if doc.source_url and doc.source_url.strip() else None
                    }]

                rag_result = {
                    'answer': ai_response['content'],
                    'sources': relevant_sources,
                    'retrieved_docs': len(context_docs_list) if context_docs_list else 0
                }

                # Save assistant response with sources
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
            return Response({
                'session_id': session.id,
                'title': session.title,
                'user_message': {
                    'id': user_message.id,
                    'role': user_message.role,
                    'content': user_message.content,
                },
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

        # Generate AI response for the edited message
        try:
            logger.debug(f"ChatBranchView.post: calling RAG for branch session={new_session.id}")
            rag_result = rag_service.answer_question(new_message, original_session.context, session=new_session)
            logger.debug(f"ChatBranchView.post: RAG returned {rag_result['retrieved_docs']} docs, answer_len={len(rag_result['answer'])}")

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
