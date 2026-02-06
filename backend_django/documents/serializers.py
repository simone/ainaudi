"""
Serializers for documents models.
"""
from rest_framework import serializers
from .models import TemplateType, Template, GeneratedDocument


class TemplateTypeSerializer(serializers.ModelSerializer):
    """Serializer for TemplateType model."""

    class Meta:
        model = TemplateType
        fields = [
            'id', 'code', 'name', 'description',
            'default_schema', 'default_merge_mode', 'use_case',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TemplateSerializer(serializers.ModelSerializer):
    template_type_details = TemplateTypeSerializer(source='template_type', read_only=True)
    template_file_url = serializers.SerializerMethodField()
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True, allow_null=True)

    class Meta:
        model = Template
        fields = [
            'id', 'consultazione', 'consultazione_nome', 'name',
            'template_type', 'template_type_details',
            'description', 'template_file', 'template_file_url', 'variables_schema',
            'is_active', 'version', 'created_at', 'updated_at',
            # Template editor fields
            'field_mappings', 'loop_config', 'merge_mode'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'template_file_url', 'consultazione_nome', 'template_type_details']

    def get_template_file_url(self, obj):
        """Return API endpoint URL for template file (works with Vite proxy)"""
        if obj.template_file:
            # Use /api/documents/media/ endpoint instead of /media/
            # This works because /api is properly proxied by Vite
            # Original path: /media/templates/file.pdf
            # API path: /api/documents/media/templates/file.pdf
            original_url = obj.template_file.url  # e.g., /media/templates/file.pdf
            if original_url.startswith('/media/'):
                # Strip /media/ and prepend /api/documents/media/
                return '/api/documents/media/' + original_url[7:]  # Remove '/media/'
            return original_url
        return None


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_email = serializers.EmailField(source='generated_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'template', 'template_name',
            'generated_by', 'generated_by_email',
            'input_data', 'pdf_file', 'pdf_url', 'generated_at',
            # State machine fields
            'status', 'status_display', 'review_token',
            'preview_expires_at', 'confirmed_at', 'confirmation_ip'
        ]
        read_only_fields = [
            'id', 'generated_by', 'pdf_file', 'pdf_url', 'generated_at',
            'status', 'review_token', 'confirmed_at', 'confirmation_ip'
        ]


class GeneratePDFSerializer(serializers.Serializer):
    """Serializer for PDF generation request."""
    template_id = serializers.IntegerField()
    data = serializers.JSONField()
    store = serializers.BooleanField(default=False)
