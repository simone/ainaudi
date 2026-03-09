"""
Views for AI Assistant endpoints.

Thin API layer: validates input, manages sessions/messages, delegates
all AI logic to the ConversationOrchestrator.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
import logging

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from core.permissions import CanAskToAIAssistant
from .models import KnowledgeSource, ChatSession, ChatMessage, ChatAttachment
from .orchestrator import ConversationOrchestrator

logger = logging.getLogger(__name__)

# Singleton orchestrator
_orchestrator = ConversationOrchestrator()


def generate_session_title(first_message: str) -> str:
    """Generate a short title from the first user message using Gemini."""
    from .vertex_service import vertex_ai_service

    prompt = (
        'Genera un titolo brevissimo (max 6 parole) per questa conversazione, '
        "basandoti sulla domanda dell'utente.\n"
        "Il titolo deve essere descrittivo ma conciso, in italiano.\n\n"
        f'Domanda utente: "{first_message}"\n\n'
        "Rispondi SOLO con il titolo, senza virgolette, senza punteggiatura finale.\n"
        "Esempi:\n"
        '- "Come si compila la scheda?" -> "Compilazione scheda elettorale"\n'
        '- "Cosa fare se vedo irregolarita?" -> "Gestione irregolarita"\n'
        '- "Quali sono i miei diritti?" -> "Diritti e doveri RDL"'
    )

    try:
        title = vertex_ai_service.generate_response(prompt, context=None)
        title = title.strip().strip('"').strip("'").strip(".")
        if len(title) > 60:
            title = title[:57] + "..."
        return title
    except Exception as e:
        logger.error("Title generation failed: %s", e)
        words = first_message.split()[:6]
        return " ".join(words) + ("..." if len(words) == 6 else "")


def generate_ai_response(request, session, message, attachment_data=None):
    """
    Shared AI generation logic.

    Delegates to ConversationOrchestrator.generate_response.
    Kept as a module-level function for backward compatibility
    (used by telegram_bot.message_service).
    """
    return _orchestrator.generate_response(
        request, session, message, attachment_data=attachment_data
    )


class ChatView(APIView):
    """
    Send a message to the AI assistant or retrieve session history.

    POST /api/ai/chat/
    GET /api/ai/chat/?session_id=1
    """

    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """Retrieve messages from a session."""
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "session_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = ChatSession.objects.get(
                id=session_id, user_email=request.user.email
            )
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        messages = session.messages.order_by("created_at").prefetch_related(
            "attachments"
        )

        return Response(
            {
                "session_id": session.id,
                "title": session.title or "Nuova conversazione",
                "incident_id": (
                    session.metadata.get("incident_id") if session.metadata else None
                ),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at,
                        "sources": (
                            [
                                {
                                    "id": src.id,
                                    "title": src.title,
                                    "type": src.source_type,
                                    "url": (
                                        src.source_url.strip()
                                        if src.source_url and src.source_url.strip()
                                        else None
                                    ),
                                }
                                for src in KnowledgeSource.objects.filter(
                                    id__in=msg.sources_cited
                                )
                            ]
                            if msg.sources_cited
                            else []
                        ),
                        "attachments": [
                            {
                                "id": att.id,
                                "filename": att.filename,
                                "file_type": att.file_type,
                                "mime_type": att.mime_type,
                                "file_size": att.file_size,
                                "url": att.file.url if att.file else None,
                            }
                            for att in msg.attachments.all()
                        ],
                    }
                    for msg in messages
                ],
            }
        )

    def post(self, request):
        # Check feature flag
        if not settings.FEATURE_FLAGS.get("AI_ASSISTANT", False):
            return Response(
                {"error": "AI Assistant non abilitato"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        session_id = request.data.get("session_id")
        message = request.data.get("message")
        context = request.data.get("context")

        logger.info(
            "ChatView.post: user=%s session_id=%s context=%s message='%s'",
            request.user.email,
            session_id,
            context,
            message[:80] if message else None,
        )

        if not message:
            return Response(
                {"error": "message required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(message) > 2000:
            return Response(
                {"error": "Message too long (max 2000 characters)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(
                    id=session_id, user_email=request.user.email
                )
            except ChatSession.DoesNotExist:
                return Response({"error": "Session not found"}, status=404)
        else:
            session = ChatSession.objects.create(
                user_email=request.user.email, context=context
            )
            logger.info("ChatView.post: new session=%d", session.id)

        # Handle file attachment
        attachment_data = None
        attachment_file = request.FILES.get("attachment")
        if attachment_file:
            mime_type = attachment_file.content_type or ""
            supported_types = (
                ChatAttachment.SUPPORTED_IMAGE_TYPES
                | ChatAttachment.SUPPORTED_AUDIO_TYPES
            )
            if mime_type not in supported_types:
                return Response(
                    {
                        "error": (
                            f"Tipo file non supportato: {mime_type}. "
                            "Supportati: immagini (JPEG, PNG, GIF, WebP) "
                            "e audio (MP3, WAV, OGG, AAC, FLAC, M4A)."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if attachment_file.size > ChatAttachment.MAX_FILE_SIZE:
                max_mb = ChatAttachment.MAX_FILE_SIZE // (1024 * 1024)
                return Response(
                    {"error": f"File troppo grande (max {max_mb}MB)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            file_bytes = attachment_file.read()
            attachment_file.seek(0)
            attachment_data = [{"data": file_bytes, "mime_type": mime_type}]

        # Save user message
        user_message = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER, content=message
        )

        # Save attachment if present
        saved_attachment = None
        if attachment_file:
            saved_attachment = ChatAttachment.objects.create(
                message=user_message,
                file=attachment_file,
                file_type=ChatAttachment.detect_file_type(
                    attachment_file.content_type or ""
                ),
                mime_type=attachment_file.content_type or "",
                filename=attachment_file.name or "attachment",
                file_size=attachment_file.size,
            )

        # Generate AI response via orchestrator
        try:
            rag_result = generate_ai_response(
                request, session, message, attachment_data=attachment_data
            )

            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=rag_result["answer"],
                sources_cited=[s["id"] for s in rag_result["sources"]],
            )

            # Generate title for first message
            if session.messages.count() == 2 and not session.title:
                try:
                    session.title = generate_session_title(message)
                    session.save(update_fields=["title"])
                except Exception as e:
                    logger.warning("Title generation failed: %s", e)

            user_msg_data = {
                "id": user_message.id,
                "role": user_message.role,
                "content": user_message.content,
            }
            if saved_attachment:
                user_msg_data["attachments"] = [
                    {
                        "id": saved_attachment.id,
                        "filename": saved_attachment.filename,
                        "file_type": saved_attachment.file_type,
                        "mime_type": saved_attachment.mime_type,
                        "file_size": saved_attachment.file_size,
                        "url": (
                            saved_attachment.file.url if saved_attachment.file else None
                        ),
                    }
                ]

            response_data = {
                "session_id": session.id,
                "title": session.title,
                "user_message": user_msg_data,
                "message": {
                    "id": assistant_message.id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "sources": rag_result["sources"],
                    "retrieved_docs": rag_result["retrieved_docs"],
                },
            }

            # Include function_result so frontend can invalidate caches
            if rag_result.get("function_result"):
                response_data["function_result"] = rag_result["function_result"]

            return Response(response_data)

        except Exception as e:
            logger.error(
                "ChatView.post FAILED: user=%s session=%d error=%s: %s",
                request.user.email,
                session.id,
                type(e).__name__,
                e,
                exc_info=True,
            )

            error_content = (
                "Scusa, Ainaudino e un po' sovraccarico in questo momento e non riesce a rispondere. "
                "Riprova tra qualche secondo! Se il problema persiste, prova ad aprire una nuova conversazione."
            )
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=error_content,
                sources_cited=[],
            )

            return Response(
                {
                    "session_id": session.id,
                    "title": session.title,
                    "user_message": {
                        "id": user_message.id,
                        "role": user_message.role,
                        "content": user_message.content,
                    },
                    "message": {
                        "id": 0,
                        "role": "assistant",
                        "content": error_content,
                        "sources": [],
                        "retrieved_docs": 0,
                    },
                }
            )


class ChatBranchView(APIView):
    """
    Create a new chat branch by editing a message.

    POST /api/ai/chat/branch/
    """

    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

    def post(self, request):
        session_id = request.data.get("session_id")
        message_id = request.data.get("message_id")
        new_message = request.data.get("new_message")

        if not all([session_id, message_id, new_message]):
            return Response(
                {"error": "session_id, message_id, and new_message required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            original_session = ChatSession.objects.get(
                id=session_id, user_email=request.user.email
            )
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        try:
            edit_message = ChatMessage.objects.get(
                id=message_id,
                session=original_session,
                role=ChatMessage.Role.USER,
            )
        except ChatMessage.DoesNotExist:
            return Response(
                {"error": "Message not found or not a user message"}, status=404
            )

        try:
            new_title = generate_session_title(new_message)
        except Exception:
            new_title = f"Branch: {new_message[:50]}..."

        new_session = ChatSession.objects.create(
            user_email=request.user.email,
            title=new_title,
            context=original_session.context,
            parent_session=original_session,
            sezione=original_session.sezione,
            metadata=(
                original_session.metadata.copy() if original_session.metadata else {}
            ),
        )

        # Copy messages before the edited one
        messages_before = original_session.messages.filter(
            created_at__lt=edit_message.created_at
        ).order_by("created_at")

        for msg in messages_before:
            ChatMessage.objects.create(
                session=new_session,
                role=msg.role,
                content=msg.content,
                sources_cited=msg.sources_cited,
            )

        ChatMessage.objects.create(
            session=new_session,
            role=ChatMessage.Role.USER,
            content=new_message,
        )

        try:
            rag_result = generate_ai_response(request, new_session, new_message)

            assistant_message = ChatMessage.objects.create(
                session=new_session,
                role=ChatMessage.Role.ASSISTANT,
                content=rag_result["answer"],
                sources_cited=[s["id"] for s in rag_result["sources"]],
            )

            return Response(
                {
                    "session_id": new_session.id,
                    "title": new_session.title,
                    "parent_session_id": original_session.id,
                    "message": {
                        "id": assistant_message.id,
                        "role": assistant_message.role,
                        "content": assistant_message.content,
                        "sources": rag_result["sources"],
                        "retrieved_docs": rag_result["retrieved_docs"],
                    },
                }
            )

        except Exception as e:
            logger.error(
                "ChatBranchView.post FAILED: user=%s session=%d error=%s",
                request.user.email,
                new_session.id,
                e,
                exc_info=True,
            )
            new_session.delete()
            return Response(
                {"error": "Errore durante la generazione della risposta"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatSessionsView(APIView):
    """
    List user's chat sessions.

    GET /api/ai/sessions/
    """

    permission_classes = [permissions.IsAuthenticated, CanAskToAIAssistant]

    def get(self, request):
        sessions = ChatSession.objects.filter(
            user_email=request.user.email
        ).order_by("-updated_at")[:50]
        return Response(
            [
                {
                    "id": s.id,
                    "title": s.title or "Nuova conversazione",
                    "context": s.context,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "message_count": s.messages.count(),
                    "has_branches": s.branches.exists(),
                }
                for s in sessions
            ]
        )


class KnowledgeSourcesView(APIView):
    """
    List knowledge sources (for admin/debugging).

    GET /api/ai/knowledge/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({"error": "Staff only"}, status=403)

        sources = KnowledgeSource.objects.filter(is_active=True)
        return Response(
            [
                {
                    "id": s.id,
                    "title": s.title,
                    "source_type": s.source_type,
                    "content_preview": s.content[:200],
                }
                for s in sources
            ]
        )
