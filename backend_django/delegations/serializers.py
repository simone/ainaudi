"""
Serializers for delegations models.

Gerarchia: PARTITO -> DELEGATO -> SUB-DELEGATO -> RDL
"""
from django.db import models
from rest_framework import serializers
from .models import Delegato, SubDelega, DesignazioneRDL, ProcessoDesignazione, BatchGenerazioneDocumenti
from campaign.models import CampagnaReclutamento, RdlRegistration


class DelegatoSerializer(serializers.ModelSerializer):
    """Serializer per Delegato."""
    carica_display = serializers.CharField(source='get_carica_display', read_only=True)
    nome_completo = serializers.CharField(read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    n_sub_deleghe = serializers.SerializerMethodField()
    territorio = serializers.SerializerMethodField()

    class Meta:
        model = Delegato
        fields = [
            'id', 'consultazione', 'consultazione_nome',
            'cognome', 'nome', 'nome_completo',
            'luogo_nascita', 'data_nascita',
            'carica', 'carica_display', 'circoscrizione',
            'data_nomina', 'email', 'telefono',
            'n_sub_deleghe', 'territorio'
        ]

    def get_n_sub_deleghe(self, obj):
        return obj.sub_deleghe.filter(is_attiva=True).count()

    def get_territorio(self, obj):
        """Restituisce descrizione testuale del territorio di competenza."""
        parti = []
        # Regioni
        regioni = list(obj.regioni.values_list('nome', flat=True))
        if regioni:
            parti.append(f"Regioni: {', '.join(regioni)}")
        # Province
        province = list(obj.province.values_list('nome', flat=True))
        if province:
            parti.append(f"Province: {', '.join(province)}")
        # Comuni
        comuni = list(obj.comuni.values_list('nome', flat=True))
        if comuni:
            parti.append(f"Comuni: {', '.join(comuni)}")
        # Municipi (Roma)
        if obj.municipi:
            mun_list = ', '.join(str(m) for m in obj.municipi)
            parti.append(f"Roma - Municipi: {mun_list}")
        return ' | '.join(parti) if parti else None


class SubDelegaSerializer(serializers.ModelSerializer):
    """Serializer per Sub-Delega."""
    nome_completo = serializers.CharField(read_only=True)
    delegato_nome = serializers.CharField(source='delegato.nome_completo', read_only=True)
    delegato_carica = serializers.CharField(source='delegato.get_carica_display', read_only=True)
    consultazione_id = serializers.IntegerField(source='consultazione.id', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    regioni_nomi = serializers.SerializerMethodField()
    province_nomi = serializers.SerializerMethodField()
    comuni_nomi = serializers.SerializerMethodField()
    territorio = serializers.SerializerMethodField()
    n_designazioni = serializers.SerializerMethodField()
    n_bozze = serializers.SerializerMethodField()
    catena_deleghe = serializers.SerializerMethodField()
    tipo_delega_display = serializers.CharField(source='get_tipo_delega_display', read_only=True)
    puo_designare_direttamente = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubDelega
        fields = [
            'id', 'delegato', 'delegato_nome', 'delegato_carica',
            'consultazione_id', 'consultazione_nome',
            'cognome', 'nome', 'nome_completo',
            'luogo_nascita', 'data_nascita', 'domicilio',
            'tipo_documento', 'numero_documento',
            'regioni', 'regioni_nomi', 'province', 'province_nomi',
            'comuni', 'comuni_nomi', 'municipi', 'territorio',
            'data_delega', 'firma_autenticata', 'autenticatore',
            'tipo_delega', 'tipo_delega_display', 'puo_designare_direttamente',
            'email', 'telefono',
            'is_attiva', 'n_designazioni', 'n_bozze',
            'catena_deleghe'
        ]
        read_only_fields = ['id', 'created_at']

    def get_regioni_nomi(self, obj):
        return list(obj.regioni.values_list('nome', flat=True))

    def get_province_nomi(self, obj):
        return list(obj.province.values_list('nome', flat=True))

    def get_comuni_nomi(self, obj):
        return list(obj.comuni.values_list('nome', flat=True))

    def get_territorio(self, obj):
        """Restituisce descrizione testuale del territorio completo."""
        parti = []
        # Regioni
        regioni = list(obj.regioni.values_list('nome', flat=True))
        if regioni:
            parti.append(f"Regioni: {', '.join(regioni)}")
        # Province
        province = list(obj.province.values_list('nome', flat=True))
        if province:
            parti.append(f"Province: {', '.join(province)}")
        # Comuni
        comuni = list(obj.comuni.values_list('nome', flat=True))
        if comuni:
            parti.append(f"Comuni: {', '.join(comuni)}")
        # Municipi (Roma)
        if obj.municipi:
            mun_list = ', '.join(str(m) for m in obj.municipi)
            parti.append(f"Roma - Municipi: {mun_list}")
        return ' | '.join(parti) if parti else None

    def get_n_designazioni(self, obj):
        return obj.designazioni_rdl.filter(is_attiva=True, stato='CONFERMATA').count()

    def get_n_bozze(self, obj):
        return obj.designazioni_rdl.filter(is_attiva=True, stato='BOZZA').count()

    def get_catena_deleghe(self, obj):
        return obj.get_catena_deleghe()


class SubDelegaCreateSerializer(serializers.ModelSerializer):
    """Serializer per creare una Sub-Delega."""

    class Meta:
        model = SubDelega
        fields = [
            'delegato',
            'cognome', 'nome', 'luogo_nascita', 'data_nascita', 'domicilio',
            'tipo_documento', 'numero_documento',
            'regioni', 'province', 'comuni', 'municipi',
            'data_delega', 'firma_autenticata', 'data_autenticazione', 'autenticatore',
            'email', 'telefono'
        ]

    def create(self, validated_data):
        validated_data['created_by_email'] = self.context['request'].user.email
        return super().create(validated_data)


class DesignazioneRDLSerializer(serializers.ModelSerializer):
    """Serializer per Designazione RDL (snapshot fields: campi diretti)."""
    # Nested serializers per RDL (costruiti dai campi diretti)
    effettivo = serializers.SerializerMethodField()
    supplente = serializers.SerializerMethodField()

    # Sezione info
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_indirizzo = serializers.CharField(source='sezione.indirizzo', read_only=True)
    sezione_municipio = serializers.SerializerMethodField()

    # Designante
    designante_nome = serializers.CharField(read_only=True)
    delegato_nome = serializers.SerializerMethodField()
    sub_delegato_nome = serializers.SerializerMethodField()

    # Stato
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    is_bozza = serializers.BooleanField(read_only=True)

    # Approvazione
    approvata_da_nome = serializers.CharField(source='approvata_da.get_full_name', read_only=True, allow_null=True)

    # Catena deleghe
    catena_deleghe = serializers.SerializerMethodField()

    class Meta:
        model = DesignazioneRDL
        fields = [
            'id', 'delegato', 'delegato_nome', 'sub_delega', 'sub_delegato_nome',
            'designante_nome',
            'sezione', 'sezione_numero', 'sezione_comune', 'sezione_indirizzo', 'sezione_municipio',
            'effettivo', 'supplente',
            'stato', 'stato_display', 'is_bozza',
            'data_designazione', 'is_attiva',
            'approvata_da_email', 'approvata_da_nome', 'data_approvazione',
            'processo',
            'catena_deleghe'
        ]
        read_only_fields = ['id', 'data_designazione', 'created_at', 'data_approvazione']

    def get_effettivo(self, obj):
        if not obj.effettivo_email:
            return None
        return {
            'cognome': obj.effettivo_cognome,
            'nome': obj.effettivo_nome,
            'email': obj.effettivo_email,
            'telefono': obj.effettivo_telefono or '',
        }

    def get_supplente(self, obj):
        if not obj.supplente_email:
            return None
        return {
            'cognome': obj.supplente_cognome,
            'nome': obj.supplente_nome,
            'email': obj.supplente_email,
            'telefono': obj.supplente_telefono or '',
        }

    def get_sezione_municipio(self, obj):
        if obj.sezione and obj.sezione.municipio:
            return obj.sezione.municipio.numero
        return None

    def get_delegato_nome(self, obj):
        if obj.delegato:
            return obj.delegato.nome_completo
        return None

    def get_sub_delegato_nome(self, obj):
        if obj.sub_delega:
            return obj.sub_delega.nome_completo
        return None

    def get_catena_deleghe(self, obj):
        return obj.get_catena_deleghe_completa()


class DesignazioneRDLCreateSerializer(serializers.ModelSerializer):
    """Serializer per creare una Designazione RDL con snapshot dei dati."""
    # Input: email per lookup RdlRegistration
    effettivo_email_input = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    supplente_email_input = serializers.EmailField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = DesignazioneRDL
        fields = [
            'delegato', 'sub_delega', 'sezione',
            'effettivo_email_input', 'supplente_email_input',
            'stato'
        ]

    def validate(self, data):
        """Verifica che almeno uno tra delegato e sub_delega sia valorizzato."""
        if not data.get('delegato') and not data.get('sub_delega'):
            raise serializers.ValidationError(
                "Deve essere specificato almeno uno tra 'delegato' e 'sub_delega'"
            )

        # Almeno uno tra effettivo e supplente
        if not data.get('effettivo_email_input') and not data.get('supplente_email_input'):
            raise serializers.ValidationError(
                'Specificare almeno un RDL (effettivo o supplente)'
            )

        return data

    def create(self, validated_data):
        from campaign.models import RdlRegistration

        # Estrai email input
        effettivo_email = validated_data.pop('effettivo_email_input', None)
        supplente_email = validated_data.pop('supplente_email_input', None)

        # Prepara campi designazione
        designazione_data = validated_data.copy()

        # Lookup e copia dati effettivo
        if effettivo_email:
            effettivo = RdlRegistration.objects.filter(
                email=effettivo_email, status='APPROVED'
            ).first()
            if not effettivo:
                raise serializers.ValidationError(
                    f'RDL effettivo {effettivo_email} non trovato o non approvato'
                )

            # Copia snapshot dei dati
            designazione_data['effettivo_cognome'] = effettivo.cognome
            designazione_data['effettivo_nome'] = effettivo.nome
            designazione_data['effettivo_email'] = effettivo.email
            designazione_data['effettivo_telefono'] = effettivo.telefono or ''
            designazione_data['effettivo_luogo_nascita'] = effettivo.comune_nascita or ''
            designazione_data['effettivo_data_nascita'] = effettivo.data_nascita
            designazione_data['effettivo_domicilio'] = f"{effettivo.indirizzo_residenza}, {effettivo.comune_residenza}"

        # Lookup e copia dati supplente
        if supplente_email:
            supplente = RdlRegistration.objects.filter(
                email=supplente_email, status='APPROVED'
            ).first()
            if not supplente:
                raise serializers.ValidationError(
                    f'RDL supplente {supplente_email} non trovato o non approvato'
                )

            # Copia snapshot dei dati
            designazione_data['supplente_cognome'] = supplente.cognome
            designazione_data['supplente_nome'] = supplente.nome
            designazione_data['supplente_email'] = supplente.email
            designazione_data['supplente_telefono'] = supplente.telefono or ''
            designazione_data['supplente_luogo_nascita'] = supplente.comune_nascita or ''
            designazione_data['supplente_data_nascita'] = supplente.data_nascita
            designazione_data['supplente_domicilio'] = f"{supplente.indirizzo_residenza}, {supplente.comune_residenza}"

        # Crea designazione con snapshot
        designazione = DesignazioneRDL.objects.create(**designazione_data)

        return designazione


class DesignazioneRDLListSerializer(serializers.ModelSerializer):
    """Serializer leggero per lista designazioni (snapshot fields)."""
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    designante_nome = serializers.CharField(read_only=True)
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_indirizzo = serializers.CharField(source='sezione.indirizzo', read_only=True)
    sezione_municipio = serializers.SerializerMethodField()

    # Nested RDL info
    effettivo = serializers.SerializerMethodField()
    supplente = serializers.SerializerMethodField()

    class Meta:
        model = DesignazioneRDL
        fields = [
            'id', 'sezione', 'sezione_numero', 'sezione_comune', 'sezione_indirizzo', 'sezione_municipio',
            'effettivo', 'supplente',
            'stato', 'stato_display', 'designante_nome',
            'is_attiva', 'processo'
        ]

    def get_sezione_municipio(self, obj):
        if obj.sezione and obj.sezione.municipio:
            return obj.sezione.municipio.numero
        return None

    def get_effettivo(self, obj):
        if not obj.effettivo_email:
            return None
        return {
            'cognome': obj.effettivo_cognome,
            'nome': obj.effettivo_nome,
            'email': obj.effettivo_email,
            'telefono': obj.effettivo_telefono or '',
            'data_nascita': obj.effettivo_data_nascita.strftime('%d/%m/%Y') if obj.effettivo_data_nascita else '',
            'luogo_nascita': obj.effettivo_luogo_nascita or '',
            'domicilio': obj.effettivo_domicilio or ''
        }

    def get_supplente(self, obj):
        if not obj.supplente_email:
            return None
        return {
            'cognome': obj.supplente_cognome,
            'nome': obj.supplente_nome,
            'email': obj.supplente_email,
            'telefono': obj.supplente_telefono or '',
            'data_nascita': obj.supplente_data_nascita.strftime('%d/%m/%Y') if obj.supplente_data_nascita else '',
            'luogo_nascita': obj.supplente_luogo_nascita or '',
            'domicilio': obj.supplente_domicilio or ''
        }


class ProcessoDesignazioneSerializer(serializers.ModelSerializer):
    """Serializer per Processo Designazione RDL."""
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    delegato_nome = serializers.SerializerMethodField()
    template_individuale_nome = serializers.CharField(source='template_individuale.name', read_only=True)
    template_cumulativo_nome = serializers.CharField(source='template_cumulativo.name', read_only=True)
    email_gia_inviate = serializers.SerializerMethodField()

    class Meta:
        model = ProcessoDesignazione
        fields = [
            'id', 'consultazione', 'consultazione_nome',
            'delegato', 'delegato_nome',
            'template_individuale', 'template_individuale_nome',
            'template_cumulativo', 'template_cumulativo_nome',
            'dati_delegato', 'stato', 'stato_display',
            'documento_individuale', 'documento_cumulativo',
            'data_generazione_individuale', 'data_generazione_cumulativo',
            'n_designazioni', 'n_pagine',
            'created_at', 'created_by_email',
            'approvata_at', 'approvata_da_email',
            'email_inviate_at', 'email_inviate_da',
            'n_email_inviate', 'n_email_fallite', 'email_gia_inviate'
        ]
        read_only_fields = [
            'id', 'stato', 'documento_individuale', 'documento_cumulativo',
            'data_generazione_individuale', 'data_generazione_cumulativo',
            'n_designazioni', 'n_pagine', 'created_at', 'created_by_email',
            'approvata_at', 'approvata_da_email',
            'email_inviate_at', 'email_inviate_da', 'n_email_inviate', 'n_email_fallite'
        ]

    def get_delegato_nome(self, obj):
        if obj.delegato:
            return obj.delegato.nome_completo
        return None

    def get_email_gia_inviate(self, obj):
        """Flag per disabilitare bottone invio email se già inviate."""
        return obj.email_inviate_at is not None


# Serializer per vecchio endpoint /batch/ (retrocompatibilità)
class BatchGenerazioneDocumentiSerializer(serializers.ModelSerializer):
    """Serializer per vecchio endpoint batch (con campo tipo per retrocompatibilità)."""
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = ProcessoDesignazione
        fields = [
            'id', 'consultazione', 'consultazione_nome',
            'tipo', 'tipo_display',
            'stato', 'stato_display',
            'n_designazioni', 'n_pagine',
            'created_at', 'created_by_email',
            'approvata_at', 'approvata_da_email'
        ]
        read_only_fields = [
            'id', 'tipo_display', 'stato',
            'n_designazioni', 'n_pagine', 'created_at', 'created_by_email',
            'approvata_at', 'approvata_da_email'
        ]


class AvviaProcessoSerializer(serializers.Serializer):
    """Serializer per avviare un nuovo processo di designazione."""
    consultazione_id = serializers.IntegerField()
    sezione_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista ID sezioni da includere nel processo"
    )


class ConfiguraProcessoSerializer(serializers.Serializer):
    """Serializer per configurare template e dati delegato."""
    template_individuale_id = serializers.IntegerField()
    template_cumulativo_id = serializers.IntegerField()
    delegato_id = serializers.IntegerField(required=False, allow_null=True)
    subdelegato_id = serializers.IntegerField(required=False, allow_null=True)
    dati_delegato = serializers.JSONField(
        help_text="Dati delegato compilati (snapshot per PDF)"
    )


class TemplateChoiceSerializer(serializers.Serializer):
    """Serializer per scelte template disponibili."""
    id = serializers.IntegerField()
    nome = serializers.CharField()
    tipo = serializers.CharField()
    variabili = serializers.ListField(child=serializers.CharField())


class CampiRichiestiSerializer(serializers.Serializer):
    """Schema campi richiesti per compilare dati delegato."""
    field_name = serializers.CharField()
    field_type = serializers.CharField()
    label = serializers.CharField()
    required = serializers.BooleanField()
    current_value = serializers.CharField(allow_null=True, allow_blank=True)


# =============================================================================
# Serializers per la vista "Mia Catena Deleghe"
# =============================================================================

class MiaCatenaSerializer(serializers.Serializer):
    """Serializer per la catena deleghe dell'utente loggato."""
    is_delegato = serializers.BooleanField()
    is_sub_delegato = serializers.BooleanField()
    is_rdl = serializers.BooleanField()
    deleghe_lista = DelegatoSerializer(many=True)
    sub_deleghe_ricevute = SubDelegaSerializer(many=True)
    sub_deleghe_fatte = SubDelegaSerializer(many=True)
    designazioni_fatte = DesignazioneRDLListSerializer(many=True)
    designazioni_ricevute = DesignazioneRDLSerializer(many=True)


class SezioneDisponibileSerializer(serializers.Serializer):
    """Serializer per sezioni disponibili per designazione."""
    id = serializers.IntegerField()
    numero = serializers.IntegerField()
    comune_nome = serializers.CharField()
    municipio = serializers.IntegerField(allow_null=True)
    indirizzo = serializers.CharField(allow_blank=True)
    ha_effettivo = serializers.BooleanField()
    ha_supplente = serializers.BooleanField()


class RdlRegistrationForMappatura(serializers.Serializer):
    """Serializer per RdlRegistration nella vista mappatura."""
    id = serializers.IntegerField()
    nome = serializers.CharField()
    cognome = serializers.CharField()
    email = serializers.EmailField()
    telefono = serializers.CharField()
    comune_nascita = serializers.CharField()
    data_nascita = serializers.DateField()
    comune_residenza = serializers.CharField()
    indirizzo_residenza = serializers.CharField()
    comune_id = serializers.IntegerField(source='comune.id')
    comune_nome = serializers.CharField(source='comune.nome')
    municipio_id = serializers.IntegerField(source='municipio.id', allow_null=True)
    municipio_nome = serializers.CharField(source='municipio.nome', allow_null=True)
    seggio_preferenza = serializers.CharField(allow_blank=True)
    # Stato designazioni
    designazione_effettivo_id = serializers.IntegerField(allow_null=True)
    designazione_supplente_id = serializers.IntegerField(allow_null=True)


# MappaturaCreaSerializer removed - logic moved to carica_mappatura view


class ConfermaDesignazioneSerializer(serializers.Serializer):
    """Serializer per confermare una designazione in stato BOZZA."""
    pass  # Non richiede parametri, l'ID è nell'URL


class RifiutaDesignazioneSerializer(serializers.Serializer):
    """Serializer per rifiutare una designazione in stato BOZZA."""
    motivo = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# Serializers per Campagna di Reclutamento
# =============================================================================

class CampagnaReclutamentoSerializer(serializers.ModelSerializer):
    """Serializer per Campagna di Reclutamento (lettura completa)."""
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    delegato_nome = serializers.SerializerMethodField()
    sub_delegato_nome = serializers.SerializerMethodField()
    created_by_nome = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    territorio = serializers.SerializerMethodField()
    is_aperta = serializers.BooleanField(read_only=True)
    n_registrazioni = serializers.IntegerField(read_only=True)
    posti_disponibili = serializers.IntegerField(read_only=True)

    class Meta:
        model = CampagnaReclutamento
        fields = [
            'id', 'consultazione', 'consultazione_nome',
            'nome', 'slug', 'descrizione',
            'data_apertura', 'data_chiusura',
            'territorio_regioni', 'territorio_province', 'territorio_comuni',
            'territorio',
            'stato', 'stato_display',
            'delegato', 'delegato_nome', 'sub_delega', 'sub_delegato_nome',
            'created_by_nome',
            'richiedi_approvazione', 'max_registrazioni', 'messaggio_conferma',
            'is_aperta', 'n_registrazioni', 'posti_disponibili',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by_nome']

    def get_delegato_nome(self, obj):
        if obj.delegato:
            return obj.delegato.nome_completo
        return None

    def get_sub_delegato_nome(self, obj):
        if obj.sub_delega:
            return obj.sub_delega.nome_completo
        return None

    def get_territorio(self, obj):
        """Restituisce descrizione testuale del territorio."""
        parti = []
        regioni = list(obj.territorio_regioni.values_list('nome', flat=True))
        if regioni:
            parti.append(f"Regioni: {', '.join(regioni)}")
        province = list(obj.territorio_province.values_list('nome', flat=True))
        if province:
            parti.append(f"Province: {', '.join(province)}")
        comuni = list(obj.territorio_comuni.values_list('nome', flat=True))
        if comuni:
            parti.append(f"Comuni: {', '.join(comuni)}")
        return ' | '.join(parti) if parti else 'Tutto il territorio'


class CampagnaReclutamentoCreateSerializer(serializers.ModelSerializer):
    """Serializer per creare/aggiornare una Campagna di Reclutamento."""

    class Meta:
        model = CampagnaReclutamento
        fields = [
            'consultazione', 'nome', 'slug', 'descrizione',
            'data_apertura', 'data_chiusura',
            'territorio_regioni', 'territorio_province', 'territorio_comuni',
            'stato', 'delegato', 'sub_delega',
            'richiedi_approvazione', 'max_registrazioni', 'messaggio_conferma'
        ]

    def create(self, validated_data):
        validated_data['created_by_email'] = self.context['request'].user.email
        return super().create(validated_data)


class CampagnaReclutamentoPublicSerializer(serializers.ModelSerializer):
    """Serializer pubblico per Campagna (info limitate per pagina registrazione)."""
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    consultazione_tipi_elezione = serializers.SerializerMethodField()
    is_aperta = serializers.BooleanField(read_only=True)
    posti_disponibili = serializers.IntegerField(read_only=True)
    comuni_disponibili = serializers.SerializerMethodField()

    class Meta:
        model = CampagnaReclutamento
        fields = [
            'nome', 'slug', 'descrizione',
            'consultazione_nome', 'consultazione_tipi_elezione',
            'data_apertura', 'data_chiusura',
            'is_aperta', 'posti_disponibili',
            'richiedi_approvazione', 'messaggio_conferma',
            'comuni_disponibili'
        ]

    def get_consultazione_tipi_elezione(self, obj):
        """Restituisce i tipi di elezione della consultazione."""
        return list(obj.consultazione.tipi_elezione.values_list('tipo', flat=True).distinct())

    def get_comuni_disponibili(self, obj):
        """Restituisce lista semplificata dei comuni disponibili."""
        comuni = obj.get_comuni_disponibili()
        return [
            {
                'id': c.id,
                'nome': c.nome,
                'label': str(c),
                'has_municipi': c.municipi.exists(),
                'municipi': [
                    {'numero': m.numero, 'nome': m.nome}
                    for m in c.municipi.all().order_by('numero')
                ] if c.municipi.exists() else []
            }
            for c in comuni.prefetch_related('municipi')[:500]  # Limit for performance
        ]


class CampagnaRegistrazioneSerializer(serializers.Serializer):
    """Serializer per registrazione RDL via campagna."""
    email = serializers.EmailField()
    nome = serializers.CharField(max_length=100)
    cognome = serializers.CharField(max_length=100)
    telefono = serializers.CharField(max_length=20)
    comune_nascita = serializers.CharField(max_length=100)
    data_nascita = serializers.DateField()
    comune_residenza = serializers.CharField(max_length=100)
    indirizzo_residenza = serializers.CharField(max_length=255)
    # Fuorisede info
    fuorisede = serializers.BooleanField(required=False, allow_null=True)
    comune_domicilio = serializers.CharField(max_length=100, required=False, allow_blank=True)
    indirizzo_domicilio = serializers.CharField(max_length=255, required=False, allow_blank=True)
    seggio_preferenza = serializers.CharField(max_length=255, required=False, allow_blank=True)
    comune_id = serializers.IntegerField()
    municipio = serializers.IntegerField(required=False, allow_null=True)

    def validate_comune_id(self, value):
        from territory.models import Comune
        try:
            Comune.objects.get(id=value)
        except Comune.DoesNotExist:
            raise serializers.ValidationError("Comune non trovato")
        return value

    def validate(self, data):
        campagna = self.context.get('campagna')
        if not campagna:
            raise serializers.ValidationError("Campagna non specificata")

        if not campagna.is_aperta:
            raise serializers.ValidationError("La campagna non è aperta")

        if campagna.posti_disponibili is not None and campagna.posti_disponibili <= 0:
            raise serializers.ValidationError("Posti esauriti")

        # Verify comune is within campaign territory
        from territory.models import Comune
        comune = Comune.objects.get(id=data['comune_id'])
        comuni_disponibili = campagna.get_comuni_disponibili()
        if not comuni_disponibili.filter(id=comune.id).exists():
            raise serializers.ValidationError({
                'comune_id': 'Il comune selezionato non è disponibile per questa campagna'
            })

        return data

    def create(self, validated_data):
        from territory.models import Comune, Municipio

        campagna = self.context['campagna']
        comune = Comune.objects.get(id=validated_data['comune_id'])

        municipio = None
        if validated_data.get('municipio'):
            municipio = Municipio.objects.filter(
                comune=comune,
                numero=validated_data['municipio']
            ).first()

        # Determine initial status
        status = (
            RdlRegistration.Status.PENDING
            if campagna.richiedi_approvazione
            else RdlRegistration.Status.APPROVED
        )

        registration = RdlRegistration.objects.create(
            email=validated_data['email'].lower().strip(),
            nome=validated_data['nome'].strip(),
            cognome=validated_data['cognome'].strip(),
            telefono=validated_data['telefono'].strip(),
            comune_nascita=validated_data['comune_nascita'].strip(),
            data_nascita=validated_data['data_nascita'],
            comune_residenza=validated_data['comune_residenza'].strip(),
            indirizzo_residenza=validated_data['indirizzo_residenza'].strip(),
            fuorisede=validated_data.get('fuorisede'),
            comune_domicilio=validated_data.get('comune_domicilio', '').strip(),
            indirizzo_domicilio=validated_data.get('indirizzo_domicilio', '').strip(),
            seggio_preferenza=validated_data.get('seggio_preferenza', '').strip(),
            comune=comune,
            municipio=municipio,
            status=status,
            source='CAMPAGNA',
            campagna=campagna,
            consultazione=campagna.consultazione
        )

        return registration
