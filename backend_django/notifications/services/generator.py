"""
Notification generator service.

Creates Notification records and Cloud Tasks for events and assignments.
"""
import logging
from datetime import timedelta, datetime, time

from django.conf import settings
from django.utils import timezone

from notifications.models import Event, Notification, DeviceToken

logger = logging.getLogger(__name__)


def _compute_scheduled_time(reference_dt, offset):
    """
    Compute the notification scheduled time from a reference datetime and offset config.

    Args:
        reference_dt: datetime - the event start_at or consultation start datetime
        offset: dict - e.g. {'hours': -24} or {'days': -3} or {'time': '07:30'}

    Returns:
        datetime or None if the computed time is in the past
    """
    now = timezone.now()

    if 'time' in offset:
        # Absolute time on the same day as reference
        h, m = offset['time'].split(':')
        # Use the reference date but with the specified time
        scheduled = timezone.make_aware(
            datetime.combine(reference_dt.date(), time(int(h), int(m))),
            timezone.get_current_timezone()
        )
    else:
        # Relative offset
        delta_kwargs = {}
        if 'days' in offset:
            delta_kwargs['days'] = offset['days']
        if 'hours' in offset:
            delta_kwargs['hours'] = offset['hours']
        if 'minutes' in offset:
            delta_kwargs['minutes'] = offset['minutes']
        scheduled = reference_dt + timedelta(**delta_kwargs)

    # Don't schedule in the past
    if scheduled <= now:
        return None

    return scheduled


def generate_notifications_for_event(event):
    """
    Generate notification records and Cloud Tasks for an event.

    Creates one notification per user per offset for the event.
    Users are determined by the event's consultazione (all RDLs + delegati).

    Args:
        event: Event model instance (must be ACTIVE with future start_at)

    Returns:
        int: Number of notifications created
    """
    from .cloud_tasks import create_notification_task
    from core.models import User
    from data.models import SectionAssignment
    from delegations.models import Delegato, SubDelega

    if event.status != Event.Status.ACTIVE:
        return 0

    if event.start_at <= timezone.now():
        return 0

    offsets = getattr(settings, 'EVENT_NOTIFICATION_OFFSETS', [
        {'hours': -24, 'label': '24 ore prima'},
        {'hours': -2, 'label': '2 ore prima'},
        {'minutes': -10, 'label': '10 minuti prima', 'only_if_url': True},
    ])

    # Collect target user emails
    user_emails = set()

    if event.consultazione:
        # RDLs assigned to sections in this consultation
        rdl_emails = SectionAssignment.objects.filter(
            consultazione=event.consultazione,
        ).values_list('rdl_registration__email', flat=True).distinct()
        user_emails.update(e for e in rdl_emails if e)

        # Delegati for this consultation
        delegato_emails = Delegato.objects.filter(
            consultazione=event.consultazione,
        ).values_list('email', flat=True)
        user_emails.update(e for e in delegato_emails if e)

        # SubDelegati for this consultation
        sub_emails = SubDelega.objects.filter(
            delegato__consultazione=event.consultazione,
            is_attiva=True,
        ).values_list('email', flat=True)
        user_emails.update(e for e in sub_emails if e)

    if not user_emails:
        logger.info(f'No users to notify for event {event.id}')
        return 0

    # Map emails to User objects
    users = User.objects.filter(email__in=user_emails, is_active=True)
    user_map = {u.email: u for u in users}

    created_count = 0

    for offset in offsets:
        # Skip URL-only offsets if no external URL
        if offset.get('only_if_url') and not event.external_url:
            continue

        scheduled_at = _compute_scheduled_time(event.start_at, offset)
        if not scheduled_at:
            continue  # In the past

        label = offset.get('label', '')

        for email in user_emails:
            user = user_map.get(email)
            if not user:
                continue

            notification = Notification.objects.create(
                user=user,
                event=event,
                title=f'{event.title}',
                body=f'{label}: {event.title}',
                deep_link=f'/events/{event.id}',
                scheduled_at=scheduled_at,
                channel=Notification.Channel.BOTH,
                status=Notification.Status.SCHEDULED,
            )

            # Create Cloud Task
            create_notification_task(notification)
            created_count += 1

    logger.info(
        f'Generated {created_count} notifications for event {event.id} '
        f'({len(user_emails)} users, {len(offsets)} offsets)'
    )
    return created_count


def generate_notifications_for_assignments(consultazione):
    """
    Generate notification records and Cloud Tasks for all section assignments
    in a consultation.

    Called when admin presses "Start notifications" for assignments.

    Args:
        consultazione: ConsultazioneElettorale model instance

    Returns:
        dict: {'notifications_created': int, 'users_notified': int}
    """
    from .cloud_tasks import create_notification_task
    from core.models import User
    from data.models import SectionAssignment

    offsets = getattr(settings, 'ASSIGNMENT_NOTIFICATION_OFFSETS', [
        {'days': -3, 'label': '3 giorni prima'},
        {'hours': -24, 'label': '24 ore prima'},
        {'hours': -2, 'label': '2 ore prima'},
        {'time': '07:30', 'label': 'Mattina stessa'},
    ])

    # Get all assignments for this consultation
    assignments = SectionAssignment.objects.filter(
        consultazione=consultazione,
    ).select_related(
        'sezione', 'sezione__comune', 'rdl_registration'
    )

    if not assignments.exists():
        return {'notifications_created': 0, 'users_notified': 0}

    # Collect unique emails and map to users
    emails = set(a.rdl_registration.email for a in assignments if a.rdl_registration and a.rdl_registration.email)
    users = User.objects.filter(email__in=emails, is_active=True)
    user_map = {u.email: u for u in users}

    # Reference datetime: consultation start date at midnight
    reference_dt = timezone.make_aware(
        datetime.combine(consultazione.data_inizio, time(7, 0)),
        timezone.get_current_timezone()
    )

    created_count = 0
    users_notified = set()

    for assignment in assignments:
        email = assignment.rdl_registration.email if assignment.rdl_registration else None
        if not email:
            continue

        user = user_map.get(email)
        if not user:
            continue

        sezione_desc = f'Sezione {assignment.sezione.numero}'
        if assignment.sezione.comune:
            sezione_desc += f' - {assignment.sezione.comune.nome}'

        for offset in offsets:
            scheduled_at = _compute_scheduled_time(reference_dt, offset)
            if not scheduled_at:
                continue

            label = offset.get('label', '')

            # Check for existing notification to avoid duplicates
            existing = Notification.objects.filter(
                user=user,
                section_assignment=assignment,
                scheduled_at=scheduled_at,
                status=Notification.Status.SCHEDULED,
            ).exists()

            if existing:
                continue

            notification = Notification.objects.create(
                user=user,
                section_assignment=assignment,
                title=f'Incarico: {sezione_desc}',
                body=f'{label}: il tuo seggio è {sezione_desc}. '
                     f'Indirizzo: {assignment.sezione.indirizzo or "da verificare"}',
                deep_link=f'/assignments/{assignment.id}',
                scheduled_at=scheduled_at,
                channel=Notification.Channel.BOTH,
                status=Notification.Status.SCHEDULED,
            )

            create_notification_task(notification)
            created_count += 1
            users_notified.add(email)

    logger.info(
        f'Generated {created_count} notifications for consultation '
        f'{consultazione.id} ({len(users_notified)} users)'
    )

    return {
        'notifications_created': created_count,
        'users_notified': len(users_notified),
    }
