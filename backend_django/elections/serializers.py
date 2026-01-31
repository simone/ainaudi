"""
Serializers for elections models.
Territory serializers are in territorio/serializers.py.
"""
from rest_framework import serializers
from territorio.models import Regione
from territorio.serializers import RegioneSerializer
from .models import (
    CircoscrizioneCamera, CircoscrizioneSenato, CircoscrizioneEuropee,
    ConsultazioneElettorale, TipoElezione, SchedaElettorale,
    ListaElettorale, Candidato,
)


# =============================================================================
# CIRCUMSCRIPTIONS SERIALIZERS
# =============================================================================

class CircoscrizioneCameraSerializer(serializers.ModelSerializer):
    regioni = RegioneSerializer(many=True, read_only=True)

    class Meta:
        model = CircoscrizioneCamera
        fields = ['id', 'numero', 'nome', 'regioni']


class CircoscrizioneSenatoSerializer(serializers.ModelSerializer):
    regione = RegioneSerializer(read_only=True)

    class Meta:
        model = CircoscrizioneSenato
        fields = ['id', 'regione']


class CircoscrizioneEuropeeSerializer(serializers.ModelSerializer):
    codice_display = serializers.CharField(source='get_codice_display', read_only=True)
    regioni = RegioneSerializer(many=True, read_only=True)

    class Meta:
        model = CircoscrizioneEuropee
        fields = ['id', 'codice', 'codice_display', 'regioni']


# =============================================================================
# ELECTIONS SERIALIZERS
# =============================================================================

class ConsultazioneElettoraleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultazioneElettorale
        fields = ['id', 'nome', 'data_inizio', 'data_fine', 'is_attiva', 'descrizione']


class TipoElezioneSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    regione_nome = serializers.CharField(source='regione.nome', read_only=True)

    class Meta:
        model = TipoElezione
        fields = [
            'id', 'tipo', 'tipo_display', 'consultazione', 'consultazione_nome',
            'ambito_nazionale', 'regione', 'regione_nome'
        ]


class SchedaElettoraleSerializer(serializers.ModelSerializer):
    tipo_elezione_display = serializers.CharField(source='tipo_elezione.get_tipo_display', read_only=True)

    class Meta:
        model = SchedaElettorale
        fields = [
            'id', 'tipo_elezione', 'tipo_elezione_display',
            'nome', 'colore', 'ordine', 'testo_quesito', 'schema_voti'
        ]


class CandidatoSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Candidato
        fields = [
            'id', 'nome', 'cognome', 'nome_completo',
            'data_nascita', 'luogo_nascita',
            'lista', 'scheda', 'posizione_lista',
            'collegio_uninominale', 'is_sindaco', 'is_presidente'
        ]


class CandidatoListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for candidate lists."""
    class Meta:
        model = Candidato
        fields = ['id', 'cognome', 'nome', 'posizione_lista']


class ListaElettoraleSerializer(serializers.ModelSerializer):
    candidati = CandidatoListSerializer(many=True, read_only=True)

    class Meta:
        model = ListaElettorale
        fields = [
            'id', 'nome', 'nome_breve', 'scheda',
            'ordine_scheda', 'coalizione', 'candidati'
        ]


class ListaElettoraleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists."""
    class Meta:
        model = ListaElettorale
        fields = ['id', 'nome', 'nome_breve', 'ordine_scheda']


# =============================================================================
# NESTED SERIALIZERS (for complete views)
# =============================================================================

class TipoElezioneDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including ballots and lists."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    schede = SchedaElettoraleSerializer(many=True, read_only=True)

    class Meta:
        model = TipoElezione
        fields = [
            'id', 'tipo', 'tipo_display',
            'ambito_nazionale', 'regione', 'schede'
        ]


class ConsultazioneElettoraleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including election types."""
    tipi_elezione = TipoElezioneDetailSerializer(many=True, read_only=True)

    class Meta:
        model = ConsultazioneElettorale
        fields = [
            'id', 'nome', 'data_inizio', 'data_fine',
            'is_attiva', 'descrizione', 'tipi_elezione'
        ]


class SchedaElettoraleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including lists and candidates."""
    liste = ListaElettoraleSerializer(many=True, read_only=True)
    candidati_uninominali = CandidatoSerializer(many=True, read_only=True)

    class Meta:
        model = SchedaElettorale
        fields = [
            'id', 'tipo_elezione', 'nome', 'colore', 'ordine',
            'testo_quesito', 'schema_voti', 'liste', 'candidati_uninominali'
        ]
