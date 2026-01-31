"""
Admin configuration for Territorio app.
"""
from django.contrib import admin
from .models import Regione, Provincia, Comune, Municipio, SezioneElettorale


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
    list_display = ['codice_istat', 'nome', 'provincia', 'popolazione', 'cap']
    list_filter = ['provincia__regione', 'provincia']
    search_fields = ['nome', 'codice_istat', 'codice_catastale', 'cap']
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
