"""
Event publisher for PDF generation using Redis Pub/Sub.
"""
import uuid
import redis
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client instance."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )


def publish_preview_pdf_and_email(review_token, email_to, subject, pdf_data, template_name):
    """
    Publish PREVIEW_PDF_AND_EMAIL event (self-contained).

    Args:
        review_token: Signed token for confirmation
        email_to: Recipient email(s) - string or list
        subject: Email subject
        pdf_data: Dict with PDF generation data
        template_name: Template identifier

    Returns:
        str: Event ID (UUID)
    """
    event_id = str(uuid.uuid4())

    event = {
        'event_type': 'PREVIEW_PDF_AND_EMAIL',
        'event_id': event_id,
        'payload': {
            'review_token': review_token,
            'email': {
                'to': email_to if isinstance(email_to, list) else [email_to],
                'subject': subject,
                'from': settings.DEFAULT_FROM_EMAIL,
            },
            'pdf': {
                'template': template_name,
                'data': pdf_data,
            },
            'confirm_url': f"{settings.FRONTEND_URL}/pdf/confirm?token={review_token}",
        }
    }

    try:
        client = get_redis_client()
        client.publish(settings.REDIS_PDF_EVENT_CHANNEL, json.dumps(event))
        logger.info(f"Published PREVIEW_PDF_AND_EMAIL event {event_id} for token {review_token}")
        return event_id
    except Exception as e:
        logger.error(f"Failed to publish event {event_id}: {e}", exc_info=True)
        raise


def publish_confirm_freeze(review_token):
    """
    Publish CONFIRM_FREEZE audit event (non-critical).

    Args:
        review_token: Token that was confirmed

    Returns:
        str: Event ID (UUID) or None if failed
    """
    event_id = str(uuid.uuid4())
    event = {
        'event_type': 'CONFIRM_FREEZE',
        'event_id': event_id,
        'payload': {'review_token': review_token}
    }

    try:
        client = get_redis_client()
        client.publish(settings.REDIS_PDF_EVENT_CHANNEL, json.dumps(event))
        logger.info(f"Published CONFIRM_FREEZE event {event_id} for token {review_token}")
        return event_id
    except Exception as e:
        logger.warning(f"Failed to publish audit event {event_id}: {e}")
        return None  # Non-blocking
