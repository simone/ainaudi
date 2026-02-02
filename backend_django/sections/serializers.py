"""
Serializers for sections models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import SectionAssignment, DatiSezione, DatiScheda, SectionDataHistory


class SectionAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for SectionAssignment model."""
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_indirizzo = serializers.CharField(source='sezione.indirizzo', read_only=True)
    rdl_email = serializers.EmailField(source='rdl_registration.email', read_only=True)
    rdl_nome = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)

    class Meta:
        model = SectionAssignment
        fields = [
            'id', 'sezione', 'sezione_numero', 'sezione_comune', 'sezione_indirizzo',
            'consultazione', 'rdl_registration', 'rdl_email', 'rdl_nome',
            'role', 'role_display', 'assigned_by', 'assigned_by_email',
            'assigned_at', 'notes'
        ]
        read_only_fields = ['id', 'assigned_at', 'assigned_by']

    def get_rdl_nome(self, obj):
        if obj.rdl_registration:
            return f"{obj.rdl_registration.cognome} {obj.rdl_registration.nome}"
        return None


class SectionAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SectionAssignment."""

    class Meta:
        model = SectionAssignment
        fields = ['sezione', 'consultazione', 'rdl_registration', 'role', 'notes']

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        # Set user from rdl_registration
        if validated_data.get('rdl_registration') and validated_data['rdl_registration'].user:
            validated_data['user'] = validated_data['rdl_registration'].user
        return super().create(validated_data)


class DatiSchedaSerializer(serializers.ModelSerializer):
    """Serializer for DatiScheda model."""
    scheda_nome = serializers.CharField(source='scheda.nome', read_only=True)
    scheda_colore = serializers.CharField(source='scheda.colore', read_only=True)
    totale_voti_validi = serializers.IntegerField(read_only=True)

    class Meta:
        model = DatiScheda
        fields = [
            'id', 'scheda', 'scheda_nome', 'scheda_colore',
            'schede_ricevute', 'schede_autenticate',
            'schede_bianche', 'schede_nulle', 'schede_contestate',
            'voti', 'totale_voti_validi',
            'is_valid', 'errori_validazione',
            'inserito_at', 'aggiornato_at'
        ]
        read_only_fields = ['id', 'is_valid', 'errori_validazione', 'aggiornato_at']


class DatiSchedaUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating DatiScheda."""

    class Meta:
        model = DatiScheda
        fields = [
            'schede_ricevute', 'schede_autenticate',
            'schede_bianche', 'schede_nulle', 'schede_contestate',
            'voti'
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.validate_data()
        instance.inserito_at = timezone.now()
        instance.save()
        return instance


class DatiSezioneSerializer(serializers.ModelSerializer):
    """Serializer for DatiSezione model."""
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_indirizzo = serializers.CharField(source='sezione.indirizzo', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    totale_elettori = serializers.IntegerField(read_only=True)
    totale_votanti = serializers.IntegerField(read_only=True)
    affluenza_percentuale = serializers.FloatField(read_only=True)
    schede = DatiSchedaSerializer(many=True, read_only=True)
    inserito_da_email = serializers.EmailField(source='inserito_da.email', read_only=True)
    verified_by_email = serializers.EmailField(source='verified_by.email', read_only=True)

    class Meta:
        model = DatiSezione
        fields = [
            'id', 'sezione', 'sezione_numero', 'sezione_comune', 'sezione_indirizzo',
            'consultazione', 'consultazione_nome',
            'elettori_maschi', 'elettori_femmine', 'totale_elettori',
            'votanti_maschi', 'votanti_femmine', 'totale_votanti',
            'affluenza_percentuale',
            'is_complete', 'is_verified', 'verified_by', 'verified_by_email', 'verified_at',
            'inserito_da', 'inserito_da_email', 'inserito_at', 'aggiornato_at',
            'schede'
        ]
        read_only_fields = [
            'id', 'totale_elettori', 'totale_votanti', 'affluenza_percentuale',
            'verified_by', 'verified_at', 'inserito_da', 'aggiornato_at'
        ]


class DatiSezioneUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating DatiSezione."""

    class Meta:
        model = DatiSezione
        fields = [
            'elettori_maschi', 'elettori_femmine',
            'votanti_maschi', 'votanti_femmine',
            'is_complete'
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.inserito_da = self.context['request'].user
        instance.inserito_at = timezone.now()
        instance.save()
        return instance


class DatiSezioneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists."""
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    affluenza_percentuale = serializers.FloatField(read_only=True)

    class Meta:
        model = DatiSezione
        fields = [
            'id', 'sezione', 'sezione_numero', 'sezione_comune',
            'affluenza_percentuale', 'is_complete', 'is_verified'
        ]


class SectionDataHistorySerializer(serializers.ModelSerializer):
    """Serializer for SectionDataHistory model."""
    modificato_da_email = serializers.EmailField(source='modificato_da.email', read_only=True)

    class Meta:
        model = SectionDataHistory
        fields = [
            'id', 'dati_sezione', 'dati_scheda', 'campo',
            'valore_precedente', 'valore_nuovo',
            'modificato_da', 'modificato_da_email', 'modificato_at', 'ip_address'
        ]
