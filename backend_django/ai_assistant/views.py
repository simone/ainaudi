"""
Views for AI Assistant endpoints.

Note: Full implementation in Fase 6 with RAG and Anthropic/OpenAI integration.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from core.permissions import CanAskToAIAssistant
from .models import KnowledgeSource, ChatSession, ChatMessage


class ChatView(APIView):
    """
    Send a message to the AI assistant.

    POST /api/ai/chat/
    {
        "session_id": 1,  // optional, creates new if not provided
        "message": "Come si compila la scheda del referendum?",
        "context": "SCRUTINY"  // optional
    }
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

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

        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return Response({'error': 'Session not found'}, status=404)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                context=context
            )

        # Save user message
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message
        )

        # TODO: Implement RAG-based response generation
        # For now, return a placeholder response
        response_content = (
            "Mi dispiace, l'assistente AI non è ancora completamente implementato. "
            "Consulta le FAQ o contatta il supporto per assistenza."
        )

        # Save assistant response
        assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=response_content,
            sources_cited=[]
        )

        return Response({
            'session_id': session.id,
            'message': {
                'id': assistant_message.id,
                'role': assistant_message.role,
                'content': assistant_message.content,
                'sources': assistant_message.sources_cited,
            }
        })


class ChatSessionsView(APIView):
    """
    List user's chat sessions.

    GET /api/ai/sessions/
    """
    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

    def get(self, request):
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:20]
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
