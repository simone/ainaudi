"""
Serializers for territorio models.
"""
from rest_framework import serializers
from .models import Regione, Provincia, Comune, Municipio, SezioneElettorale


# ==============================================================================
# READ SERIALIZERS (for listing and detail views)
# ==============================================================================

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
    n_municipi = serializers.SerializerMethodField()

    class Meta:
        model = Comune
        fields = [
            'id', 'codice_istat', 'codice_catastale', 'nome',
            'provincia', 'provincia_sigla', 'provincia_nome', 'regione_nome',
            'sopra_15000_abitanti', 'sistema_elettorale_comunali', 'n_municipi'
        ]

    def get_n_municipi(self, obj):
        return obj.municipi.count()


class ComuneSerializer(serializers.ModelSerializer):
    provincia = ProvinciaSerializer(read_only=True)
    municipi = MunicipioSerializer(many=True, read_only=True)

    class Meta:
        model = Comune
        fields = [
            'id', 'codice_istat', 'codice_catastale', 'nome',
            'provincia', 'sopra_15000_abitanti',
            'sistema_elettorale_comunali', 'municipi'
        ]


class SezioneElettoraleListSerializer(serializers.ModelSerializer):
    comune_nome = serializers.CharField(source='comune.nome', read_only=True)
    provincia_sigla = serializers.CharField(source='comune.provincia.sigla', read_only=True)
    municipio_numero = serializers.IntegerField(source='municipio.numero', read_only=True, allow_null=True)

    class Meta:
        model = SezioneElettorale
        fields = [
            'id', 'numero', 'comune', 'comune_nome', 'provincia_sigla',
            'municipio', 'municipio_numero', 'indirizzo', 'denominazione', 'n_elettori', 'is_attiva'
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


# ==============================================================================
# WRITE SERIALIZERS (for create/update operations)
# ==============================================================================

class RegioneWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Regione."""
    class Meta:
        model = Regione
        fields = ['id', 'codice_istat', 'nome', 'statuto_speciale']


class ProvinciaWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Provincia."""
    regione = serializers.PrimaryKeyRelatedField(queryset=Regione.objects.all())

    class Meta:
        model = Provincia
        fields = ['id', 'regione', 'codice_istat', 'sigla', 'nome', 'is_citta_metropolitana']


class ComuneWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Comune."""
    provincia = serializers.PrimaryKeyRelatedField(queryset=Provincia.objects.all())

    class Meta:
        model = Comune
        fields = ['id', 'provincia', 'codice_istat', 'codice_catastale', 'nome', 'sopra_15000_abitanti']


class MunicipioWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Municipio."""
    comune = serializers.PrimaryKeyRelatedField(queryset=Comune.objects.all())

    class Meta:
        model = Municipio
        fields = ['id', 'comune', 'numero', 'nome']


class MunicipioListSerializer(serializers.ModelSerializer):
    """Serializer for listing Municipio with comune details."""
    comune_nome = serializers.CharField(source='comune.nome', read_only=True)
    comune_codice_istat = serializers.CharField(source='comune.codice_istat', read_only=True)
    provincia_sigla = serializers.CharField(source='comune.provincia.sigla', read_only=True)

    class Meta:
        model = Municipio
        fields = ['id', 'numero', 'nome', 'comune', 'comune_nome', 'comune_codice_istat', 'provincia_sigla']


class SezioneElettoraleWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating SezioneElettorale."""
    comune = serializers.PrimaryKeyRelatedField(queryset=Comune.objects.all())
    municipio = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = SezioneElettorale
        fields = [
            'id', 'comune', 'municipio', 'numero',
            'indirizzo', 'denominazione', 'n_elettori', 'is_attiva',
            'latitudine', 'longitudine'
        ]

    def validate(self, data):
        """Validate that municipio belongs to the specified comune."""
        municipio = data.get('municipio')
        comune = data.get('comune')

        if municipio and comune and municipio.comune_id != comune.id:
            raise serializers.ValidationError({
                'municipio': 'Il municipio deve appartenere al comune selezionato.'
            })

        return data
