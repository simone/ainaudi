"""
Views for notifications API endpoints.

User-facing endpoints for dashboard, events, assignments, and device tokens.
"""
import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from data.models import SectionAssignment
from elections.models import ConsultazioneElettorale

from .models import Event, DeviceToken
from .serializers import (
    EventSerializer, EventListSerializer,
    AssignmentSerializer, DeviceTokenSerializer,
    DashboardItemSerializer,
)


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


def get_user_territory_ids(user):
    """
    Get the set of comune/provincia/regione IDs for sections assigned to the user.
    Returns (comune_ids, provincia_ids, regione_ids).
    """
    assignments = SectionAssignment.objects.filter(
        rdl_registration__email=user.email,
    ).select_related(
        'sezione__comune__provincia__regione'
    )

    comune_ids = set()
    provincia_ids = set()
    regione_ids = set()

    for a in assignments:
        comune = a.sezione.comune
        comune_ids.add(comune.pk)
        if comune.provincia_id:
            provincia_ids.add(comune.provincia_id)
            if comune.provincia.regione_id:
                regione_ids.add(comune.provincia.regione_id)

    return comune_ids, provincia_ids, regione_ids


def filter_events_by_territory(events, user):
    """
    Filter events based on user's territory.
    Events without territory restrictions are visible to all.
    Events with territory restrictions are visible only if user has
    sections in those territories.

    Expects events to have regioni/province/comuni already prefetched.
    """
    # Get user territories
    comune_ids, provincia_ids, regione_ids = get_user_territory_ids(user)

    # Filter in Python using prefetched M2M data
    filtered = []
    for event in events:
        evt_regioni = set(event.regioni.values_list('pk', flat=True))
        evt_province = set(event.province.values_list('pk', flat=True))
        evt_comuni = set(event.comuni.values_list('pk', flat=True))

        # No territory filter → visible to all
        if not evt_regioni and not evt_province and not evt_comuni:
            filtered.append(event)
            continue

        # Check if user matches any territory
        if (evt_regioni & regione_ids or
                evt_province & provincia_ids or
                evt_comuni & comune_ids):
            filtered.append(event)

    return filtered


def get_user_sections_count(user, consultazione):
    """Count how many sections a user has assigned for a consultazione."""
    if not consultazione:
        return 0
    return SectionAssignment.objects.filter(
        consultazione=consultazione,
        rdl_registration__email=user.email,
    ).count()


class DashboardView(APIView):
    """
    GET /api/me/dashboard

    Returns upcoming events for the authenticated user,
    filtered by territory. Events drive the dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        urgent_threshold = now + timedelta(hours=48)

        try:
            # Upcoming events (ACTIVE, not yet ended)
            events_qs = Event.objects.filter(
                status=Event.Status.ACTIVE,
                end_at__gte=now,
            ).select_related('consultazione').prefetch_related(
                'regioni', 'province', 'comuni'
            ).order_by('start_at')[:20]

            # Filter by user territory
            events = filter_events_by_territory(list(events_qs), user)
        except Exception:
            # Graceful fallback: if M2M tables don't exist yet (migration pending),
            # show all events without territory filtering
            logger.warning('Territory filter failed, showing all events', exc_info=True)
            events = list(Event.objects.filter(
                status=Event.Status.ACTIVE,
                end_at__gte=now,
            ).select_related('consultazione').order_by('start_at')[:20])

        items = []
        for event in events[:10]:
            subtitle = event.description[:100] if event.description else ''

            # For consultazione events, enrich subtitle with section count
            if event.consultazione_id:
                n_sections = get_user_sections_count(user, event.consultazione)
                if n_sections > 0:
                    section_word = 'sezione assegnata' if n_sections == 1 else 'sezioni assegnate'
                    subtitle = f'{n_sections} {section_word}'

            items.append({
                'type': 'event',
                'id': str(event.id),
                'title': event.title,
                'subtitle': subtitle,
                'start_at': event.start_at,
                'end_at': event.end_at,
                'temporal_status': event.temporal_status,
                'deep_link': f'/events/{event.id}',
                'is_urgent': event.start_at <= urgent_threshold,
                'external_url': event.external_url or '',
                'has_consultazione': bool(event.consultazione_id),
            })

        serializer = DashboardItemSerializer(items, many=True)
        return Response(serializer.data)


class EventListView(APIView):
    """
    GET /api/me/events

    Returns all active events, optionally filtered by consultazione.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        events = Event.objects.filter(
            status=Event.Status.ACTIVE,
        ).prefetch_related('regioni', 'province', 'comuni').order_by('start_at')

        consultazione_id = request.query_params.get('consultazione')
        if consultazione_id:
            events = events.filter(consultazione_id=consultazione_id)

        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)


class EventDetailView(APIView):
    """
    GET /api/me/events/<id>

    Returns full event details with temporal status.
    If the event has a consultazione, includes user's assigned sections
    grouped by location address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, event_id):
        try:
            event = Event.objects.select_related('consultazione').get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': 'Evento non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EventSerializer(event, context={'request': request})
        return Response(serializer.data)


class AssignmentListView(APIView):
    """
    GET /api/me/assignments

    Returns the authenticated user's section assignments.
    Matches by email through rdl_registration.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        consultazione = get_consultazione_attiva()

        if not consultazione:
            return Response([])

        assignments = SectionAssignment.objects.filter(
            consultazione=consultazione,
            rdl_registration__email=user.email,
        ).select_related(
            'sezione', 'sezione__comune', 'sezione__municipio',
            'consultazione', 'rdl_registration'
        ).order_by('sezione__numero')

        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)


class AssignmentDetailView(APIView):
    """
    GET /api/me/assignments/<id>

    Returns full assignment details with derived fields.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, assignment_id):
        user = request.user

        try:
            assignment = SectionAssignment.objects.select_related(
                'sezione', 'sezione__comune', 'sezione__municipio',
                'consultazione', 'rdl_registration'
            ).get(
                pk=assignment_id,
                rdl_registration__email=user.email,
            )
        except SectionAssignment.DoesNotExist:
            return Response(
                {'error': 'Assegnazione non trovata'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data)


class DeviceTokenView(APIView):
    """
    POST /api/me/device-tokens - Register or update a device token
    DELETE /api/me/device-tokens/<id> - Deactivate a device token
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, token_id=None):
        if not token_id:
            return Response(
                {'error': 'Token ID richiesto'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            device_token = DeviceToken.objects.get(
                pk=token_id,
                user=request.user,
            )
        except DeviceToken.DoesNotExist:
            return Response(
                {'error': 'Token non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )

        device_token.is_active = False
        device_token.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
