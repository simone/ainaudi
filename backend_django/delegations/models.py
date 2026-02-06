"""
Sistema di Deleghe Elettorali - Modello Django

Gerarchia delle deleghe secondo la normativa italiana (DPR 361/1957 Art. 25):

    PARTITO (M5S)
        ↓ nomina (atto formale del partito)
    DELEGATO DI LISTA (deputati, senatori, consiglieri regionali)
        ↓ sub-delega (con firma autenticata)
    SUB-DELEGATO (per territorio specifico: comuni/municipi)
        ↓ designa
    RDL (Responsabile Di Lista) - Effettivo + Supplente

Note:
- Un Delegato può sub-delegare a più Sub-delegati (uno per territorio)
- Un Sub-delegato può ricevere deleghe da più Delegati (es. Camera + Senato)
- La catena delle deleghe viene allegata nel PDF di designazione RDL
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import get_user_by_email


# =============================================================================
# DELEGATO DI LISTA (nominato dal Partito)
# =============================================================================

class DelegatoDiLista(models.Model):
    """
    Delegato di Lista nominato dal Partito.
    Sono eletti: deputati, senatori, consiglieri regionali, eurodeputati.
    Ricevono la delega dal partito per una specifica consultazione elettorale.
    """
    class Carica(models.TextChoices):
        DEPUTATO = 'DEPUTATO', _('Deputato')
        SENATORE = 'SENATORE', _('Senatore')
        CONSIGLIERE_REGIONALE = 'CONSIGLIERE_REGIONALE', _('Consigliere Regionale')
        CONSIGLIERE_COMUNALE = 'CONSIGLIERE_COMUNALE', _('Consigliere Comunale')
        EURODEPUTATO = 'EURODEPUTATO', _('Europarlamentare')

    # Consultazione elettorale di riferimento
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='delegati_lista',
        verbose_name=_('consultazione')
    )

    # Dati anagrafici (come da documento di nomina)
    cognome = models.CharField(_('cognome'), max_length=100)
    nome = models.CharField(_('nome'), max_length=100)
    luogo_nascita = models.CharField(_('luogo di nascita'), max_length=100)
    data_nascita = models.DateField(_('data di nascita'))

    # Carica elettiva
    carica = models.CharField(_('carica'), max_length=30, choices=Carica.choices)
    circoscrizione = models.CharField(
        _('circoscrizione (testo)'),
        max_length=100,
        blank=True,
        help_text=_('Campo descrittivo, usare i campi territorio per i permessi')
    )

    # Territorio di competenza (determina quali sezioni può vedere)
    # Il delegato può operare su uno o più di questi livelli
    territorio_regioni = models.ManyToManyField(
        'territory.Regione',
        blank=True,
        related_name='delegati_lista',
        verbose_name=_('regioni'),
        help_text=_('Regioni di competenza')
    )
    territorio_province = models.ManyToManyField(
        'territory.Provincia',
        blank=True,
        related_name='delegati_lista',
        verbose_name=_('province'),
        help_text=_('Province di competenza')
    )
    territorio_comuni = models.ManyToManyField(
        'territory.Comune',
        blank=True,
        related_name='delegati_lista',
        verbose_name=_('comuni'),
        help_text=_('Comuni di competenza')
    )
    territorio_municipi = models.JSONField(
        _('municipi'),
        default=list,
        blank=True,
        help_text=_('Lista di numeri di municipio (per grandi città)')
    )

    # Documento di nomina dal Partito
    data_nomina = models.DateField(_('data nomina'))
    numero_protocollo_nomina = models.CharField(
        _('numero protocollo'),
        max_length=50,
        blank=True
    )
    documento_nomina = models.FileField(
        _('documento nomina'),
        upload_to='deleghe/nomine_partito/',
        null=True, blank=True,
        help_text=_('PDF della nomina dal Partito')
    )

    # Contatti
    email = models.EmailField(_('email'), blank=True)
    telefono = models.CharField(_('telefono'), max_length=20, blank=True)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)

    class Meta:
        verbose_name = _('Delegato di Lista')
        verbose_name_plural = _('Delegati di Lista')
        ordering = ['consultazione', 'cognome', 'nome']
        unique_together = ['consultazione', 'cognome', 'nome', 'data_nascita']

    def __str__(self):
        return f"{self.get_carica_display()} {self.cognome} {self.nome}"

    @property
    def nome_completo(self):
        return f"{self.cognome} {self.nome}"

    @property
    def user(self):
        """Restituisce l'utente associato a questa email (per login/permessi)."""
        return get_user_by_email(self.email)


# =============================================================================
# SUB-DELEGA (dal Delegato di Lista al Sub-Delegato)
# =============================================================================

class SubDelega(models.Model):
    """
    Sub-delega: autorizzazione dal Delegato di Lista a un Sub-Delegato
    per operare su un territorio specifico (comuni e/o municipi).

    Tipi di sub-delega:
    - FIRMA_AUTENTICATA: Sub-Delegato può designare RDL direttamente (firma autenticata)
    - MAPPATURA: Sub-Delegato prepara bozze di designazione, il Delegato approva e firma
    """

    class TipoDelega(models.TextChoices):
        FIRMA_AUTENTICATA = 'FIRMA_AUTENTICATA', _('Con firma autenticata (può designare RDL)')
        MAPPATURA = 'MAPPATURA', _('Solo mappatura sezioni (Delegato firma)')

    # Chi delega
    delegato = models.ForeignKey(
        DelegatoDiLista,
        on_delete=models.CASCADE,
        related_name='sub_deleghe',
        verbose_name=_('delegato')
    )

    # Dati anagrafici del Sub-Delegato (come da documento)
    cognome = models.CharField(_('cognome'), max_length=100)
    nome = models.CharField(_('nome'), max_length=100)
    luogo_nascita = models.CharField(_('luogo di nascita'), max_length=100)
    data_nascita = models.DateField(_('data di nascita'))
    domicilio = models.CharField(
        _('domicilio'),
        max_length=255,
        help_text=_('Indirizzo completo di residenza/domicilio')
    )

    # Documento di identità
    tipo_documento = models.CharField(
        _('tipo documento'),
        max_length=50,
        help_text=_("es. Carta d'identità, Patente")
    )
    numero_documento = models.CharField(_('numero documento'), max_length=50)

    # Territorio di competenza (dal più ampio al più specifico)
    regioni = models.ManyToManyField(
        'territory.Regione',
        blank=True,
        related_name='sub_deleghe',
        verbose_name=_('regioni'),
        help_text=_('Regioni di competenza')
    )
    province = models.ManyToManyField(
        'territory.Provincia',
        blank=True,
        related_name='sub_deleghe',
        verbose_name=_('province'),
        help_text=_('Province di competenza')
    )
    comuni = models.ManyToManyField(
        'territory.Comune',
        blank=True,
        related_name='sub_deleghe',
        verbose_name=_('comuni'),
        help_text=_('Comuni di competenza')
    )
    municipi = models.JSONField(
        _('municipi'),
        default=list,
        blank=True,
        help_text=_('Lista di numeri di municipio (per grandi città)')
    )

    # Dati della sub-delega
    data_delega = models.DateField(_('data delega'))
    numero_protocollo = models.CharField(_('numero protocollo'), max_length=50, blank=True)

    # Autenticazione firma
    firma_autenticata = models.BooleanField(_('firma autenticata'), default=False)
    data_autenticazione = models.DateField(_('data autenticazione'), null=True, blank=True)
    autenticatore = models.CharField(
        _('autenticatore'),
        max_length=255,
        blank=True,
        help_text=_('Chi ha autenticato la firma (es. Segretario Comunale, Notaio)')
    )

    # Documento di sub-delega
    documento_delega = models.FileField(
        _('documento delega'),
        upload_to='deleghe/sub_deleghe/',
        null=True, blank=True,
        help_text=_('PDF della sub-delega firmata e autenticata')
    )

    # Contatti
    email = models.EmailField(_('email'))
    telefono = models.CharField(_('telefono'), max_length=20, blank=True)

    # Tipo di delega
    tipo_delega = models.CharField(
        _('tipo delega'),
        max_length=20,
        choices=TipoDelega.choices,
        default=TipoDelega.MAPPATURA,
        help_text=_('Determina se il Sub-Delegato può designare direttamente o solo preparare mappature')
    )

    # Stato
    is_attiva = models.BooleanField(_('attiva'), default=True)
    revocata_il = models.DateField(_('revocata il'), null=True, blank=True)
    motivo_revoca = models.TextField(_('motivo revoca'), blank=True)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)
    created_by_email = models.EmailField(_('creato da (email)'), blank=True)

    class Meta:
        verbose_name = _('Sub-Delega')
        verbose_name_plural = _('Sub-Deleghe')
        ordering = ['delegato', 'cognome', 'nome']

    def __str__(self):
        return f"Sub-delega a {self.cognome} {self.nome} da {self.delegato}"

    @property
    def nome_completo(self):
        return f"{self.cognome} {self.nome}"

    @property
    def user(self):
        """Restituisce l'utente associato a questa email (per login/permessi)."""
        return get_user_by_email(self.email)

    @property
    def created_by(self):
        """Restituisce l'utente che ha creato questo record."""
        return get_user_by_email(self.created_by_email)

    @property
    def consultazione(self):
        """Consultazione ereditata dal Delegato"""
        return self.delegato.consultazione

    @property
    def puo_designare_direttamente(self):
        """True se può designare RDL direttamente (firma autenticata)"""
        return self.tipo_delega == self.TipoDelega.FIRMA_AUTENTICATA and self.firma_autenticata

    @property
    def solo_mappatura(self):
        """True se può solo preparare mappature (il Delegato deve approvare)"""
        return self.tipo_delega == self.TipoDelega.MAPPATURA

    def get_catena_deleghe(self):
        """
        Restituisce la catena delle deleghe per questo Sub-Delegato.
        Usata per generare il PDF con la catena allegata.
        """
        return {
            'partito': 'MOVIMENTO 5 STELLE',
            'delegato': {
                'cognome': self.delegato.cognome,
                'nome': self.delegato.nome,
                'carica': self.delegato.get_carica_display(),
                'circoscrizione': self.delegato.circoscrizione,
                'data_nomina': self.delegato.data_nomina,
            },
            'sub_delegato': {
                'cognome': self.cognome,
                'nome': self.nome,
                'luogo_nascita': self.luogo_nascita,
                'data_nascita': self.data_nascita,
                'domicilio': self.domicilio,
                'data_delega': self.data_delega,
            },
            'territorio': {
                'regioni': list(self.regioni.values_list('nome', flat=True)),
                'province': list(self.province.values_list('nome', flat=True)),
                'comuni': list(self.comuni.values_list('nome', flat=True)),
                'municipi': self.municipi,
            }
        }


# =============================================================================
# DESIGNAZIONE RDL (dal Delegato o Sub-Delegato al Rappresentante di Lista)
# =============================================================================

class DesignazioneRDL(models.Model):
    """
    Designazione di RDL (Responsabili Di Lista) per una sezione elettorale.
    Ogni sezione ha un RDL Effettivo e un RDL Supplente.

    MODELLO FINALE: 1 record per seggio con SNAPSHOT dei dati RDL.
    I dati sono copiati al momento della designazione per garantire immutabilità
    del documento formale (anche se l'RDL viene cancellato o modificato).

    La designazione può essere fatta:
    - Direttamente dal Delegato di Lista (delegato è valorizzato, sub_delega è null)
    - Dal Sub-Delegato con firma autenticata (sub_delega è valorizzato, stato=CONFERMATA)
    - Dal Sub-Delegato solo mappatura (sub_delega è valorizzato, stato=BOZZA fino ad approvazione Delegato)
    """
    class Stato(models.TextChoices):
        BOZZA = 'BOZZA', _('Bozza (in attesa approvazione Delegato)')
        CONFERMATA = 'CONFERMATA', _('Confermata')
        REVOCATA = 'REVOCATA', _('Revocata')

    # Chi designa - UNO dei due deve essere valorizzato
    delegato = models.ForeignKey(
        DelegatoDiLista,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='designazioni_rdl_dirette',
        verbose_name=_('delegato'),
        help_text=_('Se la designazione è fatta direttamente dal Delegato')
    )
    sub_delega = models.ForeignKey(
        SubDelega,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='designazioni_rdl',
        verbose_name=_('sub-delega'),
        help_text=_('Se la designazione è fatta dal Sub-Delegato')
    )

    # Sezione elettorale
    sezione = models.ForeignKey(
        'territory.SezioneElettorale',
        on_delete=models.CASCADE,
        related_name='designazioni_rdl',
        verbose_name=_('sezione')
    )

    # =========================================================================
    # RDL EFFETTIVO - Snapshot dei dati al momento della designazione
    # =========================================================================
    effettivo_cognome = models.CharField(_('effettivo cognome'), max_length=100, blank=True)
    effettivo_nome = models.CharField(_('effettivo nome'), max_length=100, blank=True)
    effettivo_email = models.EmailField(_('effettivo email'), blank=True)
    effettivo_telefono = models.CharField(_('effettivo telefono'), max_length=20, blank=True)
    effettivo_luogo_nascita = models.CharField(_('effettivo luogo nascita'), max_length=100, blank=True)
    effettivo_data_nascita = models.DateField(_('effettivo data nascita'), null=True, blank=True)
    effettivo_domicilio = models.CharField(_('effettivo domicilio'), max_length=255, blank=True)

    # =========================================================================
    # RDL SUPPLENTE - Snapshot dei dati al momento della designazione
    # =========================================================================
    supplente_cognome = models.CharField(_('supplente cognome'), max_length=100, blank=True)
    supplente_nome = models.CharField(_('supplente nome'), max_length=100, blank=True)
    supplente_email = models.EmailField(_('supplente email'), blank=True)
    supplente_telefono = models.CharField(_('supplente telefono'), max_length=20, blank=True)
    supplente_luogo_nascita = models.CharField(_('supplente luogo nascita'), max_length=100, blank=True)
    supplente_data_nascita = models.DateField(_('supplente data nascita'), null=True, blank=True)
    supplente_domicilio = models.CharField(_('supplente domicilio'), max_length=255, blank=True)

    # Stato della designazione
    stato = models.CharField(
        _('stato'),
        max_length=15,
        choices=Stato.choices,
        default=Stato.BOZZA,
        help_text=_('BOZZA = mappatura in attesa di approvazione del Delegato')
    )
    data_designazione = models.DateField(_('data designazione'), auto_now_add=True)
    is_attiva = models.BooleanField(_('attiva'), default=True)

    # Approvazione (per designazioni BOZZA approvate dal Delegato)
    approvata_da_email = models.EmailField(
        _('approvata da (email)'),
        blank=True,
        help_text=_('Email del Delegato che ha approvato la bozza')
    )
    data_approvazione = models.DateTimeField(_('data approvazione'), null=True, blank=True)

    # Batch PDF (per tracking conferma via PDF)
    batch_pdf = models.ForeignKey(
        'BatchGenerazioneDocumenti',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='designazioni',
        verbose_name=_('batch PDF'),
        help_text=_('Batch di generazione PDF associato')
    )

    # Revoca
    revocata_il = models.DateField(_('revocata il'), null=True, blank=True)
    motivo_revoca = models.TextField(_('motivo revoca'), blank=True)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)
    created_by_email = models.EmailField(_('creato da (email)'), blank=True)

    class Meta:
        verbose_name = _('Designazione RDL')
        verbose_name_plural = _('Designazioni RDL')
        ordering = ['sezione']
        constraints = [
            # Una sola designazione attiva e confermata per sezione
            models.UniqueConstraint(
                fields=['sezione'],
                condition=models.Q(is_attiva=True, stato='CONFERMATA'),
                name='unique_designazione_confermata_per_sezione'
            ),
            # Almeno uno tra delegato e sub_delega deve essere valorizzato
            models.CheckConstraint(
                check=models.Q(delegato__isnull=False) | models.Q(sub_delega__isnull=False),
                name='designazione_ha_delegante'
            ),
            # Almeno uno tra effettivo e supplente deve avere email
            models.CheckConstraint(
                check=~models.Q(effettivo_email='', supplente_email=''),
                name='designazione_ha_almeno_un_rdl'
            ),
        ]

    def __str__(self):
        stato_label = f" [{self.get_stato_display()}]" if self.stato != self.Stato.CONFERMATA else ""
        rdl_info = []
        if self.effettivo_email:
            rdl_info.append(f"Eff: {self.effettivo_cognome}")
        if self.supplente_email:
            rdl_info.append(f"Sup: {self.supplente_cognome}")
        rdl_str = ", ".join(rdl_info) if rdl_info else "Nessun RDL"
        return f"Sez. {self.sezione} - {rdl_str}{stato_label}"

    @property
    def approvata_da(self):
        """Restituisce l'utente che ha approvato questa designazione."""
        return get_user_by_email(self.approvata_da_email)

    @property
    def created_by(self):
        """Restituisce l'utente che ha creato questo record."""
        return get_user_by_email(self.created_by_email)

    @property
    def is_bozza(self):
        """True se è una bozza in attesa di approvazione"""
        return self.stato == self.Stato.BOZZA

    @property
    def is_confermata(self):
        """True se è confermata (designazione valida)"""
        return self.stato == self.Stato.CONFERMATA and self.is_attiva

    def approva(self, user_email):
        """
        Approva una designazione in bozza (chiamato dal Delegato).
        Passa lo stato da BOZZA a CONFERMATA.

        Args:
            user_email: Email dell'utente che approva (str o User object)
        """
        from django.utils import timezone

        if self.stato != self.Stato.BOZZA:
            raise ValueError("Solo le bozze possono essere approvate")

        # Accetta sia stringa email che oggetto User
        if hasattr(user_email, 'email'):
            user_email = user_email.email

        self.stato = self.Stato.CONFERMATA
        self.approvata_da_email = user_email
        self.data_approvazione = timezone.now()
        self.save(update_fields=['stato', 'approvata_da_email', 'data_approvazione', 'updated_at'])

    def rifiuta(self, user_email, motivo=''):
        """
        Rifiuta una designazione in bozza.
        """
        if self.stato != self.Stato.BOZZA:
            raise ValueError("Solo le bozze possono essere rifiutate")

        self.is_attiva = False
        self.motivo_revoca = motivo
        self.save(update_fields=['is_attiva', 'motivo_revoca', 'updated_at'])

    @property
    def consultazione(self):
        """Consultazione ereditata dalla catena"""
        if self.delegato:
            return self.delegato.consultazione
        elif self.sub_delega:
            return self.sub_delega.consultazione
        return None

    @property
    def designante(self):
        """Restituisce chi ha fatto la designazione (Delegato o Sub-Delegato)"""
        if self.sub_delega:
            return self.sub_delega
        return self.delegato

    @property
    def designante_nome(self):
        """Nome di chi ha fatto la designazione"""
        if self.sub_delega:
            return f"Sub-Delegato {self.sub_delega.nome_completo}"
        elif self.delegato:
            return f"{self.delegato.get_carica_display()} {self.delegato.nome_completo}"
        return "N/D"

    def get_catena_deleghe_completa(self):
        """
        Restituisce la catena completa delle deleghe per questa designazione.

        Due possibili catene:
        1. Partito → Delegato → RDL (designazione diretta)
        2. Partito → Delegato → Sub-Delegato → RDL (designazione tramite sub-delega)

        Usata per generare il PDF.
        """
        sezione_data = {
            'numero': self.sezione.numero,
            'comune': str(self.sezione.comune),
            'indirizzo': self.sezione.indirizzo,
        }

        effettivo_data = None
        if self.effettivo_email:
            effettivo_data = {
                'cognome': self.effettivo_cognome,
                'nome': self.effettivo_nome,
                'luogo_nascita': self.effettivo_luogo_nascita,
                'data_nascita': self.effettivo_data_nascita,
                'domicilio': self.effettivo_domicilio,
            }

        supplente_data = None
        if self.supplente_email:
            supplente_data = {
                'cognome': self.supplente_cognome,
                'nome': self.supplente_nome,
                'luogo_nascita': self.supplente_luogo_nascita,
                'data_nascita': self.supplente_data_nascita,
                'domicilio': self.supplente_domicilio,
            }

        if self.sub_delega:
            # Catena completa: Partito → Delegato → Sub-Delegato → RDL
            catena = self.sub_delega.get_catena_deleghe()
            catena['sezione'] = sezione_data
            catena['rdl_effettivo'] = effettivo_data
            catena['rdl_supplente'] = supplente_data
        else:
            # Catena diretta: Partito → Delegato → RDL
            catena = {
                'partito': 'MOVIMENTO 5 STELLE',
                'delegato': {
                    'cognome': self.delegato.cognome,
                    'nome': self.delegato.nome,
                    'carica': self.delegato.get_carica_display(),
                    'circoscrizione': self.delegato.circoscrizione,
                    'data_nomina': self.delegato.data_nomina,
                },
                'sub_delegato': None,
                'sezione': sezione_data,
                'rdl_effettivo': effettivo_data,
                'rdl_supplente': supplente_data,
            }

        return catena


# =============================================================================
# BATCH GENERAZIONE DOCUMENTI
# =============================================================================

class BatchGenerazioneDocumenti(models.Model):
    """
    Batch per generare documenti di designazione RDL in blocco.
    Utile per stampare tutte le designazioni di un territorio.
    """
    class Tipo(models.TextChoices):
        INDIVIDUALE = 'INDIVIDUALE', _('Moduli Individuali')
        RIEPILOGATIVO = 'RIEPILOGATIVO', _('Modulo Riepilogativo')

    class Stato(models.TextChoices):
        BOZZA = 'BOZZA', _('Bozza')
        GENERATO = 'GENERATO', _('Generato')
        APPROVATO = 'APPROVATO', _('Approvato')
        INVIATO = 'INVIATO', _('Inviato')

    # Consultazione elettorale di riferimento
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='batch_documenti',
        verbose_name=_('consultazione')
    )

    tipo = models.CharField(_('tipo'), max_length=20, choices=Tipo.choices)
    stato = models.CharField(
        _('stato'),
        max_length=20,
        choices=Stato.choices,
        default=Stato.BOZZA
    )

    # Filtri per le designazioni da includere
    solo_sezioni = models.JSONField(
        _('solo sezioni'),
        default=list,
        blank=True,
        help_text=_('Lista di ID sezioni da includere (vuoto = tutte)')
    )

    # Documento generato
    documento = models.FileField(
        _('documento'),
        upload_to='deleghe/batch/',
        null=True, blank=True
    )
    data_generazione = models.DateTimeField(_('data generazione'), null=True, blank=True)

    # Conteggi
    n_designazioni = models.IntegerField(_('numero designazioni'), default=0)
    n_pagine = models.IntegerField(_('numero pagine'), default=0)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    created_by_email = models.EmailField(_('creato da (email)'), blank=True)

    class Meta:
        verbose_name = _('Batch Generazione Documenti')
        verbose_name_plural = _('Batch Generazione Documenti')
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch {self.tipo} - {self.consultazione.nome} ({self.stato})"

    @property
    def created_by(self):
        """Restituisce l'utente che ha creato questo record."""
        return get_user_by_email(self.created_by_email)

    def approva(self, user_email):
        """
        Approva il batch e tutte le designazioni associate.
        Passa lo stato del batch a APPROVATO e le designazioni da BOZZA a CONFERMATA.

        Args:
            user_email: Email dell'utente che approva (str o User object)
        """
        from django.utils import timezone

        if self.stato != self.Stato.GENERATO:
            raise ValueError("Solo i batch generati possono essere approvati")

        # Accetta sia stringa email che oggetto User
        if hasattr(user_email, 'email'):
            user_email = user_email.email

        # Aggiorna stato batch
        self.stato = self.Stato.APPROVATO
        self.save(update_fields=['stato', 'updated_at'])

        # Conferma tutte le designazioni BOZZA associate a questo batch
        self.designazioni.filter(stato='BOZZA').update(
            stato='CONFERMATA',
            approvata_da_email=user_email,
            data_approvazione=timezone.now()
        )
