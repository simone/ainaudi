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


def execute_ai_function(function_name: str, args: dict, session, request) -> dict:
    """Execute an AI-requested function and return the result."""
    if function_name == 'suggest_incident_report':
        # Extract incident data from conversation
        try:
            from .vertex_service import vertex_ai_service

            # Build conversation transcript
            messages = session.messages.order_by('created_at')
            conversation = "\n\n".join([
                f"{'UTENTE' if msg.role == 'user' else 'ASSISTENTE'}: {msg.content}"
                for msg in messages
            ])

            # Get user's assigned sections with FULL details
            user_sections = []
            try:
                from delegations.models import DesignazioneRDL
                from territory.models import SezioneElettorale
                from elections.models import ConsultazioneElettorale

                consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
                if consultazione:
                    designazioni = DesignazioneRDL.objects.filter(
                        processo__consultazione=consultazione,
                        rdl_email=request.user.email,
                        stato='APPROVATA'
                    ).select_related('sezione', 'sezione__comune', 'sezione__municipio')

                    for des in designazioni:
                        sez = des.sezione
                        if sez:
                            user_sections.append({
                                'id': sez.numero,
                                'numero': sez.numero,
                                'comune': sez.comune.nome,
                                'municipio': sez.municipio.nome if sez.municipio else None,
                                'indirizzo': sez.indirizzo,
                                'denominazione': sez.denominazione
                            })
            except Exception as e:
                logger.warning(f"Error retrieving sections for incident: {e}")

            # Get user's full name
            user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email

            # Extract incident data
            incident_data = vertex_ai_service.extract_incident_from_conversation(
                conversation=conversation,
                user_sections=user_sections,
                user_name=user_name
            )

            # Format message
            category_labels = {
                'PROCEDURAL': 'Procedurale', 'ACCESS': 'Accesso al seggio',
                'MATERIALS': 'Materiali', 'INTIMIDATION': 'Intimidazione',
                'IRREGULARITY': 'Irregolarità', 'TECHNICAL': 'Tecnico', 'OTHER': 'Altro',
            }
            severity_labels = {
                'LOW': 'Bassa', 'MEDIUM': 'Media', 'HIGH': 'Alta', 'CRITICAL': 'Critica',
            }

            # Get full section details for display
            sezione_text = "Generale (non specifica a sezione)"
            sezione_detail = None
            if incident_data.get('sezione'):
                # Find section details from user_sections
                sezione_detail = next((s for s in user_sections if s['numero'] == incident_data['sezione']), None)
                if sezione_detail:
                    sezione_text = (
                        f"Sezione {sezione_detail['numero']} - {sezione_detail['comune']}"
                        f"{' ('+sezione_detail['municipio']+')' if sezione_detail.get('municipio') else ''}"
                        f"{' - '+sezione_detail['indirizzo'] if sezione_detail.get('indirizzo') else ''}"
                        f"{' ('+sezione_detail['denominazione']+')' if sezione_detail.get('denominazione') else ''}"
                    )
                else:
                    sezione_text = f"Sezione {incident_data['sezione']}"

            # Add verbalizzazione suggestion for section-specific incidents
            verbalizzazione_text = ""
            if sezione_detail:
                # Extract first 120 chars of description for verbale
                desc_short = incident_data['description'][:120] + "..." if len(incident_data['description']) > 120 else incident_data['description']
                verbalizzazione_text = f"\n\n📝 **Suggerimento per verbale:**\n_\"Alle ore [ora], {desc_short} Firma RDL.\"_\n\nRicorda di annotarlo sul registro di sezione se non l'hai già fatto."

            message = f"""Ecco la segnalazione che preparo:

📋 **Titolo:** {incident_data['title']}

📝 **Descrizione:** {incident_data['description']}

🏷️ **Categoria:** {category_labels.get(incident_data['category'], incident_data['category'])}

⚠️ **Gravità:** {severity_labels.get(incident_data['severity'], incident_data['severity'])}

🗳️ **Sezione:** {sezione_text}
{verbalizzazione_text}

Confermi? Rispondi "sì" e la creo."""

            # Store in session metadata
            session.metadata = session.metadata or {}
            session.metadata['pending_incident'] = incident_data
            session.save()

            return {'message': message, 'data': incident_data}

        except Exception as e:
            logger.error(f"Error in suggest_incident_report: {e}", exc_info=True)
            return {
                'message': '❌ Mi dispiace, ho avuto un problema nell\'analizzare la conversazione.',
                'data': None
            }

    elif function_name == 'create_incident_report':
        # Create incident from stored data
        pending_incident = session.metadata.get('pending_incident') if session.metadata else None

        if not pending_incident:
            return {
                'message': '❌ Non ho trovato dati di segnalazione pendenti. Riprova a descrivere il problema.',
                'data': None
            }

        try:
            from incidents.models import IncidentReport
            from elections.models import ConsultazioneElettorale

            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return {'message': '❌ Non c\'è una consultazione attiva al momento.', 'data': None}

            incident = IncidentReport.objects.create(
                consultazione=consultazione,
                sezione_id=pending_incident.get('sezione'),
                title=pending_incident['title'],
                description=pending_incident['description'],
                category=pending_incident['category'],
                severity=pending_incident['severity'],
                reporter=request.user,
                is_verbalizzato=False
            )

            # Save incident_id in session metadata and update title
            session.metadata['pending_incident'] = None
            session.metadata['incident_id'] = incident.id
            session.title = f"📋 {incident.title}"  # Update chat title with incident title
            session.save()

            # Add verbalizzazione reminder for section incidents
            verbale_reminder = ""
            if incident.sezione_id:
                verbale_reminder = "\n\n📝 **Ricorda:** Annota l'incidente sul registro di sezione se non l'hai già fatto. Puoi segnare come \"Verbalizzato\" nella scheda della segnalazione."

            return {
                'message': f'✅ **Segnalazione creata con successo!**\n\nID: {incident.id} | Clicca sull\'intestazione della chat per visualizzarla.{verbale_reminder}',
                'data': {'incident_id': incident.id}
            }

        except Exception as e:
            logger.error(f"Error in create_incident_report: {e}", exc_info=True)
            return {'message': f'❌ Errore nella creazione: {str(e)}', 'data': None}

    else:
        return {'message': f'⚠️ Funzione sconosciuta: {function_name}', 'data': None}


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

            # Get user's assigned sections with FULL details for incident context
            user_sections_context = ""
            user_sections_list = []
            try:
                from delegations.models import DesignazioneRDL
                from territory.models import SezioneElettorale
                from elections.models import ConsultazioneElettorale

                consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
                if consultazione:
                    designazioni = DesignazioneRDL.objects.filter(
                        processo__consultazione=consultazione,
                        rdl_email=request.user.email,
                        stato='APPROVATA'
                    ).select_related('sezione', 'sezione__comune', 'sezione__municipio')

                    for des in designazioni:
                        sez = des.sezione
                        if sez:
                            municipio_text = f" - {sez.municipio.nome}" if sez.municipio else ""
                            indirizzo_text = f" - {sez.indirizzo}" if sez.indirizzo else ""
                            denominazione_text = f" ({sez.denominazione})" if sez.denominazione else ""

                            section_info = {
                                'id': sez.numero,
                                'numero': sez.numero,
                                'comune': sez.comune.nome,
                                'municipio': sez.municipio.nome if sez.municipio else None,
                                'indirizzo': sez.indirizzo,
                                'denominazione': sez.denominazione
                            }
                            user_sections_list.append(section_info)

                    if user_sections_list:
                        sections_text = "\n".join([
                            f"- Sezione {s['numero']} - {s['comune']}{' ('+s['municipio']+')' if s['municipio'] else ''}{' - '+s['indirizzo'] if s['indirizzo'] else ''}{' ('+s['denominazione']+')' if s['denominazione'] else ''}"
                            for s in user_sections_list
                        ])
                        user_sections_context = f"\n\nSEZIONI ASSEGNATE ALL'UTENTE:\n{sections_text}\n(Se l'utente ha UNA SOLA sezione, deducila automaticamente. Se ne ha MULTIPLE, chiedi quale.)\n"
            except Exception as e:
                logger.warning(f"Error retrieving user sections: {e}")

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
                    context_text = "\n\n---\n\n".join(context_parts) + user_sections_context
                else:
                    context_text = user_sections_context if user_sections_context else None
            except Exception as e:
                logger.warning(f"Error retrieving context: {e}")
                context_docs_list = []
                context_text = user_sections_context if user_sections_context else None

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
                    request=request
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
                f"ChatView.post FAILED: user={request.user.email} session={session.id} message='{message[:100]}' error={e}",
                exc_info=True
            )
            return Response(
                {'error': 'Errore durante la generazione della risposta'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
