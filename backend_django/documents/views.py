"""
Views for documents API endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.core.signing import TimestampSigner, BadSignature
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta
import io
import os

from .models import TemplateType, Template, GeneratedDocument
from .serializers import TemplateTypeSerializer, TemplateSerializer, GeneratedDocumentSerializer, GeneratePDFSerializer
from .events import publish_preview_pdf_and_email, publish_confirm_freeze

# Signer for review tokens (similar to magic link pattern)
signer = TimestampSigner()


class TemplateTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for TemplateType (read-only for users, editable via admin).

    GET /api/documents/template-types/        - List all template types
    GET /api/documents/template-types/{id}/   - Get template type detail
    """
    queryset = TemplateType.objects.filter(is_active=True)
    serializer_class = TemplateTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Disable pagination - return full list


class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Template (full CRUD for admins).

    GET /api/documents/templates/        - List templates
    GET /api/documents/templates/?consultazione=<id> - Filter by consultazione
    POST /api/documents/templates/       - Create template (admin only)
    GET /api/documents/templates/{id}/   - Get template detail
    PUT /api/documents/templates/{id}/   - Update template (admin only)
    DELETE /api/documents/templates/{id}/ - Delete template (admin only)
    """
    queryset = Template.objects.filter(is_active=True).select_related('consultazione')
    serializer_class = TemplateSerializer
    filterset_fields = ['template_type', 'is_active', 'consultazione']
    search_fields = ['name', 'description']
    pagination_class = None  # Disable pagination - return full list

    def get_permissions(self):
        """Admin required for create/update/delete"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def perform_destroy(self, instance):
        """Soft delete - set is_active=False"""
        instance.is_active = False
        instance.save()


class GeneratedDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for GeneratedDocument (read-only).

    GET /api/documents/generated/
    GET /api/documents/generated/{id}/
    """
    queryset = GeneratedDocument.objects.select_related('template', 'generated_by').all()
    serializer_class = GeneratedDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['template', 'generated_by']

    def get_queryset(self):
        # Users can only see their own generated documents unless staff
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(generated_by=self.request.user)


class GeneratePDFView(APIView):
    """
    LEGACY: Direct PDF generation endpoint (to be deprecated).

    POST /api/documents/generate/
    {
        "template_id": 1,
        "data": {"field1": "value1", ...},
        "store": false
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GeneratePDFSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template_id = serializer.validated_data['template_id']
        data = serializer.validated_data['data']
        store = serializer.validated_data.get('store', False)

        try:
            template = Template.objects.get(id=template_id, is_active=True)
        except Template.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Implement PDF generation using PyMuPDF
        # For now, return a placeholder response
        # This will be implemented in Fase 4

        return Response({
            'message': 'PDF generation not yet implemented',
            'template': template.name,
            'data': data,
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


class RequestPDFPreviewView(APIView):
    """
    Request PDF preview with email confirmation workflow.

    POST /api/documents/preview/
    {
        "template_id": 1,
        "data": {...},
        "email_to": "user@example.com"  # Optional, defaults to user's email
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.conf import settings

        template_id = request.data.get('template_id')
        pdf_data = request.data.get('data', {})
        email_to = request.data.get('email_to') or request.user.email

        if not template_id:
            return Response({'error': 'template_id required'}, status=400)

        template = get_object_or_404(Template, id=template_id, is_active=True)

        # Create document in PREVIEW state
        expires_at = timezone.now() + timedelta(seconds=settings.PDF_PREVIEW_EXPIRY_SECONDS)
        document = GeneratedDocument.objects.create(
            template=template,
            generated_by=request.user,
            input_data=pdf_data,
            status=GeneratedDocument.Status.PREVIEW,
            preview_expires_at=expires_at,
        )

        # Generate signed token (includes doc ID for security)
        review_token = signer.sign(f"pdf-{document.id}")
        document.review_token = review_token
        document.save(update_fields=['review_token'])

        # Publish event to Redis
        try:
            event_id = publish_preview_pdf_and_email(
                review_token=review_token,
                email_to=email_to,
                subject=f"Preview: {template.name}",
                pdf_data=pdf_data,
                template_name=template.name,
            )
            document.event_id = event_id
            document.save(update_fields=['event_id'])
        except Exception as e:
            # If Redis publish fails, delete document and return error
            document.delete()
            return Response({
                'error': 'Failed to queue preview request',
                'detail': str(e)
            }, status=500)

        return Response({
            'message': 'Preview request queued. Check your email.',
            'document_id': document.id,
            'status': document.status,
            'expires_at': expires_at.isoformat(),
        }, status=202)


class ConfirmPDFView(APIView):
    """
    Confirm PDF and freeze document (PREVIEW → CONFIRMED).

    GET/POST /api/documents/confirm/?token=xxx

    Supports both GET (for email links) and POST (for form submissions).
    """
    permission_classes = [permissions.AllowAny]  # Token-based auth

    def _confirm(self, token, request):
        """Shared confirmation logic."""
        if not token:
            return Response({'error': 'Token required'}, status=400)

        # Verify signature
        try:
            unsigned = signer.unsign(token)
            if not unsigned.startswith('pdf-'):
                raise ValueError("Invalid token format")
            doc_id = int(unsigned.replace('pdf-', ''))
        except (BadSignature, ValueError) as e:
            return Response({'error': 'Invalid or expired token'}, status=400)

        # Get document
        document = get_object_or_404(GeneratedDocument, id=doc_id, review_token=token)

        # Already confirmed?
        if document.status == GeneratedDocument.Status.CONFIRMED:
            return Response({
                'message': 'Already confirmed',
                'document_id': document.id,
                'pdf_url': document.pdf_url or (document.pdf_file.url if document.pdf_file else None),
                'confirmed_at': document.confirmed_at.isoformat() if document.confirmed_at else None,
            })

        # Check if preview expired
        if document.preview_expires_at and timezone.now() > document.preview_expires_at:
            document.status = GeneratedDocument.Status.EXPIRED
            document.save(update_fields=['status'])
            return Response({'error': 'Preview expired'}, status=410)

        # Check if cancelled
        if document.status == GeneratedDocument.Status.CANCELLED:
            return Response({'error': 'Document was cancelled'}, status=410)

        # Freeze document
        document.status = GeneratedDocument.Status.CONFIRMED
        document.confirmed_at = timezone.now()
        document.confirmation_ip = request.META.get('REMOTE_ADDR')
        document.save(update_fields=['status', 'confirmed_at', 'confirmation_ip'])

        # Publish audit event (non-blocking)
        try:
            publish_confirm_freeze(token)
        except:
            pass  # Don't fail confirmation if audit event fails

        return Response({
            'message': 'Document confirmed',
            'document_id': document.id,
            'status': document.status,
            'confirmed_at': document.confirmed_at.isoformat(),
            'pdf_url': document.pdf_url or (document.pdf_file.url if document.pdf_file else None),
        })

    def get(self, request):
        """Handle GET requests (email links)."""
        return self._confirm(request.query_params.get('token'), request)

    def post(self, request):
        """Handle POST requests (form submissions)."""
        return self._confirm(request.data.get('token'), request)


class TemplateEditorView(APIView):
    """
    Template editor for admin users.

    GET /api/documents/templates/{id}/editor/
    Returns template + field mappings for editor UI.

    PUT /api/documents/templates/{id}/editor/
    Updates field_mappings and loop_config.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        template = get_object_or_404(Template, pk=pk)

        # Convert /media/ URL to /api/documents/media/ (Vite proxy workaround)
        template_file_url = None
        if template.template_file:
            url = template.template_file.url  # e.g., /media/templates/file.pdf
            if url.startswith('/media/'):
                # Convert to API endpoint: /api/documents/media/templates/file.pdf
                template_file_url = '/api/documents/media/' + url[7:]
            else:
                template_file_url = url

        return Response({
            'id': template.id,
            'name': template.name,
            'template_file_url': template_file_url,
            'field_mappings': template.field_mappings,
            'loop_config': template.loop_config,
            'merge_mode': template.merge_mode,
            'variables_schema': template.template_type.default_schema if template.template_type else {},
        })

    def put(self, request, pk):
        template = get_object_or_404(Template, pk=pk)

        # Validate field_mappings structure
        field_mappings = request.data.get('field_mappings', [])
        for mapping in field_mappings:
            required_keys = ['area', 'jsonpath', 'type']
            if not all(k in mapping for k in required_keys):
                return Response({
                    'error': 'Invalid field_mapping structure',
                    'detail': 'Each mapping must have: area, jsonpath, type'
                }, status=400)

        template.field_mappings = field_mappings
        template.loop_config = request.data.get('loop_config', template.loop_config)
        template.merge_mode = request.data.get('merge_mode', template.merge_mode)
        template.save()

        return Response({
            'message': 'Template updated',
            'id': template.id,
            'field_mappings': template.field_mappings,
            'loop_config': template.loop_config,
        })


class TemplatePreviewView(APIView):
    """
    Generate preview PDF with test data (for template testing).

    POST /api/documents/templates/{id}/preview/
    {
        "test_data": {...}
    }
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        template = get_object_or_404(Template, pk=pk)
        test_data = request.data.get('test_data', {})

        # Use same event-driven workflow for admin testing
        expires_at = timezone.now() + timedelta(hours=1)  # Short expiry for tests
        document = GeneratedDocument.objects.create(
            template=template,
            generated_by=request.user,
            input_data=test_data,
            status=GeneratedDocument.Status.PREVIEW,
            preview_expires_at=expires_at,
        )

        review_token = signer.sign(f"pdf-{document.id}")
        document.review_token = review_token
        document.save(update_fields=['review_token'])

        try:
            event_id = publish_preview_pdf_and_email(
                review_token=review_token,
                email_to=request.user.email,
                subject=f"[TEST] Template Preview: {template.name}",
                pdf_data=test_data,
                template_name=template.name,
            )
            document.event_id = event_id
            document.save(update_fields=['event_id'])
        except Exception as e:
            document.delete()
            return Response({
                'error': 'Failed to queue preview',
                'detail': str(e)
            }, status=500)

        return Response({
            'message': 'Test preview queued',
            'document_id': document.id,
            'expires_at': expires_at.isoformat(),
        }, status=202)


class ServeMediaView(APIView):
    """
    Serve media files through API endpoint.

    GET /api/media/templates/<filename>

    This is needed because Vite proxy doesn't work for /media/ paths
    (SPA fallback returns index.html). Serving through /api/media/
    works because /api is properly proxied.
    """
    permission_classes = [permissions.AllowAny]  # Files are public (or use templates for permission check)

    def get(self, request, filepath):
        """Serve a media file."""
        from django.conf import settings

        # Security: prevent directory traversal
        filepath = filepath.lstrip('/')
        if '..' in filepath or filepath.startswith('/'):
            raise Http404("Invalid file path")

        # Build full path
        full_path = os.path.join(settings.MEDIA_ROOT, filepath)

        # Check if file exists
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise Http404("File not found")

        # Serve file
        return FileResponse(open(full_path, 'rb'))
