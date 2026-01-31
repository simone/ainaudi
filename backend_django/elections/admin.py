"""
Django Admin configuration for elections models.
Territory admin is in territorio/admin.py.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    CircoscrizioneCamera, CircoscrizioneSenato, CircoscrizioneEuropee,
    ConsultazioneElettorale, TipoElezione, SchedaElettorale,
    ListaElettorale, Candidato,
)


# =============================================================================
# CIRCUMSCRIPTIONS ADMIN
# =============================================================================

@admin.register(CircoscrizioneCamera)
class CircoscrizioneCameraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nome']
    filter_horizontal = ['regioni']
    ordering = ['numero']


@admin.register(CircoscrizioneSenato)
class CircoscrizioneSenatoAdmin(admin.ModelAdmin):
    list_display = ['regione']
    autocomplete_fields = ['regione']


@admin.register(CircoscrizioneEuropee)
class CircoscrizioneEuropeeAdmin(admin.ModelAdmin):
    list_display = ['codice', 'get_codice_display']
    filter_horizontal = ['regioni']


# =============================================================================
# ELECTIONS ADMIN
# =============================================================================

class TipoElezioneInline(admin.TabularInline):
    model = TipoElezione
    extra = 0
    autocomplete_fields = ['regione']
    filter_horizontal = ['comuni']


@admin.register(ConsultazioneElettorale)
class ConsultazioneElettoraleAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_inizio', 'data_fine', 'is_attiva']
    list_filter = ['is_attiva', 'data_inizio']
    search_fields = ['nome']
    date_hierarchy = 'data_inizio'
    inlines = [TipoElezioneInline]

    fieldsets = (
        (None, {
            'fields': ('nome', 'descrizione', 'is_attiva')
        }),
        (_('Date'), {
            'fields': ('data_inizio', 'data_fine')
        }),
    )


class SchedaInline(admin.TabularInline):
    model = SchedaElettorale
    extra = 0
    fields = ['nome', 'colore', 'ordine']


@admin.register(TipoElezione)
class TipoElezioneAdmin(admin.ModelAdmin):
    list_display = ['consultazione', 'tipo', 'ambito_nazionale', 'regione']
    list_filter = ['tipo', 'ambito_nazionale', 'consultazione']
    search_fields = ['consultazione__nome', 'tipo', 'regione__nome']
    autocomplete_fields = ['consultazione', 'regione']
    filter_horizontal = ['comuni']
    inlines = [SchedaInline]


class ListaInline(admin.TabularInline):
    model = ListaElettorale
    extra = 0
    fields = ['nome', 'nome_breve', 'ordine_scheda']


@admin.register(SchedaElettorale)
class SchedaElettoraleAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_elezione', 'colore', 'ordine']
    list_filter = ['tipo_elezione__tipo', 'tipo_elezione__consultazione']
    search_fields = ['nome']
    autocomplete_fields = ['tipo_elezione']
    inlines = [ListaInline]

    fieldsets = (
        (None, {
            'fields': ('tipo_elezione', 'nome', 'colore', 'ordine')
        }),
        (_('Referendum'), {
            'fields': ('testo_quesito',),
            'classes': ('collapse',)
        }),
        (_('Schema dati'), {
            'fields': ('schema_voti',),
            'classes': ('collapse',)
        }),
    )


class CandidatoInline(admin.TabularInline):
    model = Candidato
    fk_name = 'lista'
    extra = 0
    fields = ['cognome', 'nome', 'posizione_lista']


@admin.register(ListaElettorale)
class ListaElettoraleAdmin(admin.ModelAdmin):
    list_display = ['nome', 'nome_breve', 'scheda', 'ordine_scheda', 'coalizione']
    list_filter = ['scheda__tipo_elezione__tipo', 'scheda__tipo_elezione__consultazione']
    search_fields = ['nome', 'nome_breve']
    autocomplete_fields = ['scheda', 'coalizione']
    inlines = [CandidatoInline]


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['cognome', 'nome', 'lista', 'posizione_lista', 'is_sindaco', 'is_presidente']
    list_filter = ['is_sindaco', 'is_presidente', 'lista__scheda__tipo_elezione__tipo']
    search_fields = ['cognome', 'nome']
    autocomplete_fields = ['lista', 'scheda']

    fieldsets = (
        (None, {
            'fields': ('lista', 'scheda')
        }),
        (_('Dati anagrafici'), {
            'fields': ('cognome', 'nome', 'data_nascita', 'luogo_nascita')
        }),
        (_('Posizione'), {
            'fields': ('posizione_lista', 'collegio_uninominale')
        }),
        (_('Ruoli speciali'), {
            'fields': ('is_sindaco', 'is_presidente')
        }),
    )
