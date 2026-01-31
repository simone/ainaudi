"""
Django Admin configuration for documents models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Template, GeneratedDocument


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'version', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'template', 'generated_by', 'generated_at']
    list_filter = ['template', 'generated_at']
    search_fields = ['generated_by__email']
    raw_id_fields = ['template', 'generated_by']
    readonly_fields = ['generated_at']
