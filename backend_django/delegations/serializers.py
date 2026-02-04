"""
Serializers for delegations models.

Gerarchia: PARTITO -> DELEGATO DI LISTA -> SUB-DELEGATO -> RDL
"""
from django.db import models
from rest_framework import serializers
from .models import DelegatoDiLista, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti
from campaign.models import CampagnaReclutamento, RdlRegistration


class DelegatoDiListaSerializer(serializers.ModelSerializer):
    """Serializer per Delegato di Lista."""
    carica_display = serializers.CharField(source='get_carica_display', read_only=True)
    nome_completo = serializers.CharField(read_only=True)
    consultazione_nome = serializers.CharField(source='consultazione.nome', read_only=True)
    n_sub_deleghe = serializers.SerializerMethodField()
    territorio = serializers.SerializerMethodField()

    class Meta:
        model = DelegatoDiLista
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
        regioni = list(obj.territorio_regioni.values_list('nome', flat=True))
        if regioni:
            parti.append(f"Regioni: {', '.join(regioni)}")
        # Province
        province = list(obj.territorio_province.values_list('nome', flat=True))
        if province:
            parti.append(f"Province: {', '.join(province)}")
        # Comuni
        comuni = list(obj.territorio_comuni.values_list('nome', flat=True))
        if comuni:
            parti.append(f"Comuni: {', '.join(comuni)}")
        # Municipi (Roma)
        if obj.territorio_municipi:
            mun_list = ', '.join(str(m) for m in obj.territorio_municipi)
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
    """Serializer per Designazione RDL."""
    nome_completo = serializers.CharField(read_only=True)
    ruolo_display = serializers.CharField(source='get_ruolo_display', read_only=True)
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    designante_nome = serializers.CharField(read_only=True)
    delegato_nome = serializers.SerializerMethodField()
    sub_delegato_nome = serializers.SerializerMethodField()
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_indirizzo = serializers.CharField(source='sezione.indirizzo', read_only=True)
    sezione_municipio = serializers.SerializerMethodField()
    catena_deleghe = serializers.SerializerMethodField()
    is_bozza = serializers.BooleanField(read_only=True)
    approvata_da_nome = serializers.CharField(source='approvata_da.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = DesignazioneRDL
        fields = [
            'id', 'delegato', 'delegato_nome', 'sub_delega', 'sub_delegato_nome',
            'designante_nome',
            'sezione', 'sezione_numero', 'sezione_comune', 'sezione_indirizzo', 'sezione_municipio',
            'ruolo', 'ruolo_display',
            'stato', 'stato_display', 'is_bozza',
            'cognome', 'nome', 'nome_completo',
            'luogo_nascita', 'data_nascita', 'domicilio',
            'email', 'telefono',
            'documento_designazione', 'data_generazione_documento',
            'data_designazione', 'is_attiva',
            'approvata_da', 'approvata_da_nome', 'data_approvazione',
            'catena_deleghe'
        ]
        read_only_fields = ['id', 'data_designazione', 'created_at', 'approvata_da', 'data_approvazione']

    def get_delegato_nome(self, obj):
        if obj.delegato:
            return obj.delegato.nome_completo
        return None

    def get_sub_delegato_nome(self, obj):
        if obj.sub_delega:
            return obj.sub_delega.nome_completo
        return None

    def get_sezione_municipio(self, obj):
        if obj.sezione and obj.sezione.municipio:
            return obj.sezione.municipio.numero
        return None

    def get_catena_deleghe(self, obj):
        return obj.get_catena_deleghe_completa()


class DesignazioneRDLCreateSerializer(serializers.ModelSerializer):
    """Serializer per creare una Designazione RDL."""

    class Meta:
        model = DesignazioneRDL
        fields = [
            'delegato', 'sub_delega', 'sezione', 'ruolo',
            'cognome', 'nome', 'luogo_nascita', 'data_nascita', 'domicilio',
            'email', 'telefono'
        ]

    def validate(self, data):
        """Verifica che almeno uno tra delegato e sub_delega sia valorizzato."""
        if not data.get('delegato') and not data.get('sub_delega'):
            raise serializers.ValidationError(
                "Deve essere specificato almeno uno tra 'delegato' e 'sub_delega'"
            )
        return data


class DesignazioneRDLListSerializer(serializers.ModelSerializer):
    """Serializer leggero per lista designazioni."""
    ruolo_display = serializers.CharField(source='get_ruolo_display', read_only=True)
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    designante_nome = serializers.CharField(read_only=True)
    sezione_numero = serializers.IntegerField(source='sezione.numero', read_only=True)
    sezione_comune = serializers.CharField(source='sezione.comune.nome', read_only=True)
    sezione_municipio = serializers.SerializerMethodField()

    class Meta:
        model = DesignazioneRDL
        fields = [
            'id', 'sezione', 'sezione_numero', 'sezione_comune', 'sezione_municipio',
            'ruolo', 'ruolo_display', 'stato', 'stato_display', 'designante_nome',
            'cognome', 'nome', 'email', 'is_attiva'
        ]

    def get_sezione_municipio(self, obj):
        if obj.sezione and obj.sezione.municipio:
            return obj.sezione.municipio.numero
        return None


class BatchGenerazioneDocumentiSerializer(serializers.ModelSerializer):
    """Serializer per Batch Generazione Documenti."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    sub_delegato_nome = serializers.CharField(source='sub_delega.nome_completo', read_only=True)

    class Meta:
        model = BatchGenerazioneDocumenti
        fields = [
            'id', 'sub_delega', 'sub_delegato_nome',
            'tipo', 'tipo_display', 'stato', 'stato_display',
            'solo_sezioni', 'documento', 'data_generazione',
            'n_designazioni', 'n_pagine', 'created_at'
        ]
        read_only_fields = ['id', 'data_generazione', 'n_designazioni', 'n_pagine', 'created_at']


# =============================================================================
# Serializers per la vista "Mia Catena Deleghe"
# =============================================================================

class MiaCatenaSerializer(serializers.Serializer):
    """Serializer per la catena deleghe dell'utente loggato."""
    is_delegato = serializers.BooleanField()
    is_sub_delegato = serializers.BooleanField()
    is_rdl = serializers.BooleanField()
    deleghe_lista = DelegatoDiListaSerializer(many=True)
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


class MappaturaCreaSerializer(serializers.Serializer):
    """
    Serializer per creare una mappatura (DesignazioneRDL in stato BOZZA).
    Crea la designazione a partire da una RdlRegistration approvata.
    """
    rdl_registration_id = serializers.IntegerField()
    sezione_id = serializers.IntegerField()
    ruolo = serializers.ChoiceField(choices=['EFFETTIVO', 'SUPPLENTE'])

    def validate_rdl_registration_id(self, value):
        try:
            reg = RdlRegistration.objects.get(id=value, status='APPROVED')
        except RdlRegistration.DoesNotExist:
            raise serializers.ValidationError("RdlRegistration non trovata o non approvata")
        return value

    def validate_sezione_id(self, value):
        from territory.models import SezioneElettorale
        try:
            SezioneElettorale.objects.get(id=value)
        except SezioneElettorale.DoesNotExist:
            raise serializers.ValidationError("Sezione non trovata")
        return value

    def validate(self, data):
        """Verifica che non esista già una designazione attiva per lo stesso ruolo sulla stessa sezione."""
        existing = DesignazioneRDL.objects.filter(
            sezione_id=data['sezione_id'],
            ruolo=data['ruolo'],
            is_attiva=True
        ).exclude(stato='REVOCATA').exists()
        if existing:
            raise serializers.ValidationError(
                f"Esiste già un {data['ruolo']} attivo per questa sezione"
            )
        return data

    def create(self, validated_data):
        from territory.models import SezioneElettorale

        reg = RdlRegistration.objects.get(id=validated_data['rdl_registration_id'])
        sezione = SezioneElettorale.objects.get(id=validated_data['sezione_id'])
        user = self.context['request'].user

        # Trova la sub_delega dell'utente per questo territorio
        sub_delega = SubDelega.objects.filter(
            email=user.email,
            is_attiva=True
        ).filter(
            models.Q(comuni=sezione.comune) |
            models.Q(municipi__contains=[sezione.municipio_id])
        ).first()

        # Se non è sub-delegato, cerca se è delegato
        delegato = None
        if not sub_delega:
            delegato = DelegatoDiLista.objects.filter(email=user.email).first()

        # Determina lo stato in base al tipo_delega
        if sub_delega and sub_delega.puo_designare_direttamente:
            stato = 'CONFERMATA'
            approvata_da = user
            from django.utils import timezone
            data_approvazione = timezone.now()
        elif delegato:
            stato = 'CONFERMATA'
            approvata_da = user
            from django.utils import timezone
            data_approvazione = timezone.now()
        else:
            stato = 'BOZZA'
            approvata_da = None
            data_approvazione = None

        designazione = DesignazioneRDL.objects.create(
            delegato=delegato,
            sub_delega=sub_delega,
            sezione=sezione,
            ruolo=validated_data['ruolo'],
            cognome=reg.cognome,
            nome=reg.nome,
            luogo_nascita=reg.comune_nascita,
            data_nascita=reg.data_nascita,
            domicilio=f"{reg.indirizzo_residenza}, {reg.comune_residenza}",
            email=reg.email,
            telefono=reg.telefono,
            stato=stato,
            approvata_da_email=approvata_da.email if approvata_da else '',
            data_approvazione=data_approvazione,
            created_by_email=user.email,
        )
        return designazione


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
            'created_by', 'created_by_nome',
            'richiedi_approvazione', 'max_registrazioni', 'messaggio_conferma',
            'is_aperta', 'n_registrazioni', 'posti_disponibili',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

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
            seggio_preferenza=validated_data.get('seggio_preferenza', '').strip(),
            comune=comune,
            municipio=municipio,
            status=status,
            source='CAMPAGNA',
            campagna=campagna,
            consultazione=campagna.consultazione
        )

        return registration
