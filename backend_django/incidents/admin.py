"""
Django Admin configuration for incidents models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from territory.admin_filters import make_territory_filters
from .models import IncidentReport, IncidentComment, IncidentAttachment


class IncidentCommentInline(admin.TabularInline):
    model = IncidentComment
    extra = 0
    readonly_fields = ['author', 'created_at']


class IncidentAttachmentInline(admin.TabularInline):
    model = IncidentAttachment
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at', 'file_size', 'file_type']


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'category', 'severity', 'status',
        'location_description', 'reporter', 'created_at'
    ]
    list_filter = ['status', 'category', 'severity', 'consultazione', *make_territory_filters('sezione__comune')]
    search_fields = ['title', 'description', 'reporter__email', 'sezione__comune__nome']
    raw_id_fields = ['consultazione', 'sezione', 'reporter', 'resolved_by', 'assigned_to']
    inlines = [IncidentCommentInline, IncidentAttachmentInline]
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('consultazione', 'sezione', 'reporter')
        }),
        (_('Classificazione'), {
            'fields': ('category', 'severity', 'status')
        }),
        (_('Dettagli'), {
            'fields': ('title', 'description', 'occurred_at')
        }),
        (_('Assegnazione'), {
            'fields': ('assigned_to',)
        }),
        (_('Risoluzione'), {
            'fields': ('resolution', 'resolved_by', 'resolved_at'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def location_description(self, obj):
        return obj.location_description
    location_description.short_description = _('Luogo')


@admin.register(IncidentComment)
class IncidentCommentAdmin(admin.ModelAdmin):
    list_display = ['incident', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['content', 'author__email', 'incident__title']
    raw_id_fields = ['incident', 'author']
    readonly_fields = ['created_at']


@admin.register(IncidentAttachment)
class IncidentAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'incident', 'file_type', 'file_size', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['filename', 'description', 'incident__title']
    raw_id_fields = ['incident', 'uploaded_by']
    readonly_fields = ['uploaded_at', 'file_size', 'file_type', 'filename']
