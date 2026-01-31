"""
Serializers for territorio models.
"""
from rest_framework import serializers
from .models import Regione, Provincia, Comune, Municipio, SezioneElettorale


class RegioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regione
        fields = ['id', 'codice_istat', 'nome', 'statuto_speciale']


class ProvinciaListSerializer(serializers.ModelSerializer):
    regione_nome = serializers.CharField(source='regione.nome', read_only=True)

    class Meta:
        model = Provincia
        fields = ['id', 'codice_istat', 'sigla', 'nome', 'regione', 'regione_nome', 'is_citta_metropolitana']


class ProvinciaSerializer(serializers.ModelSerializer):
    regione = RegioneSerializer(read_only=True)

    class Meta:
        model = Provincia
        fields = ['id', 'codice_istat', 'sigla', 'nome', 'regione', 'is_citta_metropolitana']


class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ['id', 'numero', 'nome']


class ComuneListSerializer(serializers.ModelSerializer):
    provincia_sigla = serializers.CharField(source='provincia.sigla', read_only=True)
    provincia_nome = serializers.CharField(source='provincia.nome', read_only=True)
    regione_nome = serializers.CharField(source='provincia.regione.nome', read_only=True)

    class Meta:
        model = Comune
        fields = [
            'id', 'codice_istat', 'codice_catastale', 'nome',
            'provincia', 'provincia_sigla', 'provincia_nome', 'regione_nome',
            'popolazione', 'cap', 'sistema_elettorale_comunali'
        ]


class ComuneSerializer(serializers.ModelSerializer):
    provincia = ProvinciaSerializer(read_only=True)
    municipi = MunicipioSerializer(many=True, read_only=True)

    class Meta:
        model = Comune
        fields = [
            'id', 'codice_istat', 'codice_catastale', 'nome',
            'provincia', 'popolazione', 'cap',
            'sistema_elettorale_comunali', 'municipi'
        ]


class SezioneElettoraleListSerializer(serializers.ModelSerializer):
    comune_nome = serializers.CharField(source='comune.nome', read_only=True)
    provincia_sigla = serializers.CharField(source='comune.provincia.sigla', read_only=True)

    class Meta:
        model = SezioneElettorale
        fields = [
            'id', 'numero', 'comune', 'comune_nome', 'provincia_sigla',
            'denominazione', 'n_elettori', 'is_attiva'
        ]


class SezioneElettoraleSerializer(serializers.ModelSerializer):
    comune = ComuneListSerializer(read_only=True)
    municipio = MunicipioSerializer(read_only=True)

    class Meta:
        model = SezioneElettorale
        fields = [
            'id', 'numero', 'comune', 'municipio',
            'indirizzo', 'denominazione', 'n_elettori', 'is_attiva',
            'latitudine', 'longitudine'
        ]
