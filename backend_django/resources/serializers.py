"""
Serializers for Resources (Documents and FAQ).
"""
from rest_framework import serializers
from .models import CategoriaDocumento, Documento, CategoriaFAQ, FAQ


class CategoriaDocumentoSerializer(serializers.ModelSerializer):
    n_documenti = serializers.SerializerMethodField()

    class Meta:
        model = CategoriaDocumento
        fields = ['id', 'nome', 'descrizione', 'icona', 'n_documenti']

    def get_n_documenti(self, obj):
        return getattr(obj, '_n_documenti', obj.documenti.filter(is_attivo=True).count())


class DocumentoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    categoria_icona = serializers.CharField(source='categoria.icona', read_only=True)
    dimensione_formattata = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = [
            'id', 'titolo', 'descrizione',
            'categoria', 'categoria_nome', 'categoria_icona',
            'file_url', 'url_esterno', 'download_url',
            'tipo_file', 'dimensione_formattata',
            'scope', 'in_evidenza', 'created_at'
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def get_download_url(self, obj):
        """Restituisce l'URL per scaricare/visualizzare il documento."""
        if obj.url_esterno:
            return obj.url_esterno
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class CategoriaFAQSerializer(serializers.ModelSerializer):
    n_faqs = serializers.SerializerMethodField()

    class Meta:
        model = CategoriaFAQ
        fields = ['id', 'nome', 'descrizione', 'icona', 'n_faqs']

    def get_n_faqs(self, obj):
        return getattr(obj, '_n_faqs', obj.faqs.filter(is_attivo=True).count())


class FAQSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    categoria_icona = serializers.CharField(source='categoria.icona', read_only=True)
    percentuale_utile = serializers.ReadOnlyField()

    class Meta:
        model = FAQ
        fields = [
            'id', 'domanda', 'risposta',
            'categoria', 'categoria_nome', 'categoria_icona',
            'scope', 'in_evidenza',
            'visualizzazioni', 'percentuale_utile',
            'created_at'
        ]


class FAQListSerializer(serializers.ModelSerializer):
    """Serializer leggero per lista FAQ (senza risposta completa)."""
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = FAQ
        fields = [
            'id', 'domanda', 'categoria', 'categoria_nome',
            'in_evidenza', 'visualizzazioni'
        ]
