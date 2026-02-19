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
                            'url': src.source_url if src.source_url else None,
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

        # === RAG IMPLEMENTATION ===
        try:
            logger.debug(f"ChatView.post: calling RAG for session={session.id}")
            rag_result = rag_service.answer_question(message, context, session=session)
            logger.debug(f"ChatView.post: RAG returned {rag_result['retrieved_docs']} docs, answer_len={len(rag_result['answer'])}")

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

        # Create new branch session
        new_session = ChatSession.objects.create(
            user_email=request.user.email,
            title=new_title,
            context=original_session.context,
            parent_session=original_session
        )
        logger.debug(f"ChatBranchView.post: created branch session={new_session.id} from session={session_id}")

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
