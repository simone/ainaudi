"""
Admin configuration for Campaign (Recruitment campaigns and RDL registrations).
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CampagnaReclutamento, RdlRegistration


@admin.register(CampagnaReclutamento)
class CampagnaReclutamentoAdmin(admin.ModelAdmin):
    list_display = [
        'nome', 'consultazione', 'stato_display', 'data_apertura', 'data_chiusura',
        'n_registrazioni', 'posti_display', 'is_aperta_display', 'created_by_email'
    ]
    list_filter = ['stato', 'consultazione', 'richiedi_approvazione']
    search_fields = ['nome', 'slug', 'descrizione']
    ordering = ['-data_apertura']
    autocomplete_fields = ['consultazione', 'delegato', 'sub_delega']
    filter_horizontal = ['territorio_regioni', 'territorio_province', 'territorio_comuni']
    prepopulated_fields = {'slug': ('nome',)}
    readonly_fields = ['n_registrazioni', 'posti_disponibili', 'is_aperta', 'created_at', 'updated_at']

    fieldsets = (
        (_('Consultazione'), {
            'fields': ('consultazione',)
        }),
        (_('Identificazione Campagna'), {
            'fields': ('nome', 'slug', 'descrizione')
        }),
        (_('Periodo'), {
            'fields': ('data_apertura', 'data_chiusura', 'stato')
        }),
        (_('Territorio'), {
            'fields': ('territorio_regioni', 'territorio_province', 'territorio_comuni'),
            'description': _('Limita i comuni dove è possibile registrarsi. Lasciare vuoto per tutti i comuni.')
        }),
        (_('Proprietario'), {
            'fields': ('delegato', 'sub_delega'),
            'description': _('Chi ha creato/gestisce questa campagna')
        }),
        (_('Configurazione'), {
            'fields': ('richiedi_approvazione', 'max_registrazioni', 'messaggio_conferma')
        }),
        (_('Statistiche'), {
            'fields': ('n_registrazioni', 'posti_disponibili', 'is_aperta'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_by_email', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stato_display(self, obj):
        colors = {
            'BOZZA': 'secondary',
            'ATTIVA': 'success',
            'CHIUSA': 'danger',
        }
        color = colors.get(obj.stato, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_stato_display())
    stato_display.short_description = _('Stato')

    def n_registrazioni(self, obj):
        return obj.n_registrazioni
    n_registrazioni.short_description = _('Registrazioni')

    def posti_display(self, obj):
        if obj.max_registrazioni is None:
            return 'Illimitati'
        disponibili = obj.posti_disponibili
        return f'{disponibili}/{obj.max_registrazioni}'
    posti_display.short_description = _('Posti')

    def is_aperta_display(self, obj):
        if obj.is_aperta:
            return format_html('<span class="text-success">Aperta</span>')
        return format_html('<span class="text-muted">Chiusa</span>')
    is_aperta_display.short_description = _('Attiva ora')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by_email = request.user.email
        super().save_model(request, obj, form, change)


@admin.register(RdlRegistration)
class RdlRegistrationAdmin(admin.ModelAdmin):
    list_display = ['email', 'cognome', 'nome', 'comune', 'municipio', 'status', 'source', 'requested_at']
    list_filter = ['status', 'source', 'comune__provincia__regione', 'comune']
    search_fields = ['email', 'nome', 'cognome', 'comune__nome']
    raw_id_fields = ['comune', 'municipio', 'consultazione', 'campagna']
    date_hierarchy = 'requested_at'
    readonly_fields = ['requested_at', 'approved_at']

    fieldsets = (
        (None, {
            'fields': ('email', 'nome', 'cognome', 'telefono')
        }),
        (_('Dati anagrafici'), {
            'fields': ('comune_nascita', 'data_nascita', 'comune_residenza', 'indirizzo_residenza')
        }),
        (_('Ambito'), {
            'fields': ('comune', 'municipio', 'consultazione', 'seggio_preferenza')
        }),
        (_('Stato'), {
            'fields': ('status', 'source', 'campagna')
        }),
        (_('Approvazione'), {
            'fields': ('approved_by_email', 'approved_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('Note'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_selected', 'reject_selected']

    def approve_selected(self, request, queryset):
        count = 0
        for reg in queryset.filter(status='PENDING'):
            reg.approve(request.user)
            count += 1
        self.message_user(request, f'{count} registrazioni approvate.')
    approve_selected.short_description = _('Approva selezionati')

    def reject_selected(self, request, queryset):
        count = queryset.filter(status='PENDING').update(status='REJECTED')
        self.message_user(request, f'{count} registrazioni rifiutate.')
    reject_selected.short_description = _('Rifiuta selezionati')
