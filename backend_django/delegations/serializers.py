"""
Serializers for delegations models.
"""
from rest_framework import serializers
from .models import DelegationRelationship, FreezeBatch, ProxyDelegationDocument


class DelegationRelationshipSerializer(serializers.ModelSerializer):
    """Serializer for DelegationRelationship model."""
    principal_email = serializers.EmailField(source='principal.email', read_only=True)
    principal_name = serializers.CharField(source='principal.display_name', read_only=True)
    delegate_email = serializers.EmailField(source='delegate.email', read_only=True)
    delegate_name = serializers.CharField(source='delegate.display_name', read_only=True)
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)
    scope_description = serializers.CharField(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = DelegationRelationship
        fields = [
            'id', 'consultazione',
            'principal', 'principal_email', 'principal_name',
            'delegate', 'delegate_email', 'delegate_name',
            'relationship_type', 'relationship_type_display',
            'scope_regione', 'scope_provincia', 'scope_comune', 'scope_municipio',
            'scope_description',
            'valid_from', 'valid_to', 'is_active',
            'created_at', 'created_by', 'created_by_email',
            'revoked_at', 'revoked_by', 'notes'
        ]
        read_only_fields = [
            'id', 'created_at', 'created_by', 'revoked_at', 'revoked_by'
        ]


class DelegationRelationshipCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DelegationRelationship."""

    class Meta:
        model = DelegationRelationship
        fields = [
            'consultazione', 'principal', 'delegate', 'relationship_type',
            'scope_regione', 'scope_provincia', 'scope_comune', 'scope_municipio',
            'valid_from', 'valid_to', 'notes'
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class DelegationTreeSerializer(serializers.Serializer):
    """Serializer for hierarchical delegation tree view."""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    scope = serializers.CharField()
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        # Recursive serialization for tree structure
        children = obj.get('children', [])
        return DelegationTreeSerializer(children, many=True).data


class ProxyDelegationDocumentSerializer(serializers.ModelSerializer):
    """Serializer for ProxyDelegationDocument model."""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    generated_by_email = serializers.EmailField(source='generated_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)

    class Meta:
        model = ProxyDelegationDocument
        fields = [
            'id', 'freeze_batch', 'delegation',
            'document_type', 'document_type_display',
            'status', 'status_display',
            'pdf_file', 'pdf_url', 'template_data',
            'generated_at', 'generated_by', 'generated_by_email',
            'approved_at', 'approved_by', 'approved_by_email',
            'sent_at'
        ]
        read_only_fields = [
            'id', 'pdf_file', 'pdf_url', 'generated_at', 'generated_by',
            'approved_at', 'approved_by', 'sent_at'
        ]


class FreezeBatchSerializer(serializers.ModelSerializer):
    """Serializer for FreezeBatch model."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    scope_description = serializers.CharField(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    documents = ProxyDelegationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = FreezeBatch
        fields = [
            'id', 'consultazione', 'name', 'description',
            'status', 'status_display',
            'scope_regione', 'scope_provincia', 'scope_comune', 'scope_description',
            'snapshot_data', 'frozen_at',
            'created_by', 'created_by_email', 'created_at',
            'approved_by', 'approved_by_email', 'approved_at',
            'documents'
        ]
        read_only_fields = [
            'id', 'snapshot_data', 'frozen_at', 'created_at', 'created_by',
            'approved_at', 'approved_by'
        ]


class FreezeBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating FreezeBatch."""

    class Meta:
        model = FreezeBatch
        fields = [
            'consultazione', 'name', 'description',
            'scope_regione', 'scope_provincia', 'scope_comune'
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class FreezeBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    scope_description = serializers.CharField(read_only=True)

    class Meta:
        model = FreezeBatch
        fields = [
            'id', 'name', 'status', 'status_display',
            'scope_description', 'frozen_at', 'created_at'
        ]
