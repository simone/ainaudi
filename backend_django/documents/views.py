"""
Views for documents API endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse
import io

from .models import Template, GeneratedDocument
from .serializers import TemplateSerializer, GeneratedDocumentSerializer, GeneratePDFSerializer


class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Template (read-only).

    GET /api/documents/templates/
    GET /api/documents/templates/{id}/
    """
    queryset = Template.objects.filter(is_active=True)
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'description']


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
    Generate a PDF from a template.

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
