"""
Views for notifications API endpoints.

User-facing endpoints for dashboard, events, assignments, and device tokens.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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


class DashboardView(APIView):
    """
    GET /api/me/dashboard

    Returns the next 5 upcoming items (events + assignments) for the
    authenticated user, ordered by start date.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        today = now.date()
        urgent_threshold = now + timedelta(hours=48)

        items = []

        # Upcoming events (ACTIVE, not yet ended)
        events = Event.objects.filter(
            status=Event.Status.ACTIVE,
            end_at__gte=now,
        ).order_by('start_at')[:10]

        for event in events:
            items.append({
                'type': 'event',
                'id': str(event.id),
                'title': event.title,
                'subtitle': event.description[:100] if event.description else '',
                'start_at': event.start_at,
                'end_at': event.end_at,
                'temporal_status': event.temporal_status,
                'deep_link': f'/events/{event.id}',
                'is_urgent': event.start_at <= urgent_threshold,
                'external_url': event.external_url or '',
            })

        # User's assignments (via RdlRegistration email match)
        consultazione = get_consultazione_attiva()
        if consultazione and consultazione.data_fine >= today:
            assignments = SectionAssignment.objects.filter(
                consultazione=consultazione,
                rdl_registration__email=user.email,
            ).select_related(
                'sezione', 'sezione__comune', 'sezione__municipio',
                'consultazione'
            )

            for assignment in assignments:
                start_dt = timezone.make_aware(
                    timezone.datetime.combine(consultazione.data_inizio, timezone.datetime.min.time())
                )
                end_dt = timezone.make_aware(
                    timezone.datetime.combine(consultazione.data_fine, timezone.datetime.max.time())
                )
                items.append({
                    'type': 'assignment',
                    'id': str(assignment.id),
                    'title': f'Sezione {assignment.sezione.numero} - {assignment.sezione.comune.nome}',
                    'subtitle': assignment.sezione.indirizzo or '',
                    'start_at': start_dt,
                    'end_at': end_dt,
                    'temporal_status': 'FUTURO' if today < consultazione.data_inizio
                        else ('IN_CORSO' if today <= consultazione.data_fine else 'CONCLUSO'),
                    'deep_link': f'/assignments/{assignment.id}',
                    'is_urgent': consultazione.data_inizio <= (today + timedelta(days=2)),
                    'external_url': '',
                })

        # Sort by start_at, take first 5
        items.sort(key=lambda x: x['start_at'])
        items = items[:5]

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
        ).order_by('start_at')

        consultazione_id = request.query_params.get('consultazione')
        if consultazione_id:
            events = events.filter(consultazione_id=consultazione_id)

        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)


class EventDetailView(APIView):
    """
    GET /api/me/events/<id>

    Returns full event details with temporal status.
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

        serializer = EventSerializer(event)
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
