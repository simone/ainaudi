"""
Admin configuration for Delegations (Electoral delegation management).

Gerarchia: PARTITO -> DELEGATO -> SUB-DELEGATO -> RDL
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from territory.admin_filters import make_territory_filters

from .models import (
    Delegato, SubDelega, DesignazioneRDL,
    BatchGenerazioneDocumenti, EmailDesignazioneLog
)


class SubDelegaInline(admin.TabularInline):
    """Inline per vedere le sub-deleghe fatte da un Delegato."""
    model = SubDelega
    extra = 0
    fields = ['cognome', 'nome', 'email', 'tipo_delega', 'data_delega', 'firma_autenticata', 'is_attiva']
    readonly_fields = ['cognome', 'nome', 'email', 'tipo_delega', 'data_delega', 'firma_autenticata', 'is_attiva']
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class DesignazioneRDLInline(admin.TabularInline):
    """Inline per vedere le designazioni fatte da una sub-delega (SNAPSHOT FIELDS)."""
    model = DesignazioneRDL
    extra = 0
    fields = ['sezione', 'effettivo_display', 'supplente_display', 'stato', 'is_attiva']
    readonly_fields = ['sezione', 'effettivo_display', 'supplente_display', 'stato', 'is_attiva']
    show_change_link = True
    can_delete = False

    def effettivo_display(self, obj):
        if obj.effettivo_email:
            return f"{obj.effettivo_cognome} {obj.effettivo_nome}"
        return "-"
    effettivo_display.short_description = _('Effettivo')

    def supplente_display(self, obj):
        if obj.supplente_email:
            return f"{obj.supplente_cognome} {obj.supplente_nome}"
        return "-"
    supplente_display.short_description = _('Supplente')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Delegato)
class DelegatoAdmin(admin.ModelAdmin):
    list_display = [
        'nome_completo', 'carica_display', 'circoscrizione',
        'consultazione', 'data_nomina', 'n_sub_deleghe', 'has_user', 'territorio_display'
    ]
    list_filter = ['carica', 'consultazione', 'data_nomina']
    search_fields = ['cognome', 'nome', 'email', 'circoscrizione']
    ordering = ['consultazione', 'cognome', 'nome']
    autocomplete_fields = ['consultazione', 'regioni', 'province', 'comuni']
    filter_horizontal = ['regioni', 'province', 'comuni']
    inlines = [SubDelegaInline]

    fieldsets = (
        (_('Dati obbligatori'), {
            'fields': ('consultazione', 'cognome', 'nome')
        }),
        (_('Dati anagrafici opzionali'), {
            'fields': ('luogo_nascita', 'data_nascita'),
            'classes': ('collapse',)
        }),
        (_('Carica elettiva (opzionale)'), {
            'fields': ('carica', 'circoscrizione'),
            'classes': ('collapse',)
        }),
        (_('Territorio di competenza'), {
            'fields': ('regioni', 'province', 'comuni', 'municipi'),
            'description': _('Definisce quali sezioni elettorali il delegato può gestire')
        }),
        (_('Nomina dal Partito (opzionale)'), {
            'fields': ('data_nomina', 'numero_protocollo_nomina', 'documento_nomina'),
            'classes': ('collapse',)
        }),
        (_('Contatti (opzionali)'), {
            'fields': ('email', 'telefono'),
            'classes': ('collapse',)
        }),
    )

    def nome_completo(self, obj):
        return f"{obj.cognome} {obj.nome}"
    nome_completo.short_description = _('Nome')
    nome_completo.admin_order_field = 'cognome'

    def carica_display(self, obj):
        if not obj.carica:
            return '-'
        colors = {
            'DEPUTATO': 'primary',
            'SENATORE': 'info',
            'CONSIGLIERE_REGIONALE': 'warning',
            'EURODEPUTATO': 'success',
            'RAPPRESENTANTE_PARTITO': 'secondary',
        }
        color = colors.get(obj.carica, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_carica_display())
    carica_display.short_description = _('Carica')
    carica_display.admin_order_field = 'carica'

    def n_sub_deleghe(self, obj):
        count = obj.sub_deleghe.filter(is_attiva=True).count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    n_sub_deleghe.short_description = _('Sub-deleghe')

    def has_user(self, obj):
        from core.models import User
        if obj.email and User.objects.filter(email=obj.email).exists():
            return format_html('<span class="text-success">Si</span>')
        return format_html('<span class="text-muted">No</span>')
    has_user.short_description = _('Account')

    def territorio_display(self, obj):
        """Mostra territorio di competenza in forma breve."""
        parti = []
        if obj.regioni.exists():
            parti.append(f"{obj.regioni.count()} reg.")
        if obj.province.exists():
            parti.append(f"{obj.province.count()} prov.")
        if obj.comuni.exists():
            parti.append(f"{obj.comuni.count()} com.")
        if obj.municipi:
            parti.append(f"{len(obj.municipi)} mun.")
        return ', '.join(parti) if parti else '-'
    territorio_display.short_description = _('Territorio')


@admin.register(SubDelega)
class SubDelegaAdmin(admin.ModelAdmin):
    list_display = [
        'nome_completo', 'delegato_display', 'tipo_delega_display', 'territorio_display',
        'data_delega', 'firma_status', 'n_designazioni', 'is_attiva'
    ]
    list_filter = ['is_attiva', 'tipo_delega', 'firma_autenticata', 'delegato__consultazione', 'delegato__carica']
    search_fields = ['cognome', 'nome', 'email', 'delegato__cognome', 'delegato__nome']
    ordering = ['delegato', 'cognome', 'nome']
    # Temporaneamente disabilitato per permettere la migration
    # autocomplete_fields = ['delegato', 'regioni', 'province', 'comuni']
    autocomplete_fields = ['regioni', 'province', 'comuni']
    filter_horizontal = ['regioni', 'province', 'comuni']

    fieldsets = (
        (_('Delegato'), {
            'fields': ('delegato',)
        }),
        (_('Tipo di delega'), {
            'fields': ('tipo_delega',),
            'description': _('FIRMA_AUTENTICATA: può designare RDL direttamente. MAPPATURA: prepara bozze, il Delegato approva.')
        }),
        (_('Dati anagrafici Sub-Delegato'), {
            'fields': ('cognome', 'nome', 'luogo_nascita', 'data_nascita', 'domicilio')
        }),
        (_('Documento di identita'), {
            'fields': ('tipo_documento', 'numero_documento')
        }),
        (_('Territorio di competenza'), {
            'fields': ('regioni', 'province', 'comuni', 'municipi'),
            'description': _('Seleziona il livello appropriato: regioni per ambiti regionali, province per ambiti provinciali, comuni per ambiti comunali, municipi per grandi città')
        }),
        (_('Dati delega'), {
            'fields': ('data_delega', 'numero_protocollo', 'documento_delega')
        }),
        (_('Autenticazione firma'), {
            'fields': ('firma_autenticata', 'data_autenticazione', 'autenticatore'),
            'description': _('La firma deve essere autenticata da notaio o segretario comunale (richiesto per FIRMA_AUTENTICATA)')
        }),
        (_('Contatti'), {
            'fields': ('email', 'telefono')
        }),
        (_('Stato'), {
            'fields': ('is_attiva', 'revocata_il', 'motivo_revoca'),
            'classes': ('collapse',)
        }),
    )

    def tipo_delega_display(self, obj):
        colors = {
            'FIRMA_AUTENTICATA': 'success',
            'MAPPATURA': 'warning',
        }
        color = colors.get(obj.tipo_delega, 'secondary')
        label = 'Designa' if obj.tipo_delega == 'FIRMA_AUTENTICATA' else 'Mappa'
        return format_html('<span class="badge bg-{}">{}</span>', color, label)
    tipo_delega_display.short_description = _('Tipo')

    def nome_completo(self, obj):
        return f"{obj.cognome} {obj.nome}"
    nome_completo.short_description = _('Sub-Delegato')
    nome_completo.admin_order_field = 'cognome'

    def delegato_display(self, obj):
        return f"{obj.delegato.get_carica_display()} {obj.delegato.nome_completo}"
    delegato_display.short_description = _('Delegato')

    def territorio_display(self, obj):
        parti = []
        # Regioni
        regioni = list(obj.regioni.values_list('nome', flat=True)[:2])
        if regioni:
            text = ', '.join(regioni)
            if obj.regioni.count() > 2:
                text += f' (+{obj.regioni.count() - 2})'
            parti.append(f"Reg: {text}")
        # Province
        province = list(obj.province.values_list('nome', flat=True)[:2])
        if province:
            text = ', '.join(province)
            if obj.province.count() > 2:
                text += f' (+{obj.province.count() - 2})'
            parti.append(f"Prov: {text}")
        # Comuni
        comuni = list(obj.comuni.values_list('nome', flat=True)[:2])
        if comuni:
            text = ', '.join(comuni)
            if obj.comuni.count() > 2:
                text += f' (+{obj.comuni.count() - 2})'
            parti.append(text)
        # Municipi
        if obj.municipi:
            parti.append(f"Mun. {', '.join(map(str, obj.municipi[:3]))}")
        return ' | '.join(parti) if parti else '-'
    territorio_display.short_description = _('Territorio')

    def firma_status(self, obj):
        if obj.firma_autenticata:
            return format_html('<span class="text-success">Autenticata</span>')
        return format_html('<span class="text-warning">Da autenticare</span>')
    firma_status.short_description = _('Firma')

    def n_designazioni(self, obj):
        count = obj.designazioni_rdl.filter(is_attiva=True).count()
        return format_html('<span class="badge bg-success">{}</span>', count)
    n_designazioni.short_description = _('RDL')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by_email = request.user.email
        super().save_model(request, obj, form, change)


# DesignazioneRDL are shown only as inline of ProcessoDesignazione
# Uncomment if you need standalone admin for designazioni without processo
# @admin.register(DesignazioneRDL)
class DesignazioneRDLAdmin(admin.ModelAdmin):
    """Admin per DesignazioneRDL (SNAPSHOT FIELDS: campi diretti immutabili)."""
    list_display = [
        'sezione', 'effettivo_display', 'supplente_display',
        'stato_display', 'designante_display', 'processo', 'is_attiva'
    ]
    list_filter = ['stato', 'is_attiva', 'sub_delega__delegato__consultazione']
    search_fields = [
        'sezione__numero',
        'sezione__comune__nome',
        'effettivo_cognome', 'effettivo_nome', 'effettivo_email',
        'supplente_cognome', 'supplente_nome', 'supplente_email'
    ]
    ordering = ['stato', 'sezione']
    autocomplete_fields = ['delegato', 'sub_delega', 'sezione', 'processo']
    actions = ['approva_bozze', 'rifiuta_bozze']

    fieldsets = (
        (_('Chi designa (uno dei due)'), {
            'fields': ('delegato', 'sub_delega'),
            'description': _('Specificare il Delegato (designazione diretta) OPPURE il Sub-Delegato')
        }),
        (_('Sezione'), {
            'fields': ('sezione',)
        }),
        (_('RDL Effettivo (snapshot dati)'), {
            'fields': ('effettivo_cognome', 'effettivo_nome', 'effettivo_email', 'effettivo_telefono',
                      'effettivo_luogo_nascita', 'effettivo_data_nascita', 'effettivo_domicilio'),
            'classes': ('collapse',)
        }),
        (_('RDL Supplente (snapshot dati)'), {
            'fields': ('supplente_cognome', 'supplente_nome', 'supplente_email', 'supplente_telefono',
                      'supplente_luogo_nascita', 'supplente_data_nascita', 'supplente_domicilio'),
            'classes': ('collapse',)
        }),
        (_('Stato designazione'), {
            'fields': ('stato', 'processo'),
            'description': _('BOZZA = in attesa approvazione Delegato, CONFERMATA = designazione valida')
        }),
        (_('Approvazione'), {
            'fields': ('approvata_da_email', 'data_approvazione'),
            'classes': ('collapse',)
        }),
        (_('Revoca'), {
            'fields': ('is_attiva', 'revocata_il', 'motivo_revoca'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['approvata_da_email', 'data_approvazione']

    def effettivo_display(self, obj):
        if obj.effettivo_email:
            return format_html(
                '<strong>{} {}</strong><br><small>{}</small>',
                obj.effettivo_cognome, obj.effettivo_nome, obj.effettivo_email
            )
        return format_html('<span class="text-muted">-</span>')
    effettivo_display.short_description = _('Effettivo')

    def supplente_display(self, obj):
        if obj.supplente_email:
            return format_html(
                '<strong>{} {}</strong><br><small>{}</small>',
                obj.supplente_cognome, obj.supplente_nome, obj.supplente_email
            )
        return format_html('<span class="text-muted">-</span>')
    supplente_display.short_description = _('Supplente')

    def stato_display(self, obj):
        colors = {
            'BOZZA': 'warning',
            'CONFERMATA': 'success',
            'REVOCATA': 'danger',
        }
        color = colors.get(obj.stato, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_stato_display())
    stato_display.short_description = _('Stato')

    def designante_display(self, obj):
        return obj.designante_nome
    designante_display.short_description = _('Designato da')

    @admin.action(description=_('Approva bozze selezionate'))
    def approva_bozze(self, request, queryset):
        bozze = queryset.filter(stato='BOZZA')
        count = 0
        for designazione in bozze:
            designazione.approva(request.user)
            count += 1
        self.message_user(request, f'{count} designazioni approvate.')

    @admin.action(description=_('Rifiuta bozze selezionate'))
    def rifiuta_bozze(self, request, queryset):
        bozze = queryset.filter(stato='BOZZA')
        count = 0
        for designazione in bozze:
            designazione.rifiuta(request.user, 'Rifiutato da admin')
            count += 1
        self.message_user(request, f'{count} designazioni rifiutate.')


class DesignazioniProcessoInline(admin.TabularInline):
    """Inline per vedere le designazioni di un processo."""
    model = DesignazioneRDL
    extra = 0
    fields = ['sezione', 'effettivo_display', 'supplente_display', 'stato']
    readonly_fields = ['sezione', 'effettivo_display', 'supplente_display', 'stato']
    show_change_link = False
    can_delete = False

    def effettivo_display(self, obj):
        if obj.effettivo_cognome:
            return f"{obj.effettivo_cognome} {obj.effettivo_nome}"
        return "-"
    effettivo_display.short_description = _('Effettivo')

    def supplente_display(self, obj):
        if obj.supplente_cognome:
            return f"{obj.supplente_cognome} {obj.supplente_nome}"
        return "-"
    supplente_display.short_description = _('Supplente')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BatchGenerazioneDocumenti)
class BatchGenerazioneDocumentiAdmin(admin.ModelAdmin):
    list_display = ['id', 'consultazione', 'comune', 'delegato', 'stato', 'n_designazioni', 'created_at']
    list_filter = ['stato', 'consultazione', *make_territory_filters('comune')]
    search_fields = ['consultazione__nome', 'comune__nome', 'created_by_email', 'delegato__cognome', 'delegato__nome']
    ordering = ['-created_at']
    autocomplete_fields = ['consultazione', 'comune', 'delegato', 'template_individuale', 'template_cumulativo']
    readonly_fields = [
        'n_designazioni', 'n_pagine',
        'data_generazione_individuale', 'data_generazione_cumulativo',
        'approvata_at', 'approvata_da_email',
        'created_at', 'created_by_email'
    ]
    inlines = [DesignazioniProcessoInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by_email = request.user.email
        super().save_model(request, obj, form, change)


@admin.register(EmailDesignazioneLog)
class EmailDesignazioneLogAdmin(admin.ModelAdmin):
    """Admin per log invio email designazioni."""

    list_display = [
        'id',
        'processo',
        'destinatario_email',
        'destinatario_nome',
        'tipo_rdl',
        'stato',
        'sent_at',
        'sent_by_email',
    ]

    list_filter = [
        'stato',
        'tipo_rdl',
        'sent_at',
    ]

    search_fields = [
        'destinatario_email',
        'destinatario_nome',
        'sent_by_email',
        'subject',
    ]

    readonly_fields = [
        'processo',
        'designazione',
        'destinatario_email',
        'destinatario_nome',
        'tipo_rdl',
        'stato',
        'errore',
        'subject',
        'sent_at',
        'sent_by_email',
    ]

    date_hierarchy = 'sent_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


