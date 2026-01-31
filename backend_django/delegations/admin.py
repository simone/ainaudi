"""
Django Admin configuration for delegations models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import DelegationRelationship, FreezeBatch, ProxyDelegationDocument


class ProxyDelegationDocumentInline(admin.TabularInline):
    model = ProxyDelegationDocument
    extra = 0
    fields = ['document_type', 'status', 'generated_at', 'pdf_url']
    readonly_fields = ['generated_at']


@admin.register(DelegationRelationship)
class DelegationRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        'principal', 'delegate', 'relationship_type',
        'scope_description', 'is_active', 'valid_from', 'valid_to'
    ]
    list_filter = [
        'relationship_type', 'is_active', 'consultazione',
        'scope_regione', 'scope_provincia', 'scope_comune'
    ]
    search_fields = [
        'principal__email', 'delegate__email',
        'principal__display_name', 'delegate__display_name'
    ]
    raw_id_fields = [
        'consultazione', 'principal', 'delegate', 'created_by', 'revoked_by',
        'scope_regione', 'scope_provincia', 'scope_comune', 'scope_municipio'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('consultazione', 'principal', 'delegate', 'relationship_type', 'is_active')
        }),
        (_('Ambito territoriale'), {
            'fields': ('scope_regione', 'scope_provincia', 'scope_comune', 'scope_municipio')
        }),
        (_('Validità'), {
            'fields': ('valid_from', 'valid_to')
        }),
        (_('Revoca'), {
            'fields': ('revoked_at', 'revoked_by'),
            'classes': ('collapse',)
        }),
        (_('Note e Audit'), {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

    def scope_description(self, obj):
        return obj.scope_description
    scope_description.short_description = _('Ambito')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FreezeBatch)
class FreezeBatchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'consultazione', 'status', 'scope_description',
        'frozen_at', 'created_by'
    ]
    list_filter = ['status', 'consultazione', 'scope_regione', 'scope_provincia']
    search_fields = ['name', 'description']
    raw_id_fields = [
        'consultazione', 'created_by', 'approved_by',
        'scope_regione', 'scope_provincia', 'scope_comune'
    ]
    inlines = [ProxyDelegationDocumentInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('consultazione', 'name', 'description', 'status')
        }),
        (_('Ambito'), {
            'fields': ('scope_regione', 'scope_provincia', 'scope_comune')
        }),
        (_('Snapshot'), {
            'fields': ('snapshot_data', 'frozen_at'),
            'classes': ('collapse',)
        }),
        (_('Approvazione'), {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

    def scope_description(self, obj):
        return obj.scope_description
    scope_description.short_description = _('Ambito')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProxyDelegationDocument)
class ProxyDelegationDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'document_type', 'status', 'freeze_batch',
        'generated_at', 'approved_at', 'sent_at'
    ]
    list_filter = ['document_type', 'status', 'freeze_batch__consultazione']
    search_fields = ['freeze_batch__name', 'delegation__principal__email']
    raw_id_fields = [
        'freeze_batch', 'delegation', 'generated_by', 'approved_by'
    ]
    date_hierarchy = 'generated_at'

    fieldsets = (
        (None, {
            'fields': ('freeze_batch', 'delegation', 'document_type', 'status')
        }),
        (_('File PDF'), {
            'fields': ('pdf_file', 'pdf_url')
        }),
        (_('Dati template'), {
            'fields': ('template_data',),
            'classes': ('collapse',)
        }),
        (_('Generazione'), {
            'fields': ('generated_by', 'generated_at'),
            'classes': ('collapse',)
        }),
        (_('Approvazione'), {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        (_('Invio'), {
            'fields': ('sent_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['generated_at']
