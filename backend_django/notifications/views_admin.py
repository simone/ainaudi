"""
Admin views for notifications management.

Endpoints for admin actions like starting notification campaigns
and managing events.
"""
import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSuperAdmin, CanManageDelegations
from elections.models import ConsultazioneElettorale

from .models import Event
from .serializers import EventSerializer
from .services.generator import generate_notifications_for_assignments

logger = logging.getLogger(__name__)


class StartAssignmentNotificationsView(APIView):
    """
    POST /api/admin/assignments/start-notifications/

    Generate notifications for all RDL section assignments in a consultation.
    Only accessible by admin or delegato.

    Body: {"consultazione_id": <int>}
    """
    permission_classes = [permissions.IsAuthenticated, CanManageDelegations]

    def post(self, request):
        consultazione_id = request.data.get('consultazione_id')
        if not consultazione_id:
            return Response(
                {'error': 'consultazione_id richiesto'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            consultazione = ConsultazioneElettorale.objects.get(pk=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            return Response(
                {'error': 'Consultazione non trovata'},
                status=status.HTTP_404_NOT_FOUND
            )

        result = generate_notifications_for_assignments(consultazione)

        logger.info(
            f'Admin {request.user.email} started assignment notifications '
            f'for consultation {consultazione_id}: {result}'
        )

        return Response({
            'message': (
                f'Create {result["notifications_created"]} notifiche '
                f'per {result["users_notified"]} RDL'
            ),
            **result,
        })


class EventCreateView(APIView):
    """
    POST /api/admin/events/

    Create a new event. Notifications are generated automatically
    via the Event post_save signal.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventUpdateView(APIView):
    """
    PUT /api/admin/events/<id>/

    Update an existing event. If dates or status change,
    notifications are regenerated via the Event post_save signal.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def put(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': 'Evento non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': 'Evento non trovato'},
                status=status.HTTP_404_NOT_FOUND
            )

        event.status = Event.Status.CANCELLED
        event.save()  # Signal will cancel scheduled notifications
        return Response(status=status.HTTP_204_NO_CONTENT)
