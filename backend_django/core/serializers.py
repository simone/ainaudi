"""
Serializers for core models.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import RoleAssignment, AuditLog

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name', 'first_name', 'last_name',
            'phone_number', 'avatar_url', 'is_active', 'is_superuser',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'email', 'is_active', 'is_superuser', 'created_at', 'last_login']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates."""

    class Meta:
        model = User
        fields = ['display_name', 'first_name', 'last_name', 'phone_number']


class RoleAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for RoleAssignment model."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            'id', 'role', 'role_display', 'scope_type', 'scope_type_display',
            'scope_value', 'assigned_by_email', 'assigned_at',
            'valid_from', 'valid_to', 'is_active', 'is_valid', 'notes'
        ]
        read_only_fields = ['id', 'assigned_at', 'is_valid']


class RoleAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RoleAssignment."""

    class Meta:
        model = RoleAssignment
        fields = [
            'user', 'role', 'scope_type', 'scope_value',
            'scope_regione', 'scope_provincia', 'scope_comune',
            'valid_from', 'valid_to', 'notes'
        ]

    def create(self, validated_data):
        # Set assigned_by from request context
        validated_data['assigned_by_email'] = self.context['request'].user.email
        return super().create(validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user_email', 'action', 'action_display',
            'target_model', 'target_id', 'details',
            'ip_address', 'timestamp'
        ]


class MagicLinkRequestSerializer(serializers.Serializer):
    """Serializer for Magic Link request."""
    email = serializers.EmailField(
        help_text='Email to send magic link to'
    )


class MagicLinkVerifySerializer(serializers.Serializer):
    """Serializer for Magic Link verification."""
    token = serializers.CharField(
        help_text='Magic link token from email'
    )
