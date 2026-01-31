"""
Serializers for documents models.
"""
from rest_framework import serializers
from .models import Template, GeneratedDocument


class TemplateSerializer(serializers.ModelSerializer):
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = Template
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'description', 'template_file', 'variables_schema',
            'is_active', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_email = serializers.EmailField(source='generated_by.email', read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'template', 'template_name',
            'generated_by', 'generated_by_email',
            'input_data', 'pdf_file', 'pdf_url', 'generated_at'
        ]
        read_only_fields = ['id', 'generated_by', 'pdf_file', 'pdf_url', 'generated_at']


class GeneratePDFSerializer(serializers.Serializer):
    """Serializer for PDF generation request."""
    template_id = serializers.IntegerField()
    data = serializers.JSONField()
    store = serializers.BooleanField(default=False)
