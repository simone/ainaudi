"""
Django Admin configuration for notifications models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Event, Notification, DeviceToken


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_at', 'end_at', 'status', 'consultazione', 'has_url', 'created_at']
    list_filter = ['status', 'consultazione']
    search_fields = ['title', 'description']
    raw_id_fields = ['consultazione']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_at'

    fieldsets = (
        (None, {
            'fields': ('id', 'consultazione', 'title', 'description')
        }),
        (_('Date e link'), {
            'fields': ('start_at', 'end_at', 'external_url')
        }),
        (_('Stato'), {
            'fields': ('status',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_url(self, obj):
        return bool(obj.external_url)
    has_url.boolean = True
    has_url.short_description = _('Link')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user_email', 'source_type_display', 'channel',
        'status', 'scheduled_at', 'sent_at'
    ]
    list_filter = ['status', 'channel']
    search_fields = ['title', 'body', 'user__email']
    raw_id_fields = ['user', 'event', 'section_assignment']
    readonly_fields = ['id', 'created_at', 'updated_at', 'cloud_task_name']
    date_hierarchy = 'scheduled_at'

    fieldsets = (
        (None, {
            'fields': ('id', 'user')
        }),
        (_('Sorgente'), {
            'fields': ('event', 'section_assignment')
        }),
        (_('Contenuto'), {
            'fields': ('title', 'body', 'deep_link')
        }),
        (_('Programmazione'), {
            'fields': ('scheduled_at', 'channel', 'status', 'sent_at')
        }),
        (_('Cloud Tasks'), {
            'fields': ('cloud_task_name',),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = _('Email')
    user_email.admin_order_field = 'user__email'

    def source_type_display(self, obj):
        return _('Evento') if obj.event_id else _('Assegnazione')
    source_type_display.short_description = _('Tipo')


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'platform', 'is_active', 'last_seen_at', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__email', 'token']
    raw_id_fields = ['user']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = _('Email')
    user_email.admin_order_field = 'user__email'
