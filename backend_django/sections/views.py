"""
Views for sections API endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import SectionAssignment, DatiSezione, DatiScheda, SectionDataHistory
from .serializers import (
    SectionAssignmentSerializer, SectionAssignmentCreateSerializer,
    DatiSezioneSerializer, DatiSezioneUpdateSerializer, DatiSezioneListSerializer,
    DatiSchedaSerializer, DatiSchedaUpdateSerializer,
    SectionDataHistorySerializer,
)


class SectionAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SectionAssignment.

    GET /api/sections/assignments/ - List all assignments
    GET /api/sections/assignments/my/ - List user's own assignments
    POST /api/sections/assignments/ - Create assignment
    DELETE /api/sections/assignments/{id}/ - Delete assignment
    """
    queryset = SectionAssignment.objects.select_related(
        'sezione', 'sezione__comune', 'sezione__comune__provincia',
        'consultazione', 'user', 'assigned_by'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['consultazione', 'sezione', 'user', 'role', 'is_active']
    search_fields = ['user__email', 'sezione__comune__nome']

    def get_serializer_class(self):
        if self.action == 'create':
            return SectionAssignmentCreateSerializer
        return SectionAssignmentSerializer

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's assignments."""
        assignments = self.queryset.filter(
            user=request.user,
            is_active=True
        )
        serializer = SectionAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()


class DatiSezioneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DatiSezione.

    GET /api/sections/dati/ - List all section data
    GET /api/sections/dati/my/ - List user's own sections data
    GET /api/sections/dati/{id}/ - Get section data detail
    PUT/PATCH /api/sections/dati/{id}/ - Update section data
    POST /api/sections/dati/{id}/verify/ - Verify section data
    """
    queryset = DatiSezione.objects.select_related(
        'sezione', 'sezione__comune', 'sezione__comune__provincia',
        'consultazione', 'inserito_da', 'verified_by'
    ).prefetch_related('schede', 'schede__scheda').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['consultazione', 'sezione', 'is_complete', 'is_verified']
    search_fields = ['sezione__comune__nome', 'sezione__numero']

    def get_serializer_class(self):
        if self.action == 'list':
            return DatiSezioneListSerializer
        if self.action in ['update', 'partial_update']:
            return DatiSezioneUpdateSerializer
        return DatiSezioneSerializer

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get section data for user's assigned sections."""
        # Get user's assigned sections
        assigned_sections = SectionAssignment.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('sezione_id', flat=True)

        dati = self.queryset.filter(sezione_id__in=assigned_sections)
        serializer = DatiSezioneSerializer(dati, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark section data as verified."""
        dati_sezione = self.get_object()

        # Check if user has permission to verify
        # TODO: Add proper permission check based on role

        dati_sezione.is_verified = True
        dati_sezione.verified_by = request.user
        dati_sezione.verified_at = timezone.now()
        dati_sezione.save()

        serializer = DatiSezioneSerializer(dati_sezione)
        return Response(serializer.data)


class DatiSchedaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DatiScheda.

    GET /api/sections/schede/ - List all ballot data
    GET /api/sections/schede/{id}/ - Get ballot data detail
    PUT/PATCH /api/sections/schede/{id}/ - Update ballot data
    """
    queryset = DatiScheda.objects.select_related(
        'dati_sezione', 'dati_sezione__sezione', 'scheda'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['dati_sezione', 'scheda', 'is_valid']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return DatiSchedaUpdateSerializer
        return DatiSchedaSerializer

    def perform_update(self, serializer):
        instance = self.get_object()

        # Store old values for history
        old_values = {
            'voti': str(instance.voti),
            'schede_bianche': str(instance.schede_bianche),
            'schede_nulle': str(instance.schede_nulle),
        }

        # Save the update
        updated_instance = serializer.save()

        # Create history entries for changed fields
        for field, old_value in old_values.items():
            new_value = str(getattr(updated_instance, field))
            if old_value != new_value:
                SectionDataHistory.objects.create(
                    dati_sezione=updated_instance.dati_sezione,
                    dati_scheda=updated_instance,
                    campo=field,
                    valore_precedente=old_value,
                    valore_nuovo=new_value,
                    modificato_da=self.request.user,
                    ip_address=self.get_client_ip(self.request),
                )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class SectionDataHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SectionDataHistory (read-only).

    GET /api/sections/history/ - List all history
    GET /api/sections/history/{id}/ - Get history detail
    """
    queryset = SectionDataHistory.objects.select_related(
        'dati_sezione', 'dati_sezione__sezione', 'dati_scheda', 'modificato_da'
    ).all()
    serializer_class = SectionDataHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['dati_sezione', 'dati_scheda', 'campo', 'modificato_da']
