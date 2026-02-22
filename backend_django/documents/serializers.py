"""
Serializers for documents models.
"""
from rest_framework import serializers
from .models import Template, GeneratedDocument


class TemplateSerializer(serializers.ModelSerializer):
    template_file_url = serializers.SerializerMethodField()
    variables_schema = serializers.SerializerMethodField()
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True, allow_null=True)
    is_generic = serializers.SerializerMethodField()
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = Template
        fields = [
            'id', 'consultazione', 'consultazione_nome', 'name',
            'template_type', 'template_type_display',
            'owner_email', 'is_generic',
            'description', 'template_file', 'template_file_url', 'variables_schema',
            'is_active', 'version', 'created_at', 'updated_at',
            # Template editor fields
            'field_mappings', 'loop_config', 'merge_mode'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'template_file_url', 'consultazione_nome', 'template_type_display', 'variables_schema', 'is_generic']

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

    def get_variables_schema(self, obj):
        """Return variables schema from registry."""
        return obj.get_variables_schema()

    def get_is_generic(self, obj):
        """Return True if template is generic (not owned by anyone)"""
        return obj.is_generic()


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
