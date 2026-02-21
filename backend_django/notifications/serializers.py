"""
Serializers for notifications app.
"""
from django.utils import timezone
from rest_framework import serializers

from .models import Event, Notification, DeviceToken
from data.models import SectionAssignment


class EventSerializer(serializers.ModelSerializer):
    """Full event serializer with computed temporal status."""
    temporal_status = serializers.SerializerMethodField()
    consultazione_nome = serializers.CharField(
        source='consultazione.nome', read_only=True, default=None
    )

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'start_at', 'end_at',
            'external_url', 'status', 'temporal_status',
            'consultazione', 'consultazione_nome',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_temporal_status(self, obj):
        return obj.temporal_status


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight event serializer for list views."""
    temporal_status = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_at', 'end_at',
            'external_url', 'status', 'temporal_status',
        ]

    def get_temporal_status(self, obj):
        return obj.temporal_status


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Wraps SectionAssignment with derived operational fields.

    Derives start_at/end_at from consultazione dates,
    location info from sezione.
    """
    # Derived from consultazione
    start_at = serializers.DateField(source='consultazione.data_inizio', read_only=True)
    end_at = serializers.DateField(source='consultazione.data_fine', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)

    # Derived from sezione
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    location_name = serializers.CharField(source='sezione.denominazione', read_only=True)
    address = serializers.CharField(source='sezione.indirizzo', read_only=True)
    comune_nome = serializers.CharField(source='sezione.comune.nome', read_only=True)
    municipio_nome = serializers.SerializerMethodField()
    lat = serializers.FloatField(source='sezione.latitudine', read_only=True, default=None)
    lng = serializers.FloatField(source='sezione.longitudine', read_only=True, default=None)

    # From assignment itself
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    rdl_nome = serializers.SerializerMethodField()

    # Temporal status derived from consultazione dates
    temporal_status = serializers.SerializerMethodField()

    class Meta:
        model = SectionAssignment
        fields = [
            'id', 'role', 'role_display', 'notes',
            'start_at', 'end_at', 'consultazione_nome',
            'sezione_numero', 'location_name', 'address',
            'comune_nome', 'municipio_nome', 'lat', 'lng',
            'rdl_nome', 'temporal_status', 'assigned_at',
        ]

    def get_municipio_nome(self, obj):
        if obj.sezione.municipio:
            return obj.sezione.municipio.nome
        return None

    def get_rdl_nome(self, obj):
        if obj.rdl_registration:
            return f'{obj.rdl_registration.cognome} {obj.rdl_registration.nome}'
        return None

    def get_temporal_status(self, obj):
        today = timezone.now().date()
        start = obj.consultazione.data_inizio
        end = obj.consultazione.data_fine
        if today < start:
            return 'FUTURO'
        elif today <= end:
            return 'IN_CORSO'
        return 'CONCLUSO'


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer for user notifications list."""
    source_type = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'deep_link',
            'scheduled_at', 'channel', 'status', 'sent_at',
            'source_type', 'created_at',
        ]

    def get_source_type(self, obj):
        return obj.source_type


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating device tokens."""

    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'platform', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        token = validated_data['token']
        platform = validated_data.get('platform', DeviceToken.Platform.WEB)

        # Upsert: update existing or create new
        device_token, created = DeviceToken.objects.update_or_create(
            user=user,
            token=token,
            defaults={
                'platform': platform,
                'is_active': True,
                'last_seen_at': timezone.now(),
            }
        )
        return device_token


class DashboardItemSerializer(serializers.Serializer):
    """
    Unified serializer for dashboard items (mixed events + assignments).
    """
    type = serializers.CharField()  # 'event' or 'assignment'
    id = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    temporal_status = serializers.CharField()
    deep_link = serializers.CharField()
    is_urgent = serializers.BooleanField()
    external_url = serializers.CharField(allow_blank=True, default='')
