"""
Django Admin configuration for AI Assistant models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import KnowledgeSource, ChatSession, ChatMessage


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'source_type', 'is_active', 'updated_at']
    list_filter = ['source_type', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'content', 'created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_email', 'context', 'sezione', 'created_at', 'updated_at']
    list_filter = ['context', 'created_at']
    search_fields = ['user_email']
    raw_id_fields = ['sezione']
    inlines = [ChatMessageInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content']
    raw_id_fields = ['session']
    readonly_fields = ['created_at']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('Contenuto')
