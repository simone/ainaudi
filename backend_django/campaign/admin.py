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
    list_display = ['email', 'cognome', 'nome', 'comune', 'municipio', 'status', 'source', 'geo_display', 'n_plessi_vicini', 'requested_at']
    list_filter = ['status', 'source', 'comune__provincia__regione', 'comune', ('latitudine', admin.EmptyFieldListFilter)]
    search_fields = ['email', 'nome', 'cognome', 'comune__nome']
    raw_id_fields = ['comune', 'municipio', 'consultazione', 'campagna']
    date_hierarchy = 'requested_at'
    readonly_fields = [
        'requested_at', 'approved_at',
        'latitudine', 'longitudine', 'geocoded_at', 'geocode_source',
        'geocode_quality', 'geocode_place_id',
        'google_maps_link', 'plessi_vicini_display',
    ]

    fieldsets = (
        (None, {
            'fields': ('email', 'nome', 'cognome', 'telefono')
        }),
        (_('Dati anagrafici'), {
            'fields': ('comune_nascita', 'data_nascita', 'comune_residenza', 'indirizzo_residenza')
        }),
        (_('Fuorisede'), {
            'fields': ('fuorisede', 'comune_domicilio', 'indirizzo_domicilio'),
            'classes': ('collapse',),
        }),
        (_('Ambito'), {
            'fields': ('comune', 'municipio', 'consultazione', 'seggio_preferenza')
        }),
        (_('Stato'), {
            'fields': ('status', 'source', 'campagna')
        }),
        (_('Geolocalizzazione'), {
            'fields': ('latitudine', 'longitudine', 'geocode_source', 'geocode_quality', 'geocoded_at', 'geocode_place_id', 'google_maps_link'),
            'classes': ('collapse',),
        }),
        (_('Plessi vicini'), {
            'fields': ('plessi_vicini_display',),
            'classes': ('collapse',),
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

    @admin.display(description=_('Geo'))
    def geo_display(self, obj):
        if obj.latitudine and obj.longitudine:
            return format_html(
                '<a href="https://www.google.com/maps?q={},{}" target="_blank" title="{} ({})">'
                '<span style="color:green">&#x2713;</span></a>',
                obj.latitudine, obj.longitudine,
                obj.geocode_quality or '?', obj.geocode_source or '?',
            )
        return format_html('<span style="color:#ccc">&#x2717;</span>')

    @admin.display(description=_('Plessi'))
    def n_plessi_vicini(self, obj):
        plessi = obj.sezioni_vicine or []
        if not plessi:
            return '-'
        return len(plessi)

    @admin.display(description=_('Google Maps'))
    def google_maps_link(self, obj):
        if obj.latitudine and obj.longitudine:
            return format_html(
                '<a href="https://www.google.com/maps?q={},{}" target="_blank">Apri in Google Maps</a>',
                obj.latitudine, obj.longitudine,
            )
        return '-'

    @admin.display(description=_('Plessi vicini (top 10)'))
    def plessi_vicini_display(self, obj):
        plessi = obj.sezioni_vicine or []
        if not plessi:
            return _('Nessun plesso vicino calcolato')
        rows = []
        for p in plessi:
            sezioni = ', '.join(str(n) for n in p.get('sezioni', []))
            rows.append(
                f'<tr><td>{p.get("distanza_km", "?")} km</td>'
                f'<td>{p.get("indirizzo", "-")}</td>'
                f'<td>{sezioni}</td></tr>'
            )
        return format_html(
            '<table style="border-collapse:collapse;width:100%">'
            '<tr style="background:#f0f0f0"><th style="padding:4px 8px;text-align:left">Distanza</th>'
            '<th style="padding:4px 8px;text-align:left">Indirizzo</th>'
            '<th style="padding:4px 8px;text-align:left">Sezioni</th></tr>'
            '{}</table>',
            format_html(''.join(rows)),
        )

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
