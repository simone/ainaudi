"""
Event-driven PDF worker: consumes Redis Pub/Sub events.
"""
import redis
import json
import logging
import signal
import os
from generate_adapter import generate_pdf_from_template
from email_sender import send_preview_email

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_CHANNEL = os.environ.get('REDIS_PDF_EVENT_CHANNEL', 'pdf_events')


class GracefulKiller:
    """Handle shutdown signals gracefully."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        logger.info("Shutdown signal received")
        self.kill_now = True


def handle_event(event_data):
    """
    Process a single event.

    Args:
        event_data: Dict with event_type, event_id, and payload
    """
    event_type = event_data.get('event_type')
    event_id = event_data.get('event_id')
    payload = event_data.get('payload', {})

    logger.info(f"Processing {event_type} event {event_id}")

    if event_type == 'PREVIEW_PDF_AND_EMAIL':
        try:
            # Generate PDF
            pdf_bytes = generate_pdf_from_template(
                template_name=payload['pdf']['template'],
                data=payload['pdf']['data']
            )

            # Send email with attachment + confirmation link
            send_preview_email(
                to=payload['email']['to'],
                subject=payload['email']['subject'],
                from_email=payload['email']['from'],
                pdf_bytes=pdf_bytes,
                pdf_filename=f"{payload['pdf']['template']}.pdf",
                confirm_url=payload['confirm_url']
            )

            logger.info(f"Event {event_id} processed successfully")

        except Exception as e:
            logger.error(f"Event {event_id} failed: {e}", exc_info=True)
            # NO retry - fail silently per spec

    elif event_type == 'CONFIRM_FREEZE':
        # Audit only, no action
        logger.info(f"CONFIRM_FREEZE: {payload.get('review_token')}")

    else:
        logger.warning(f"Unknown event type: {event_type}")


def run_worker():
    """Main worker loop."""
    killer = GracefulKiller()
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )
    pubsub = client.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)

    logger.info(f"PDF Worker started, listening on {REDIS_CHANNEL}")
    logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}")

    try:
        for message in pubsub.listen():
            if killer.kill_now:
                logger.info("Shutting down gracefully...")
                break

            if message['type'] != 'message':
                continue

            try:
                event_data = json.loads(message['data'])
                handle_event(event_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {e}")
            except Exception as e:
                logger.error(f"Message processing error: {e}", exc_info=True)

    finally:
        pubsub.close()
        logger.info("Worker stopped")


if __name__ == '__main__':
    run_worker()
