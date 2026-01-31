"""
Serializers for incidents models.
"""
from rest_framework import serializers
from .models import IncidentReport, IncidentComment, IncidentAttachment


class IncidentAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for IncidentAttachment model."""
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = IncidentAttachment
        fields = [
            'id', 'file', 'file_type', 'file_type_display',
            'filename', 'file_size', 'description',
            'uploaded_by', 'uploaded_by_email', 'uploaded_at'
        ]
        read_only_fields = ['id', 'filename', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at']


class IncidentCommentSerializer(serializers.ModelSerializer):
    """Serializer for IncidentComment model."""
    author_email = serializers.EmailField(source='author.email', read_only=True)
    author_name = serializers.CharField(source='author.display_name', read_only=True)

    class Meta:
        model = IncidentComment
        fields = [
            'id', 'incident', 'author', 'author_email', 'author_name',
            'content', 'is_internal', 'created_at'
        ]
        read_only_fields = ['id', 'author', 'created_at']


class IncidentCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating IncidentComment."""

    class Meta:
        model = IncidentComment
        fields = ['incident', 'content', 'is_internal']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class IncidentReportSerializer(serializers.ModelSerializer):
    """Serializer for IncidentReport model."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    location_description = serializers.CharField(read_only=True)
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)
    reporter_name = serializers.CharField(source='reporter.display_name', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    resolved_by_email = serializers.EmailField(source='resolved_by.email', read_only=True)
    comments = IncidentCommentSerializer(many=True, read_only=True)
    attachments = IncidentAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = IncidentReport
        fields = [
            'id', 'consultazione', 'sezione', 'sezione_numero', 'sezione_comune',
            'reporter', 'reporter_email', 'reporter_name',
            'category', 'category_display',
            'severity', 'severity_display',
            'status', 'status_display',
            'title', 'description', 'location_description',
            'occurred_at',
            'resolution', 'resolved_at', 'resolved_by', 'resolved_by_email',
            'assigned_to', 'assigned_to_email',
            'created_at', 'updated_at',
            'comments', 'attachments'
        ]
        read_only_fields = [
            'id', 'reporter', 'resolved_at', 'resolved_by',
            'created_at', 'updated_at'
        ]


class IncidentReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating IncidentReport."""

    class Meta:
        model = IncidentReport
        fields = [
            'consultazione', 'sezione', 'category', 'severity',
            'title', 'description', 'occurred_at'
        ]

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)


class IncidentReportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating IncidentReport."""

    class Meta:
        model = IncidentReport
        fields = [
            'category', 'severity', 'status',
            'title', 'description', 'occurred_at',
            'resolution', 'assigned_to'
        ]


class IncidentReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    location_description = serializers.CharField(read_only=True)
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)

    class Meta:
        model = IncidentReport
        fields = [
            'id', 'title', 'category', 'category_display',
            'severity', 'severity_display', 'status', 'status_display',
            'location_description', 'reporter_email', 'created_at'
        ]
