"""
Views for delegations API endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import DelegationRelationship, FreezeBatch, ProxyDelegationDocument
from .serializers import (
    DelegationRelationshipSerializer, DelegationRelationshipCreateSerializer,
    FreezeBatchSerializer, FreezeBatchCreateSerializer, FreezeBatchListSerializer,
    ProxyDelegationDocumentSerializer,
)


class DelegationRelationshipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DelegationRelationship.

    GET /api/delegations/ - List all delegations
    GET /api/delegations/my-delegations/ - List delegations I've given
    GET /api/delegations/my-received/ - List delegations I've received
    POST /api/delegations/ - Create delegation
    POST /api/delegations/{id}/revoke/ - Revoke delegation
    """
    queryset = DelegationRelationship.objects.select_related(
        'consultazione', 'principal', 'delegate', 'created_by', 'revoked_by',
        'scope_regione', 'scope_provincia', 'scope_comune', 'scope_municipio'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        'consultazione', 'principal', 'delegate',
        'relationship_type', 'is_active',
        'scope_regione', 'scope_provincia', 'scope_comune'
    ]
    search_fields = ['principal__email', 'delegate__email', 'notes']

    def get_serializer_class(self):
        if self.action == 'create':
            return DelegationRelationshipCreateSerializer
        return DelegationRelationshipSerializer

    @action(detail=False, methods=['get'])
    def my_delegations(self, request):
        """Get delegations given by current user."""
        delegations = self.queryset.filter(
            principal=request.user,
            is_active=True
        )
        serializer = DelegationRelationshipSerializer(delegations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_received(self, request):
        """Get delegations received by current user."""
        delegations = self.queryset.filter(
            delegate=request.user,
            is_active=True
        )
        serializer = DelegationRelationshipSerializer(delegations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get hierarchical tree of all delegations."""
        consultazione_id = request.query_params.get('consultazione')
        if not consultazione_id:
            return Response(
                {'error': 'consultazione parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build delegation tree
        delegations = self.queryset.filter(
            consultazione_id=consultazione_id,
            is_active=True
        )

        # Find root nodes (those who are principals but not delegates)
        delegate_ids = set(delegations.values_list('delegate_id', flat=True))
        principal_ids = set(delegations.values_list('principal_id', flat=True))
        root_ids = principal_ids - delegate_ids

        def build_subtree(user_id):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)

            children_delegations = delegations.filter(principal_id=user_id)
            children = [
                build_subtree(d.delegate_id)
                for d in children_delegations
            ]

            return {
                'id': user.id,
                'email': user.email,
                'display_name': user.display_name or user.email,
                'role': children_delegations.first().get_relationship_type_display() if children_delegations.exists() else 'Root',
                'scope': children_delegations.first().scope_description if children_delegations.exists() else 'Nazionale',
                'children': children,
            }

        tree = [build_subtree(root_id) for root_id in root_ids]
        return Response(tree)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a delegation."""
        delegation = self.get_object()

        # Check if user can revoke (must be principal or admin)
        if delegation.principal != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorizzato a revocare questa delega'},
                status=status.HTTP_403_FORBIDDEN
            )

        delegation.is_active = False
        delegation.revoked_at = timezone.now()
        delegation.revoked_by = request.user
        delegation.save()

        serializer = DelegationRelationshipSerializer(delegation)
        return Response(serializer.data)


class FreezeBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FreezeBatch.

    GET /api/delegations/batches/ - List all batches
    POST /api/delegations/batches/ - Create batch
    POST /api/delegations/batches/{id}/freeze/ - Freeze batch
    POST /api/delegations/batches/{id}/approve/ - Approve batch
    """
    queryset = FreezeBatch.objects.select_related(
        'consultazione', 'created_by', 'approved_by',
        'scope_regione', 'scope_provincia', 'scope_comune'
    ).prefetch_related('documents').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        'consultazione', 'status',
        'scope_regione', 'scope_provincia', 'scope_comune'
    ]
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return FreezeBatchCreateSerializer
        if self.action == 'list':
            return FreezeBatchListSerializer
        return FreezeBatchSerializer

    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        """Freeze the batch, creating a snapshot of current state."""
        batch = self.get_object()

        if batch.status != FreezeBatch.Status.DRAFT:
            return Response(
                {'error': 'Batch non in stato bozza'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build snapshot data
        from sections.models import SectionAssignment

        # Get delegations in scope
        delegations_qs = DelegationRelationship.objects.filter(
            consultazione=batch.consultazione,
            is_active=True
        )
        if batch.scope_comune:
            delegations_qs = delegations_qs.filter(scope_comune=batch.scope_comune)
        elif batch.scope_provincia:
            delegations_qs = delegations_qs.filter(scope_provincia=batch.scope_provincia)
        elif batch.scope_regione:
            delegations_qs = delegations_qs.filter(scope_regione=batch.scope_regione)

        # Get assignments in scope
        assignments_qs = SectionAssignment.objects.filter(
            consultazione=batch.consultazione,
            is_active=True
        )
        if batch.scope_comune:
            assignments_qs = assignments_qs.filter(sezione__comune=batch.scope_comune)
        elif batch.scope_provincia:
            assignments_qs = assignments_qs.filter(sezione__comune__provincia=batch.scope_provincia)
        elif batch.scope_regione:
            assignments_qs = assignments_qs.filter(sezione__comune__provincia__regione=batch.scope_regione)

        # Create snapshot
        snapshot = {
            'frozen_at': timezone.now().isoformat(),
            'delegations': list(delegations_qs.values(
                'id', 'principal__email', 'delegate__email',
                'relationship_type', 'scope_comune__nome', 'scope_provincia__nome'
            )),
            'assignments': list(assignments_qs.values(
                'id', 'user__email', 'sezione__numero', 'sezione__comune__nome', 'role'
            )),
            'counts': {
                'delegations': delegations_qs.count(),
                'assignments': assignments_qs.count(),
            }
        }

        batch.snapshot_data = snapshot
        batch.frozen_at = timezone.now()
        batch.status = FreezeBatch.Status.FROZEN
        batch.save()

        serializer = FreezeBatchSerializer(batch)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a frozen batch."""
        batch = self.get_object()

        if batch.status != FreezeBatch.Status.FROZEN:
            return Response(
                {'error': 'Batch non in stato congelato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch.status = FreezeBatch.Status.APPROVED
        batch.approved_by = request.user
        batch.approved_at = timezone.now()
        batch.save()

        serializer = FreezeBatchSerializer(batch)
        return Response(serializer.data)


class ProxyDelegationDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProxyDelegationDocument.

    GET /api/delegations/documents/ - List all documents
    GET /api/delegations/documents/{id}/ - Get document detail
    POST /api/delegations/documents/{id}/approve/ - Approve document
    POST /api/delegations/documents/{id}/send/ - Mark as sent
    """
    queryset = ProxyDelegationDocument.objects.select_related(
        'freeze_batch', 'delegation', 'generated_by', 'approved_by'
    ).all()
    serializer_class = ProxyDelegationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['freeze_batch', 'delegation', 'document_type', 'status']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a document."""
        document = self.get_object()

        if document.status != ProxyDelegationDocument.Status.READY:
            return Response(
                {'error': 'Documento non in stato pronto'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.status = ProxyDelegationDocument.Status.APPROVED
        document.approved_by = request.user
        document.approved_at = timezone.now()
        document.save()

        serializer = ProxyDelegationDocumentSerializer(document)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark document as sent."""
        document = self.get_object()

        if document.status != ProxyDelegationDocument.Status.APPROVED:
            return Response(
                {'error': 'Documento non approvato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.status = ProxyDelegationDocument.Status.SENT
        document.sent_at = timezone.now()
        document.save()

        serializer = ProxyDelegationDocumentSerializer(document)
        return Response(serializer.data)
