"""
Message forwarding service.

Bridges Telegram messages to the internal Ainaudi AI conversation system.
Uses the same generate_ai_response pipeline as the web app.
"""
import logging
from django.utils import timezone

from ai_assistant.models import ChatSession, ChatMessage
from ai_assistant.views import generate_ai_response
from core.models import AuditLog
from .models import TelegramIdentityBinding, ExternalChannelConversationLink

logger = logging.getLogger(__name__)


class _FakeRequest:
    """
    Minimal request-like object to satisfy generate_ai_response's interface.
    The AI pipeline accesses request.user and request.META.
    """

    def __init__(self, user):
        self.user = user
        self.META = {'REMOTE_ADDR': '0.0.0.0'}


def get_or_create_conversation(
    binding: TelegramIdentityBinding,
) -> ChatSession:
    """
    Get the current active Telegram conversation or create a new one.
    Links it via ExternalChannelConversationLink.
    """
    link = ExternalChannelConversationLink.objects.filter(
        channel='telegram',
        telegram_user_id=binding.telegram_user_id,
        telegram_chat_id=binding.telegram_chat_id,
        user=binding.user,
    ).select_related('conversation').order_by('-updated_at').first()

    if link:
        return link.conversation

    # Create new session
    session = ChatSession.objects.create(
        user_email=binding.user.email,
        context='TELEGRAM',
    )

    ExternalChannelConversationLink.objects.create(
        channel='telegram',
        telegram_chat_id=binding.telegram_chat_id,
        telegram_user_id=binding.telegram_user_id,
        conversation=session,
        user=binding.user,
    )

    logger.info(
        "New Telegram conversation created: session=%s tg_user=%s user=%s",
        session.id, binding.telegram_user_id, binding.user.email,
    )
    return session


def forward_message_to_backend(
    binding: TelegramIdentityBinding,
    message_text: str,
    telegram_message_id: int | None = None,
) -> str:
    """
    Forward a Telegram text message to the AI backend and return the reply.

    1. Get/create internal conversation
    2. Save user message
    3. Call generate_ai_response (same pipeline as web)
    4. Save assistant response
    5. Return reply text
    """
    session = get_or_create_conversation(binding)
    user = binding.user

    # Save the user message
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=message_text,
    )

    # Generate AI response using the existing pipeline
    fake_request = _FakeRequest(user)

    try:
        rag_result = generate_ai_response(fake_request, session, message_text)

        # Save assistant message
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=rag_result['answer'],
            sources_cited=[s['id'] for s in rag_result['sources']],
        )

        # Generate title for new conversations
        if session.messages.count() == 2 and not session.title:
            try:
                from ai_assistant.views import generate_session_title
                session.title = generate_session_title(message_text)
                session.save(update_fields=['title'])
            except Exception:
                pass

        # Audit
        try:
            AuditLog.objects.create(
                user_email=user.email,
                action='SUBMIT_DATA',
                target_model='ChatMessage',
                target_id=str(session.id),
                details={
                    'channel': 'telegram',
                    'telegram_user_id': binding.telegram_user_id,
                    'telegram_chat_id': binding.telegram_chat_id,
                    'telegram_message_id': telegram_message_id,
                    'session_id': session.id,
                },
            )
        except Exception as e:
            logger.warning("Telegram audit log failed: %s", e)

        # Update conversation link timestamp
        ExternalChannelConversationLink.objects.filter(
            channel='telegram',
            telegram_user_id=binding.telegram_user_id,
            conversation=session,
        ).update(updated_at=timezone.now())

        return rag_result['answer']

    except Exception as e:
        logger.error(
            "AI response generation failed for tg_user=%s session=%s: %s",
            binding.telegram_user_id, session.id, e,
            exc_info=True,
        )

        error_content = (
            "Scusa, Ainaudino non riesce a rispondere in questo momento. "
            "Riprova tra qualche secondo!"
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=error_content,
        )
        return error_content


def reset_conversation(binding: TelegramIdentityBinding) -> None:
    """Remove conversation links so the next message starts a fresh session."""
    ExternalChannelConversationLink.objects.filter(
        channel='telegram',
        telegram_user_id=binding.telegram_user_id,
        user=binding.user,
    ).delete()
