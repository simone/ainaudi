"""
Django Admin configuration for sections models.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import SectionAssignment, DatiSezione, DatiScheda, SectionDataHistory, RdlRegistration


@admin.register(RdlRegistration)
class RdlRegistrationAdmin(admin.ModelAdmin):
    list_display = ['email', 'cognome', 'nome', 'comune', 'municipio', 'status', 'source', 'requested_at']
    list_filter = ['status', 'source', 'comune__provincia__regione', 'comune']
    search_fields = ['email', 'nome', 'cognome', 'comune__nome']
    raw_id_fields = ['comune', 'municipio', 'user', 'approved_by']
    date_hierarchy = 'requested_at'
    readonly_fields = ['requested_at', 'approved_at']

    fieldsets = (
        (None, {
            'fields': ('email', 'nome', 'cognome', 'telefono')
        }),
        (_('Ambito'), {
            'fields': ('comune', 'municipio')
        }),
        (_('Stato'), {
            'fields': ('status', 'source', 'user')
        }),
        (_('Approvazione'), {
            'fields': ('approved_by', 'approved_at', 'rejection_reason'),
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


class DatiSchedaInline(admin.TabularInline):
    model = DatiScheda
    extra = 0
    fields = ['scheda', 'schede_autenticate', 'schede_bianche', 'schede_nulle', 'is_valid']
    readonly_fields = ['is_valid']


@admin.register(SectionAssignment)
class SectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ['sezione', 'rdl_registration', 'role', 'consultazione', 'assigned_at']
    list_filter = ['role', 'consultazione', 'sezione__comune__provincia__regione']
    search_fields = [
        'rdl_registration__email', 'rdl_registration__nome', 'rdl_registration__cognome',
        'sezione__comune__nome', 'sezione__numero'
    ]
    raw_id_fields = ['sezione', 'consultazione', 'rdl_registration', 'user', 'assigned_by']
    date_hierarchy = 'assigned_at'

    fieldsets = (
        (None, {
            'fields': ('sezione', 'consultazione', 'rdl_registration', 'role')
        }),
        (_('Audit'), {
            'fields': ('user', 'assigned_by', 'assigned_at', 'notes'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['assigned_at', 'user']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
            # Set user from rdl_registration
            if obj.rdl_registration and obj.rdl_registration.user:
                obj.user = obj.rdl_registration.user
        super().save_model(request, obj, form, change)


@admin.register(DatiSezione)
class DatiSezioneAdmin(admin.ModelAdmin):
    list_display = [
        'sezione', 'consultazione', 'totale_elettori', 'totale_votanti',
        'affluenza_percentuale', 'is_complete', 'is_verified'
    ]
    list_filter = [
        'is_complete', 'is_verified', 'consultazione',
        'sezione__comune__provincia__regione', 'sezione__comune'
    ]
    search_fields = ['sezione__comune__nome', 'sezione__numero']
    raw_id_fields = ['sezione', 'consultazione', 'inserito_da', 'verified_by']
    inlines = [DatiSchedaInline]
    date_hierarchy = 'aggiornato_at'

    fieldsets = (
        (None, {
            'fields': ('sezione', 'consultazione')
        }),
        (_('Affluenza'), {
            'fields': (
                ('elettori_maschi', 'elettori_femmine'),
                ('votanti_maschi', 'votanti_femmine'),
            )
        }),
        (_('Stato'), {
            'fields': ('is_complete', 'is_verified', 'verified_by', 'verified_at')
        }),
        (_('Audit'), {
            'fields': ('inserito_da', 'inserito_at', 'aggiornato_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['aggiornato_at']

    def totale_elettori(self, obj):
        return obj.totale_elettori
    totale_elettori.short_description = _('Tot. elettori')

    def totale_votanti(self, obj):
        return obj.totale_votanti
    totale_votanti.short_description = _('Tot. votanti')

    def affluenza_percentuale(self, obj):
        aff = obj.affluenza_percentuale
        return f'{aff}%' if aff else '-'
    affluenza_percentuale.short_description = _('Affluenza')


@admin.register(DatiScheda)
class DatiSchedaAdmin(admin.ModelAdmin):
    list_display = [
        'dati_sezione', 'scheda', 'schede_autenticate',
        'schede_bianche', 'schede_nulle', 'totale_voti_validi', 'is_valid'
    ]
    list_filter = [
        'is_valid', 'scheda__tipo_elezione__tipo',
        'dati_sezione__consultazione'
    ]
    search_fields = [
        'dati_sezione__sezione__comune__nome',
        'dati_sezione__sezione__numero',
        'scheda__nome'
    ]
    raw_id_fields = ['dati_sezione', 'scheda']

    fieldsets = (
        (None, {
            'fields': ('dati_sezione', 'scheda')
        }),
        (_('Conteggio schede'), {
            'fields': (
                ('schede_ricevute', 'schede_autenticate'),
                ('schede_bianche', 'schede_nulle', 'schede_contestate'),
            )
        }),
        (_('Voti'), {
            'fields': ('voti',)
        }),
        (_('Validazione'), {
            'fields': ('is_valid', 'errori_validazione'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('inserito_at', 'aggiornato_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['aggiornato_at', 'totale_voti_validi']

    def totale_voti_validi(self, obj):
        return obj.totale_voti_validi
    totale_voti_validi.short_description = _('Tot. voti validi')


@admin.register(SectionDataHistory)
class SectionDataHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'dati_sezione', 'campo', 'modificato_da', 'modificato_at'
    ]
    list_filter = ['campo', 'modificato_at']
    search_fields = [
        'dati_sezione__sezione__comune__nome',
        'modificato_da__email'
    ]
    raw_id_fields = ['dati_sezione', 'dati_scheda', 'modificato_da']
    date_hierarchy = 'modificato_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
