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
            except ChatSession.DoesNotExist:
                return Response({'error': 'Session not found'}, status=404)
        else:
            session = ChatSession.objects.create(
                user_email=request.user.email,
                context=context
            )

        # Save user message
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message
        )

        # === RAG IMPLEMENTATION ===
        try:
            rag_result = rag_service.answer_question(message, context)

            # Save assistant response with sources
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=rag_result['answer'],
                sources_cited=[s['id'] for s in rag_result['sources']]
            )

            return Response({
                'session_id': session.id,
                'message': {
                    'id': assistant_message.id,
                    'role': assistant_message.role,
                    'content': assistant_message.content,
                    'sources': rag_result['sources'],
                    'retrieved_docs': rag_result['retrieved_docs'],
                }
            })

        except Exception as e:
            logger.error(f"RAG error in chat: {e}", exc_info=True)
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
        sessions = ChatSession.objects.filter(user_email=request.user.email).order_by('-updated_at')[:20]
        return Response([
            {
                'id': s.id,
                'context': s.context,
                'created_at': s.created_at,
                'updated_at': s.updated_at,
                'message_count': s.messages.count(),
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
