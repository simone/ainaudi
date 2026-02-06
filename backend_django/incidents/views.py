"""
Views for incidents API endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import CanManageIncidents
from .models import IncidentReport, IncidentComment, IncidentAttachment
from .serializers import (
    IncidentReportSerializer, IncidentReportCreateSerializer,
    IncidentReportUpdateSerializer, IncidentReportListSerializer,
    IncidentCommentSerializer, IncidentCommentCreateSerializer,
    IncidentAttachmentSerializer,
)


class IncidentReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IncidentReport.

    GET /api/incidents/ - List all incidents
    GET /api/incidents/my/ - List user's own incidents
    POST /api/incidents/ - Create incident
    GET /api/incidents/{id}/ - Get incident detail
    PUT/PATCH /api/incidents/{id}/ - Update incident
    POST /api/incidents/{id}/resolve/ - Resolve incident
    POST /api/incidents/{id}/escalate/ - Escalate incident
    """
    queryset = IncidentReport.objects.select_related(
        'consultazione', 'sezione', 'sezione__comune',
        'reporter', 'resolved_by', 'assigned_to'
    ).prefetch_related('comments', 'attachments').all()
    permission_classes = [permissions.IsAuthenticated, CanManageIncidents]
    filterset_fields = [
        'consultazione', 'sezione', 'category', 'severity', 'status',
        'reporter', 'assigned_to'
    ]
    search_fields = ['title', 'description', 'sezione__comune__nome']

    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentReportCreateSerializer
        if self.action in ['update', 'partial_update']:
            return IncidentReportUpdateSerializer
        if self.action == 'list':
            return IncidentReportListSerializer
        return IncidentReportSerializer

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get incidents reported by current user."""
        incidents = self.queryset.filter(reporter=request.user)
        serializer = IncidentReportListSerializer(incidents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def assigned(self, request):
        """Get incidents assigned to current user."""
        incidents = self.queryset.filter(assigned_to=request.user)
        serializer = IncidentReportListSerializer(incidents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an incident."""
        incident = self.get_object()

        resolution = request.data.get('resolution', '')
        if not resolution:
            return Response(
                {'error': 'Resolution text required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        incident.status = IncidentReport.Status.RESOLVED
        incident.resolution = resolution
        incident.resolved_by = request.user
        incident.resolved_at = timezone.now()
        incident.save()

        serializer = IncidentReportSerializer(incident)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate an incident."""
        incident = self.get_object()

        incident.status = IncidentReport.Status.ESCALATED
        incident.severity = IncidentReport.Severity.CRITICAL
        incident.save()

        # Create internal comment about escalation
        IncidentComment.objects.create(
            incident=incident,
            author=request.user,
            content=f"Segnalazione escalata da {request.user.email}",
            is_internal=True
        )

        serializer = IncidentReportSerializer(incident)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an incident."""
        incident = self.get_object()

        if incident.status not in [IncidentReport.Status.RESOLVED, IncidentReport.Status.ESCALATED]:
            return Response(
                {'error': 'Incident must be resolved or escalated before closing'},
                status=status.HTTP_400_BAD_REQUEST
            )

        incident.status = IncidentReport.Status.CLOSED
        incident.save()

        serializer = IncidentReportSerializer(incident)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign incident to a user."""
        incident = self.get_object()

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        incident.assigned_to = user
        incident.status = IncidentReport.Status.IN_PROGRESS
        incident.save()

        # Create internal comment
        IncidentComment.objects.create(
            incident=incident,
            author=request.user,
            content=f"Segnalazione assegnata a {user.email}",
            is_internal=True
        )

        serializer = IncidentReportSerializer(incident)
        return Response(serializer.data)


class IncidentCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IncidentComment.

    GET /api/incidents/comments/ - List all comments
    POST /api/incidents/comments/ - Create comment
    """
    queryset = IncidentComment.objects.select_related('incident', 'author').all()
    permission_classes = [permissions.IsAuthenticated, CanManageIncidents]
    filterset_fields = ['incident', 'author', 'is_internal']

    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentCommentCreateSerializer
        return IncidentCommentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-staff users can't see internal comments
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_internal=False)
        return queryset


class IncidentAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IncidentAttachment.

    GET /api/incidents/attachments/ - List all attachments
    POST /api/incidents/attachments/ - Upload attachment
    DELETE /api/incidents/attachments/{id}/ - Delete attachment
    """
    queryset = IncidentAttachment.objects.select_related('incident', 'uploaded_by').all()
    serializer_class = IncidentAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageIncidents]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ['incident', 'file_type', 'uploaded_by']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
