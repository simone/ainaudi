"""
Admin configuration for Territorio app.
"""
from django.contrib import admin
from .models import (
    Regione, Provincia, Comune, Municipio, SezioneElettorale,
    TerritorialPartitionSet, TerritorialPartitionUnit, TerritorialPartitionMembership
)


@admin.register(Regione)
class RegioneAdmin(admin.ModelAdmin):
    list_display = ['codice_istat', 'nome', 'statuto_speciale']
    list_filter = ['statuto_speciale']
    search_fields = ['nome', 'codice_istat']
    ordering = ['codice_istat']


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ['codice_istat', 'sigla', 'nome', 'regione', 'is_citta_metropolitana']
    list_filter = ['regione', 'is_citta_metropolitana']
    search_fields = ['nome', 'sigla', 'codice_istat']
    ordering = ['regione__codice_istat', 'nome']
    autocomplete_fields = ['regione']


@admin.register(Comune)
class ComuneAdmin(admin.ModelAdmin):
    list_display = ['codice_istat', 'nome', 'provincia', 'sopra_15000_abitanti']
    list_filter = ['provincia__regione', 'provincia', 'sopra_15000_abitanti']
    search_fields = ['nome', 'codice_istat', 'codice_catastale']
    ordering = ['nome']
    autocomplete_fields = ['provincia']


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nome', 'comune']
    list_filter = ['comune__provincia__regione', 'comune']
    search_fields = ['nome', 'comune__nome']
    ordering = ['comune', 'numero']
    autocomplete_fields = ['comune']


@admin.register(SezioneElettorale)
class SezioneElettoraleAdmin(admin.ModelAdmin):
    list_display = ['numero', 'comune', 'municipio', 'denominazione', 'n_elettori', 'is_attiva']
    list_filter = ['is_attiva', 'comune__provincia__regione', 'comune__provincia', 'comune']
    search_fields = ['numero', 'denominazione', 'indirizzo', 'comune__nome']
    ordering = ['comune', 'numero']
    autocomplete_fields = ['comune', 'municipio']


# =============================================================================
# TERRITORIAL PARTITIONS (Circoscrizioni, Collegi)
# =============================================================================

class TerritorialPartitionUnitInline(admin.TabularInline):
    model = TerritorialPartitionUnit
    extra = 0
    fields = ['codice', 'nome', 'parent_unit']
    autocomplete_fields = ['parent_unit']


@admin.register(TerritorialPartitionSet)
class TerritorialPartitionSetAdmin(admin.ModelAdmin):
    list_display = ['nome', 'partition_type', 'normative_ref']
    list_filter = ['partition_type']
    search_fields = ['nome', 'descrizione', 'normative_ref']
    inlines = [TerritorialPartitionUnitInline]


@admin.register(TerritorialPartitionUnit)
class TerritorialPartitionUnitAdmin(admin.ModelAdmin):
    list_display = ['codice', 'nome', 'partition_set', 'parent_unit']
    list_filter = ['partition_set', 'partition_set__partition_type']
    search_fields = ['codice', 'nome']
    ordering = ['partition_set', 'codice']
    autocomplete_fields = ['partition_set', 'parent_unit']


@admin.register(TerritorialPartitionMembership)
class TerritorialPartitionMembershipAdmin(admin.ModelAdmin):
    list_display = ['unit', 'get_territorio', 'get_partition_type']
    list_filter = ['unit__partition_set', 'unit__partition_set__partition_type']
    search_fields = [
        'unit__nome', 'unit__codice',
        'comune__nome', 'provincia__nome', 'regione__nome'
    ]
    autocomplete_fields = ['unit', 'comune', 'provincia', 'regione']

    @admin.display(description='Territorio')
    def get_territorio(self, obj):
        return obj.comune or obj.provincia or obj.regione

    @admin.display(description='Tipo partizione')
    def get_partition_type(self, obj):
        return obj.unit.partition_set.get_partition_type_display()
