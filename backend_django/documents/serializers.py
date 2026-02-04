"""
Serializers for documents models.
"""
from rest_framework import serializers
from .models import Template, GeneratedDocument


class TemplateSerializer(serializers.ModelSerializer):
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    template_file_url = serializers.SerializerMethodField()
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)

    class Meta:
        model = Template
        fields = [
            'id', 'consultazione', 'consultazione_nome', 'name', 'template_type', 'template_type_display',
            'description', 'template_file', 'template_file_url', 'variables_schema',
            'is_active', 'version', 'created_at', 'updated_at',
            # Template editor fields
            'field_mappings', 'loop_config', 'merge_mode'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'template_file_url', 'consultazione_nome']

    def get_template_file_url(self, obj):
        """Return full URL for template file"""
        if obj.template_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.template_file.url)
            return obj.template_file.url
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
