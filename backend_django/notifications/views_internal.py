"""
Internal views called by Cloud Tasks.

These endpoints are NOT accessible by regular users. Authentication is
performed by checking App Engine-specific headers that are stripped
from external requests.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .services.fcm import send_push, send_email_notification

logger = logging.getLogger(__name__)


class InternalAuthMixin:
    """
    Authenticate internal requests from Cloud Tasks.

    On App Engine, Cloud Tasks requests include the header
    X-AppEngine-QueueName, which is stripped from external requests
    by the App Engine infrastructure.

    As fallback, accepts INTERNAL_API_SECRET header.
    """
    permission_classes = [AllowAny]

    def check_internal_auth(self, request):
        """Returns True if request is from Cloud Tasks or has valid secret."""
        # App Engine Cloud Tasks header (stripped from external requests)
        queue_name = request.META.get('HTTP_X_APPENGINE_QUEUENAME', '')
        if queue_name:
            return True

        # Fallback: shared secret
        secret = getattr(settings, 'INTERNAL_API_SECRET', '')
        if secret:
            auth_header = request.META.get('HTTP_X_INTERNAL_SECRET', '')
            if auth_header == secret:
                return True

        # In DEBUG mode, allow all (for local testing)
        if settings.DEBUG:
            return True

        return False


class SendEventNotificationsView(InternalAuthMixin, APIView):
    """
    POST /api/internal/send-event-notifications/{event_id}/

    Called by Cloud Task to send notifications for an event at a specific offset.

    This endpoint is called ONCE per offset (24h, 2h, 10min before event).
    It determines recipients based on event territory filters and sends to all.

    Request body: offset parameters (hours, days, minutes, label)

    Response:
    - 200: Notifications sent (or skipped if event inactive)
    - 404: Event not found
    - 500: Temporary error (Cloud Tasks will retry)
    """
    authentication_classes = []

    def post(self, request, event_id):
        # Auth check
        if not self.check_internal_auth(request):
            logger.warning('Unauthorized internal request')
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .models import Event
        from .services.fcm import send_push_to_token
        from core.models import User
        from data.models import SectionAssignment
        from delegations.models import Delegato, SubDelega
        from django.db.models import Q

        # 1. Load event
        try:
            event = Event.objects.select_related('consultazione').prefetch_related(
                'regioni', 'province', 'comuni'
            ).get(pk=event_id)
        except Event.DoesNotExist:
            logger.info(f'Event {event_id} not found, no-op')
            return Response({'status': 'not_found'})

        # 2. Event still active?
        if event.status != Event.Status.ACTIVE:
            logger.info(f'Event {event_id} not ACTIVE (status={event.status}), no-op')
            return Response({'status': 'cancelled'})

        # 3. Determine recipient emails based on territory filters
        user_emails = set()

        if event.consultazione:
            # Build territorial filters if event has territory constraints
            territory_filter = Q()
            has_territory_filter = (
                event.regioni.exists() or
                event.province.exists() or
                event.comuni.exists()
            )

            if has_territory_filter:
                # Filter by territory
                territory_filter = (
                    Q(rdl_registration__comune__provincia__regione__in=event.regioni.all()) |
                    Q(rdl_registration__comune__provincia__in=event.province.all()) |
                    Q(rdl_registration__comune__in=event.comuni.all())
                )

            # RDLs
            rdl_query = SectionAssignment.objects.filter(
                consultazione=event.consultazione,
            )
            if has_territory_filter:
                rdl_query = rdl_query.filter(territory_filter)

            rdl_emails = rdl_query.values_list(
                'rdl_registration__email', flat=True
            ).distinct()
            user_emails.update(e for e in rdl_emails if e)

            # Delegati (no territory constraints)
            delegato_emails = Delegato.objects.filter(
                consultazione=event.consultazione,
            ).values_list('email', flat=True)
            user_emails.update(e for e in delegato_emails if e)

            # SubDelegati (no territory constraints)
            sub_emails = SubDelega.objects.filter(
                delegato__consultazione=event.consultazione,
                is_attiva=True,
            ).values_list('email', flat=True)
            user_emails.update(e for e in sub_emails if e)

        if not user_emails:
            logger.info(f'No recipients for event {event_id}')
            return Response({
                'status': 'no_recipients',
                'sent': 0,
            })

        # 4. Get users and their device tokens
        users = User.objects.filter(email__in=user_emails, is_active=True).prefetch_related(
            'device_tokens'
        )

        # 5. Send push to all tokens
        offset_label = request.data.get('label', 'Notification')
        title = event.title
        body = f'{offset_label}: {event.title}'
        deep_link = f'/events/{event_id}'

        sent_count = 0
        failed_count = 0

        for user in users:
            for device_token in user.device_tokens.filter(is_active=True):
                ok = send_push_to_token(
                    token=device_token.token,
                    title=title,
                    body=body,
                    data={'deep_link': deep_link, 'type': 'event'},
                    ttl=None,  # No TTL for scheduled notifications
                )
                if ok:
                    sent_count += 1
                else:
                    failed_count += 1

        logger.info(
            f'Sent event {event_id} notifications: '
            f'{sent_count} sent, {failed_count} failed '
            f'to {len(list(users))} users'
        )

        return Response({
            'status': 'sent',
            'sent': sent_count,
            'failed': failed_count,
        })


class SendNotificationView(InternalAuthMixin, APIView):
    """
    POST /api/internal/send-notification/

    Called by Cloud Tasks to send a single notification.
    Idempotent: safe to call multiple times for the same notification.

    Request body: {"notification_id": "<uuid>"}

    Response:
    - 200: Notification processed (sent, cancelled, or skipped)
    - 400: Bad request (missing notification_id)
    - 403: Unauthorized
    - 500: Temporary error (Cloud Tasks will retry)
    """
    authentication_classes = []  # No JWT auth for internal endpoints

    def post(self, request):
        # Auth check
        if not self.check_internal_auth(request):
            logger.warning('Unauthorized internal request')
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification_id = request.data.get('notification_id')
        if not notification_id:
            return Response(
                {'error': 'notification_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Load notification
        try:
            notification = Notification.objects.select_related(
                'user', 'event', 'section_assignment',
                'section_assignment__consultazione',
            ).get(pk=notification_id)
        except Notification.DoesNotExist:
            logger.info(f'Notification {notification_id} not found, no-op')
            return Response({'status': 'not_found'})

        # 2. Already processed?
        if notification.status != Notification.Status.SCHEDULED:
            logger.info(
                f'Notification {notification_id} already {notification.status}, no-op'
            )
            return Response({'status': 'already_processed'})

        # 3. Too early? (tolerance: 60 seconds)
        now = timezone.now()
        if notification.scheduled_at > now + timedelta(seconds=60):
            logger.info(
                f'Notification {notification_id} arrived too early '
                f'(scheduled: {notification.scheduled_at}, now: {now}), no-op'
            )
            return Response({'status': 'too_early'})

        # 4. Source still active?
        if not notification.is_source_active:
            notification.status = Notification.Status.CANCELLED
            notification.save(update_fields=['status', 'updated_at'])
            logger.info(f'Notification {notification_id} source inactive, cancelled')
            return Response({'status': 'cancelled'})

        # 5. Send based on channel
        push_ok = False
        email_ok = False

        try:
            channel = notification.channel

            if channel in (Notification.Channel.PUSH, Notification.Channel.BOTH):
                push_ok = send_push(notification)
                if not push_ok and channel == Notification.Channel.PUSH:
                    # Push-only failed, try email as fallback
                    email_ok = send_email_notification(notification)

            if channel in (Notification.Channel.EMAIL, Notification.Channel.BOTH):
                email_ok = send_email_notification(notification)

            # At least one channel succeeded?
            if push_ok or email_ok:
                notification.status = Notification.Status.SENT
                notification.sent_at = now
                notification.save(update_fields=['status', 'sent_at', 'updated_at'])
                logger.info(
                    f'Notification {notification_id} sent '
                    f'(push={push_ok}, email={email_ok})'
                )
                return Response({'status': 'sent', 'push': push_ok, 'email': email_ok})
            else:
                # No channel succeeded - mark as failed
                notification.status = Notification.Status.FAILED
                notification.save(update_fields=['status', 'updated_at'])
                logger.warning(f'Notification {notification_id} all channels failed')
                return Response({'status': 'failed'})

        except Exception as e:
            # Temporary error - return 500 so Cloud Tasks retries
            logger.error(
                f'Temporary error sending notification {notification_id}: {e}',
                exc_info=True
            )
            return Response(
                {'error': 'temporary_failure'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
