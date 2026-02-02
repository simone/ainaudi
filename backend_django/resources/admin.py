"""
Admin configuration for Resources (Documents and FAQ).
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CategoriaDocumento, Documento, CategoriaFAQ, FAQ


@admin.register(CategoriaDocumento)
class CategoriaDocumentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'icona_preview', 'n_documenti', 'ordine', 'is_attiva']
    list_editable = ['ordine', 'is_attiva']
    search_fields = ['nome']
    ordering = ['ordine', 'nome']

    def icona_preview(self, obj):
        return format_html('<i class="fas {}"></i> {}', obj.icona, obj.icona)
    icona_preview.short_description = _('Icona')

    def n_documenti(self, obj):
        return obj.documenti.filter(is_attivo=True).count()
    n_documenti.short_description = _('Documenti')


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = [
        'titolo', 'categoria', 'scope_display', 'tipo_file',
        'dimensione_formattata', 'in_evidenza', 'is_pubblico', 'is_attivo', 'download_link'
    ]
    list_filter = ['scope', 'categoria', 'tipo_file', 'in_evidenza', 'is_pubblico', 'is_attivo']
    search_fields = ['titolo', 'descrizione']
    list_editable = ['in_evidenza', 'is_pubblico', 'is_attivo']
    ordering = ['-in_evidenza', 'ordine', '-created_at']
    readonly_fields = ['tipo_file', 'dimensione', 'created_at', 'updated_at', 'created_by']
    autocomplete_fields = ['consultazione_specifica']

    fieldsets = (
        (None, {
            'fields': ('titolo', 'descrizione', 'categoria', 'file')
        }),
        (_('Visibilità'), {
            'fields': ('scope', 'consultazione_specifica', 'is_pubblico', 'in_evidenza', 'is_attivo', 'ordine'),
            'description': _('Determina quando e a chi è visibile questo documento')
        }),
        (_('Informazioni'), {
            'fields': ('tipo_file', 'dimensione', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def scope_display(self, obj):
        colors = {
            'TUTTI': 'secondary',
            'REFERENDUM': 'success',
            'COMUNALI': 'info',
            'REGIONALI': 'warning',
            'POLITICHE': 'primary',
            'EUROPEE': 'dark',
            'SPECIFICO': 'danger',
        }
        color = colors.get(obj.scope, 'secondary')
        text = obj.get_scope_display()
        if obj.scope == 'SPECIFICO' and obj.consultazione_specifica:
            text = f'{obj.consultazione_specifica.nome}'
        return format_html('<span class="badge bg-{}">{}</span>', color, text)
    scope_display.short_description = _('Scope')
    scope_display.admin_order_field = 'scope'

    def download_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return '-'
    download_link.short_description = _('Download')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CategoriaFAQ)
class CategoriaFAQAdmin(admin.ModelAdmin):
    list_display = ['nome', 'icona_preview', 'n_faqs', 'ordine', 'is_attiva']
    list_editable = ['ordine', 'is_attiva']
    search_fields = ['nome']
    ordering = ['ordine', 'nome']

    def icona_preview(self, obj):
        return format_html('<i class="fas {}"></i> {}', obj.icona, obj.icona)
    icona_preview.short_description = _('Icona')

    def n_faqs(self, obj):
        return obj.faqs.filter(is_attivo=True).count()
    n_faqs.short_description = _('FAQ')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'domanda_short', 'categoria', 'scope_display',
        'visualizzazioni', 'rating', 'in_evidenza', 'is_pubblico', 'is_attivo'
    ]
    list_filter = ['scope', 'categoria', 'in_evidenza', 'is_pubblico', 'is_attivo']
    search_fields = ['domanda', 'risposta']
    list_editable = ['in_evidenza', 'is_pubblico', 'is_attivo']
    ordering = ['-in_evidenza', 'categoria__ordine', 'ordine', '-created_at']
    readonly_fields = ['visualizzazioni', 'utile_si', 'utile_no', 'created_at', 'updated_at', 'created_by']
    autocomplete_fields = ['consultazione_specifica']

    fieldsets = (
        (None, {
            'fields': ('domanda', 'risposta', 'categoria')
        }),
        (_('Visibilità'), {
            'fields': ('scope', 'consultazione_specifica', 'is_pubblico', 'in_evidenza', 'is_attivo', 'ordine')
        }),
        (_('Statistiche'), {
            'fields': ('visualizzazioni', 'utile_si', 'utile_no'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def domanda_short(self, obj):
        return obj.domanda[:60] + '...' if len(obj.domanda) > 60 else obj.domanda
    domanda_short.short_description = _('Domanda')

    def scope_display(self, obj):
        colors = {
            'TUTTI': 'secondary',
            'REFERENDUM': 'success',
            'COMUNALI': 'info',
            'REGIONALI': 'warning',
            'POLITICHE': 'primary',
            'EUROPEE': 'dark',
            'SPECIFICO': 'danger',
        }
        color = colors.get(obj.scope, 'secondary')
        text = obj.get_scope_display()
        if obj.scope == 'SPECIFICO' and obj.consultazione_specifica:
            text = f'{obj.consultazione_specifica.nome}'
        return format_html('<span class="badge bg-{}">{}</span>', color, text)
    scope_display.short_description = _('Scope')
    scope_display.admin_order_field = 'scope'

    def rating(self, obj):
        perc = obj.percentuale_utile
        if perc is None:
            return '-'
        color = 'success' if perc >= 70 else 'warning' if perc >= 50 else 'danger'
        return format_html(
            '<span class="text-{}">{} / {} ({}%)</span>',
            color, obj.utile_si, obj.utile_si + obj.utile_no, perc
        )
    rating.short_description = _('Utile?')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
