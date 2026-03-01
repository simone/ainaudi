"""
Cloud Tasks integration for scheduled notifications.

Creates, cancels, and manages Cloud Tasks that trigger notification
delivery at the scheduled time.
"""
import json
import logging
from datetime import datetime

from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid loading Google Cloud libs when not configured
_client = None


def _get_client():
    """Lazy-init Cloud Tasks client."""
    global _client
    if _client is None:
        from google.cloud import tasks_v2
        _client = tasks_v2.CloudTasksClient()
    return _client


def _get_queue_path():
    """Build the full queue resource path."""
    return _get_client().queue_path(
        settings.CLOUD_TASKS_PROJECT,
        settings.CLOUD_TASKS_LOCATION,
        settings.CLOUD_TASKS_QUEUE,
    )


def _get_target_url(endpoint='send-notification'):
    """
    Build the target URL for an internal endpoint.

    On App Engine, uses the service's own URL.
    In dev, uses CLOUD_TASKS_TARGET_HOST.

    Args:
        endpoint: 'send-notification' (legacy) or 'send-event-notifications'
    """
    host = settings.CLOUD_TASKS_TARGET_HOST
    if not host:
        # Default to App Engine service URL
        project = settings.CLOUD_TASKS_PROJECT
        host = f'https://api-dot-{project}.ew.r.appspot.com'
    return f'{host}/api/internal/{endpoint}/'


def create_notification_task(notification):
    """
    Create a Cloud Task to send a notification at the scheduled time.

    Args:
        notification: Notification model instance (must be saved with id)

    Returns:
        str: The full task name, or empty string if creation failed
    """
    if not settings.CLOUD_TASKS_PROJECT:
        logger.warning('CLOUD_TASKS_PROJECT not configured, skipping task creation')
        return ''

    try:
        from google.protobuf import timestamp_pb2

        client = _get_client()
        queue_path = _get_queue_path()
        target_url = _get_target_url()

        # Build the task
        task = {
            'http_request': {
                'http_method': 'POST',
                'url': target_url,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'notification_id': str(notification.id),
                }).encode(),
            },
        }

        # Set schedule time
        if notification.scheduled_at:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(notification.scheduled_at)
            task['schedule_time'] = timestamp

        # Add OIDC token for authentication (App Engine service account)
        service_account = settings.CLOUD_TASKS_SERVICE_ACCOUNT if hasattr(
            settings, 'CLOUD_TASKS_SERVICE_ACCOUNT'
        ) else None
        if service_account:
            task['http_request']['oidc_token'] = {
                'service_account_email': service_account,
                'audience': target_url,
            }

        response = client.create_task(parent=queue_path, task=task)
        task_name = response.name

        logger.info(
            f'Created Cloud Task: {task_name} '
            f'for notification {notification.id} '
            f'scheduled at {notification.scheduled_at}'
        )

        # Store task name on the notification
        notification.cloud_task_name = task_name
        notification.save(update_fields=['cloud_task_name', 'updated_at'])

        return task_name

    except Exception as e:
        logger.error(f'Failed to create Cloud Task for notification {notification.id}: {e}')
        return ''


def cancel_notification_task(notification):
    """
    Cancel a Cloud Task for a notification.

    Args:
        notification: Notification model instance with cloud_task_name set

    Returns:
        bool: True if cancelled successfully
    """
    if not notification.cloud_task_name:
        return True  # Nothing to cancel

    if not settings.CLOUD_TASKS_PROJECT:
        logger.warning('CLOUD_TASKS_PROJECT not configured, skipping task cancellation')
        return True

    try:
        client = _get_client()
        client.delete_task(name=notification.cloud_task_name)
        logger.info(f'Cancelled Cloud Task: {notification.cloud_task_name}')
        return True
    except Exception as e:
        # Task may have already executed or been deleted
        logger.warning(
            f'Could not cancel Cloud Task {notification.cloud_task_name}: {e}'
        )
        return False


def create_event_notification_task(event_id, offset, scheduled_at):
    """
    Create a single Cloud Task for an event at a specific offset.

    ARCHITECTURE: Creates ONE task per offset (24h, 2h, 10min before event).
    When the task triggers, it calls the backend with event_id and offset.
    The backend determines recipients and sends all notifications.

    Args:
        event_id: str - UUID of the event
        offset: dict - offset config (e.g., {'hours': -24, 'label': '24 ore prima'})
        scheduled_at: datetime - when to send the notification

    Returns:
        str: The full task name, or empty string if creation failed
    """
    if not settings.CLOUD_TASKS_PROJECT:
        logger.warning('CLOUD_TASKS_PROJECT not configured, skipping task creation')
        return ''

    try:
        from google.protobuf import timestamp_pb2

        client = _get_client()
        queue_path = _get_queue_path()
        target_url = _get_target_url('send-event-notifications')

        # Build the task
        task = {
            'http_request': {
                'http_method': 'POST',
                'url': f'{target_url}{event_id}/',
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'offset_hours': offset.get('hours', 0),
                    'offset_days': offset.get('days', 0),
                    'offset_minutes': offset.get('minutes', 0),
                    'label': offset.get('label', ''),
                }).encode(),
            },
        }

        # Set schedule time
        if scheduled_at:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(scheduled_at)
            task['schedule_time'] = timestamp

        # Add OIDC token for authentication (App Engine service account)
        service_account = getattr(settings, 'CLOUD_TASKS_SERVICE_ACCOUNT', None)
        if service_account:
            task['http_request']['oidc_token'] = {
                'service_account_email': service_account,
                'audience': target_url,
            }

        response = client.create_task(parent=queue_path, task=task)
        task_name = response.name

        logger.info(
            f'Created Cloud Task: {task_name} '
            f'for event {event_id} offset={offset.get("label")} '
            f'scheduled at {scheduled_at}'
        )

        return task_name

    except Exception as e:
        logger.error(
            f'Failed to create Cloud Task for event {event_id}: {e}',
            exc_info=True
        )
        return ''


def cancel_and_regenerate_for_event(event):
    """
    Cancel all SCHEDULED notifications for an event and regenerate if still active.

    Called when an event's date or status changes.
    """
    from .generator import generate_notifications_for_event
    from notifications.models import Notification

    # Cancel existing SCHEDULED notifications
    scheduled = Notification.objects.filter(
        event=event,
        status=Notification.Status.SCHEDULED,
    )
    cancelled_count = 0
    for notif in scheduled:
        cancel_notification_task(notif)
        notif.status = Notification.Status.CANCELLED
        cancelled_count += 1

    if cancelled_count:
        Notification.objects.filter(
            event=event,
            status=Notification.Status.SCHEDULED,
        ).update(status=Notification.Status.CANCELLED)
        logger.info(f'Cancelled {cancelled_count} notifications for event {event.id}')

    # Regenerate if event is still active and in the future
    from django.utils import timezone
    if event.status == 'ACTIVE' and event.start_at > timezone.now():
        generate_notifications_for_event(event)


def cancel_notifications_for_consultation(consultazione):
    """
    Cancel all SCHEDULED assignment notifications for a consultation.

    Called when consultation dates change.
    """
    from notifications.models import Notification

    scheduled = Notification.objects.filter(
        section_assignment__consultazione=consultazione,
        status=Notification.Status.SCHEDULED,
    )
    cancelled_count = 0
    for notif in scheduled:
        cancel_notification_task(notif)
        cancelled_count += 1

    if cancelled_count:
        scheduled.update(status=Notification.Status.CANCELLED)
        logger.info(
            f'Cancelled {cancelled_count} assignment notifications '
            f'for consultation {consultazione.id}'
        )
