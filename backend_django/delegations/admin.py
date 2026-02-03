"""
Admin configuration for Delegations (Electoral delegation management).

Gerarchia: PARTITO -> DELEGATO DI LISTA -> SUB-DELEGATO -> RDL
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import DelegatoDiLista, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti


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
    """Inline per vedere le designazioni fatte da una sub-delega."""
    model = DesignazioneRDL
    extra = 0
    fields = ['sezione', 'ruolo', 'cognome', 'nome', 'email', 'stato', 'is_attiva']
    readonly_fields = ['sezione', 'ruolo', 'cognome', 'nome', 'email', 'stato', 'is_attiva']
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DelegatoDiLista)
class DelegatoDiListaAdmin(admin.ModelAdmin):
    list_display = [
        'nome_completo', 'carica_display', 'circoscrizione',
        'consultazione', 'data_nomina', 'n_sub_deleghe', 'has_user'
    ]
    list_filter = ['carica', 'consultazione', 'data_nomina']
    search_fields = ['cognome', 'nome', 'email', 'circoscrizione']
    ordering = ['consultazione', 'cognome', 'nome']
    autocomplete_fields = ['consultazione']
    inlines = [SubDelegaInline]

    fieldsets = (
        (_('Consultazione'), {
            'fields': ('consultazione',)
        }),
        (_('Dati anagrafici'), {
            'fields': ('cognome', 'nome', 'luogo_nascita', 'data_nascita')
        }),
        (_('Carica elettiva'), {
            'fields': ('carica', 'circoscrizione')
        }),
        (_('Nomina dal Partito'), {
            'fields': ('data_nomina', 'numero_protocollo_nomina', 'documento_nomina')
        }),
        (_('Contatti'), {
            'fields': ('email', 'telefono')
        }),
    )

    def nome_completo(self, obj):
        return f"{obj.cognome} {obj.nome}"
    nome_completo.short_description = _('Nome')
    nome_completo.admin_order_field = 'cognome'

    def carica_display(self, obj):
        colors = {
            'DEPUTATO': 'primary',
            'SENATORE': 'info',
            'CONSIGLIERE_REGIONALE': 'warning',
            'EURODEPUTATO': 'success',
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
        user = obj.user
        if user and user.pk:
            return format_html('<span class="text-success">Si</span>')
        return format_html('<span class="text-muted">No</span>')
    has_user.short_description = _('Account')


@admin.register(SubDelega)
class SubDelegaAdmin(admin.ModelAdmin):
    list_display = [
        'nome_completo', 'delegato_display', 'tipo_delega_display', 'territorio_display',
        'data_delega', 'firma_status', 'n_designazioni', 'is_attiva'
    ]
    list_filter = ['is_attiva', 'tipo_delega', 'firma_autenticata', 'delegato__consultazione', 'delegato__carica']
    search_fields = ['cognome', 'nome', 'email', 'delegato__cognome', 'delegato__nome']
    ordering = ['delegato', 'cognome', 'nome']
    autocomplete_fields = ['delegato', 'regioni', 'province', 'comuni']
    filter_horizontal = ['regioni', 'province', 'comuni']
    inlines = [DesignazioneRDLInline]

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


@admin.register(DesignazioneRDL)
class DesignazioneRDLAdmin(admin.ModelAdmin):
    list_display = [
        'sezione', 'ruolo_display', 'nome_completo', 'email',
        'stato_display', 'designante_display', 'has_documento', 'is_attiva'
    ]
    list_filter = ['stato', 'ruolo', 'is_attiva', 'sub_delega__delegato__consultazione']
    search_fields = ['cognome', 'nome', 'email', 'sezione__numero']
    ordering = ['stato', 'sezione', 'ruolo']
    autocomplete_fields = ['delegato', 'sub_delega', 'sezione']
    actions = ['approva_bozze', 'rifiuta_bozze']

    fieldsets = (
        (_('Chi designa (uno dei due)'), {
            'fields': ('delegato', 'sub_delega'),
            'description': _('Specificare il Delegato (designazione diretta) OPPURE il Sub-Delegato')
        }),
        (_('Sezione e Ruolo'), {
            'fields': ('sezione', 'ruolo')
        }),
        (_('Stato designazione'), {
            'fields': ('stato',),
            'description': _('BOZZA = in attesa approvazione Delegato, CONFERMATA = designazione valida')
        }),
        (_('Dati anagrafici RDL'), {
            'fields': ('cognome', 'nome', 'luogo_nascita', 'data_nascita', 'domicilio')
        }),
        (_('Contatti'), {
            'fields': ('email', 'telefono')
        }),
        (_('Documento'), {
            'fields': ('documento_designazione', 'data_generazione_documento')
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

    def nome_completo(self, obj):
        return f"{obj.cognome} {obj.nome}"
    nome_completo.short_description = _('RDL')
    nome_completo.admin_order_field = 'cognome'

    def ruolo_display(self, obj):
        color = 'primary' if obj.ruolo == 'EFFETTIVO' else 'secondary'
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_ruolo_display())
    ruolo_display.short_description = _('Ruolo')

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

    def has_documento(self, obj):
        if obj.documento_designazione:
            return format_html('<a href="{}" target="_blank">PDF</a>', obj.documento_designazione.url)
        return '-'
    has_documento.short_description = _('Doc')

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


@admin.register(BatchGenerazioneDocumenti)
class BatchGenerazioneDocumentiAdmin(admin.ModelAdmin):
    list_display = ['sub_delega', 'tipo', 'stato', 'n_designazioni', 'created_at']
    list_filter = ['tipo', 'stato']
    ordering = ['-created_at']
    readonly_fields = ['n_designazioni', 'n_pagine', 'data_generazione', 'created_at', 'created_by_email']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by_email = request.user.email
        super().save_model(request, obj, form, change)


