"""
Signals for notifications app.

Auto-generates notifications when Events are created/modified.
Cancels and regenerates notifications when dates/status change.
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Event

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Event)
def cache_event_old_state(sender, instance, **kwargs):
    """Cache old state before save for change detection."""
    if instance.pk:
        try:
            old = Event.objects.get(pk=instance.pk)
            instance._old_start_at = old.start_at
            instance._old_end_at = old.end_at
            instance._old_status = old.status
            instance._old_external_url = old.external_url
        except Event.DoesNotExist:
            instance._old_start_at = None
    else:
        instance._old_start_at = None


@receiver(post_save, sender=Event)
def handle_event_save(sender, instance, created, **kwargs):
    """
    Generate or regenerate notifications when an Event is created/modified.

    On create: generates notifications for all users of the consultation.
    On update (date/status change): cancels old notifications and regenerates.
    """
    from .services.generator import generate_notifications_for_event
    from .services.cloud_tasks import cancel_and_regenerate_for_event

    if created:
        logger.info(f'Event created: {instance.title} (id={instance.pk})')
        generate_notifications_for_event(instance)
    else:
        old_start = getattr(instance, '_old_start_at', None)
        old_status = getattr(instance, '_old_status', None)

        date_changed = old_start and old_start != instance.start_at
        status_changed = old_status and old_status != instance.status

        if date_changed or status_changed:
            logger.info(
                f'Event modified: {instance.title} '
                f'(date_changed={date_changed}, status_changed={status_changed})'
            )
            cancel_and_regenerate_for_event(instance)
