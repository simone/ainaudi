"""
Django Admin configuration for documents models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import TemplateType, Template, GeneratedDocument


@admin.register(TemplateType)
class TemplateTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'default_merge_mode', 'is_active', 'updated_at']
    list_filter = ['default_merge_mode', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('code', 'name', 'description', 'is_active')
        }),
        (_('Configurazione'), {
            'fields': ('default_schema', 'default_merge_mode', 'use_case')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'consultazione', 'version', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active', 'consultazione']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('name', 'template_type', 'description', 'consultazione', 'is_active', 'version')
        }),
        (_('File Template'), {
            'fields': ('template_file',)
        }),
        (_('Configurazione Campi'), {
            'fields': ('field_mappings', 'loop_config', 'merge_mode'),
            'description': _('Configurato tramite Template Editor')
        }),
        (_('Schema Variabili (Autocomplete)'), {
            'fields': ('variables_schema',),
            'description': _('Esempio JSON per autocomplete JSONPath nell\'editor. '
                           'Inserisci un esempio di dati che rappresenta la struttura disponibile.')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'template', 'generated_by', 'generated_at']
    list_filter = ['template', 'generated_at']
    search_fields = ['generated_by__email']
    raw_id_fields = ['template', 'generated_by']
    readonly_fields = ['generated_at']
