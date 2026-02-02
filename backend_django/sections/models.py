"""
Sections models: Section assignments and vote data collection.

This module defines:
- SectionAssignment: RDL/substitute assignments to electoral sections
- DatiSezione: Base data collected for a section in a consultation
- DatiScheda: Specific data for each ballot in a section
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class RdlRegistration(models.Model):
    """
    Registration of an RDL (Responsabile Di Lista).

    Supports two flows:
    1. Self-registration: user requests to become RDL, status=PENDING until approved
    2. Import by delegate: created directly with status=APPROVED

    Once approved, RDL can be assigned to sections via SectionAssignment.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('In attesa di approvazione')
        APPROVED = 'APPROVED', _('Approvato')
        REJECTED = 'REJECTED', _('Rifiutato')

    # Contact info (email is the key identifier)
    email = models.EmailField(_('email'), db_index=True)
    nome = models.CharField(_('nome'), max_length=100)
    cognome = models.CharField(_('cognome'), max_length=100)
    telefono = models.CharField(_('recapito telefonico'), max_length=20)

    # Personal data (required)
    comune_nascita = models.CharField(_('comune di nascita'), max_length=100)
    data_nascita = models.DateField(_('data di nascita'))

    # Residence (required)
    comune_residenza = models.CharField(_('residente nel comune di'), max_length=100)
    indirizzo_residenza = models.CharField(_('indirizzo di residenza'), max_length=255)

    # Assignment preferences
    seggio_preferenza = models.CharField(
        _('seggio/plesso di preferenza'),
        max_length=255,
        blank=True,
        help_text=_('Dove fare il Rappresentante di Lista')
    )

    # Scope (where they can operate)
    comune = models.ForeignKey(
        'territorio.Comune',
        on_delete=models.CASCADE,
        related_name='rdl_registrations',
        verbose_name=_('comune operativo')
    )
    municipio = models.ForeignKey(
        'territorio.Municipio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rdl_registrations',
        verbose_name=_('municipio di appartenenza'),
        help_text=_('Per grandi città con municipi')
    )

    # Status
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Link to user (created when approved or when user logs in)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rdl_registrations',
        verbose_name=_('utente')
    )

    # Audit
    requested_at = models.DateTimeField(_('data richiesta'), auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rdl_approvals',
        verbose_name=_('approvato da')
    )
    approved_at = models.DateTimeField(_('data approvazione'), null=True, blank=True)
    rejection_reason = models.TextField(_('motivo rifiuto'), blank=True)
    notes = models.TextField(_('note'), blank=True)

    # Source of registration
    source = models.CharField(
        _('origine'),
        max_length=20,
        choices=[
            ('SELF', 'Auto-registrazione'),
            ('IMPORT', 'Import CSV'),
            ('MANUAL', 'Inserimento manuale'),
        ],
        default='SELF'
    )

    class Meta:
        verbose_name = _('registrazione RDL')
        verbose_name_plural = _('registrazioni RDL')
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['comune', 'status']),
        ]
        # No unique constraint - allow multiple registrations from same person

    def __str__(self):
        return f'{self.cognome} {self.nome} ({self.email}) - {self.comune}'

    @property
    def full_name(self):
        return f'{self.nome} {self.cognome}'

    def approve(self, approved_by):
        """Approve this registration and create/link user."""
        from django.utils import timezone
        from core.models import User, RoleAssignment

        self.status = self.Status.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()

        # Find or create user
        user, created = User.objects.get_or_create(
            email=self.email.lower(),
            defaults={
                'display_name': self.full_name,
                'first_name': self.nome,
                'last_name': self.cognome,
            }
        )
        self.user = user

        # Create RDL role assignment
        RoleAssignment.objects.get_or_create(
            user=user,
            role='RDL',
            defaults={
                'assigned_by': approved_by,
                'is_active': True,
            }
        )

        self.save()
        return user

    def reject(self, rejected_by, reason=''):
        """Reject this registration."""
        from django.utils import timezone

        self.status = self.Status.REJECTED
        self.approved_by = rejected_by  # Store who rejected
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class SectionAssignment(models.Model):
    """
    Assignment of a user (RDL or substitute) to an electoral section.

    This is the MAPPATURA (operational assignment):
    - Links RdlRegistration to SezioneElettorale
    - Freely modifiable
    - No formal document generated

    For formal designation (DesignazioneRDL), see delegations app.
    """
    class Role(models.TextChoices):
        RDL = 'RDL', _('Responsabile di Lista')
        SUPPLENTE = 'SUPPLENTE', _('Supplente')

    sezione = models.ForeignKey(
        'territorio.SezioneElettorale',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('sezione')
    )
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='section_assignments',
        verbose_name=_('consultazione')
    )
    # Primary FK - la fonte di verità per l'RDL assegnato
    rdl_registration = models.ForeignKey(
        'RdlRegistration',
        on_delete=models.CASCADE,
        related_name='section_assignments',
        verbose_name=_('registrazione RDL'),
        help_text=_('RDL dal pool approvati - cancellando l\'RDL si cancella l\'assegnazione')
    )

    # Legacy - mantenuto per compatibilità, derivato da rdl_registration.user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='section_assignments',
        verbose_name=_('utente (legacy)'),
        help_text=_('Derivato da rdl_registration.user')
    )
    role = models.CharField(
        _('ruolo'),
        max_length=20,
        choices=Role.choices,
        default=Role.RDL
    )

    # Audit
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made',
        verbose_name=_('assegnato da')
    )
    assigned_at = models.DateTimeField(_('data assegnazione'), auto_now_add=True)
    notes = models.TextField(_('note'), blank=True)

    class Meta:
        verbose_name = _('assegnazione sezione')
        verbose_name_plural = _('assegnazioni sezioni')
        ordering = ['sezione__comune', 'sezione__numero']
        indexes = [
            models.Index(fields=['rdl_registration', 'consultazione']),
            models.Index(fields=['sezione', 'consultazione']),
        ]
        constraints = [
            # Un RDL può essere assegnato una sola volta per sezione/consultazione
            models.UniqueConstraint(
                fields=['sezione', 'consultazione', 'rdl_registration'],
                name='unique_assignment_per_rdl'
            ),
            # Una sezione può avere un solo effettivo e un solo supplente
            models.UniqueConstraint(
                fields=['sezione', 'consultazione', 'role'],
                name='unique_role_per_sezione'
            ),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.sezione} ({self.get_role_display()})'


class DatiSezione(models.Model):
    """
    Base data collected for a section in a consultation.
    Common values across all ballots for this section.
    """
    sezione = models.ForeignKey(
        'territorio.SezioneElettorale',
        on_delete=models.CASCADE,
        related_name='dati',
        verbose_name=_('sezione')
    )
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='dati_sezioni',
        verbose_name=_('consultazione')
    )

    # Turnout (common to all ballots for this section)
    elettori_maschi = models.IntegerField(
        _('elettori maschi'),
        null=True,
        blank=True
    )
    elettori_femmine = models.IntegerField(
        _('elettori femmine'),
        null=True,
        blank=True
    )
    votanti_maschi = models.IntegerField(
        _('votanti maschi'),
        null=True,
        blank=True
    )
    votanti_femmine = models.IntegerField(
        _('votanti femmine'),
        null=True,
        blank=True
    )

    # Status flags
    is_complete = models.BooleanField(
        _('completato'),
        default=False,
        help_text=_('Tutti i dati inseriti')
    )
    is_verified = models.BooleanField(
        _('verificato'),
        default=False,
        help_text=_('Dati verificati da un referente')
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sezioni_verificate',
        verbose_name=_('verificato da')
    )
    verified_at = models.DateTimeField(_('data verifica'), null=True, blank=True)

    # Audit
    inserito_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dati_sezioni_inseriti',
        verbose_name=_('inserito da')
    )
    inserito_at = models.DateTimeField(_('data inserimento'), null=True, blank=True)
    aggiornato_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('dati sezione')
        verbose_name_plural = _('dati sezioni')
        unique_together = ['sezione', 'consultazione']
        ordering = ['sezione__comune', 'sezione__numero']

    def __str__(self):
        return f'Dati {self.sezione} - {self.consultazione}'

    @property
    def totale_elettori(self):
        """Total registered voters."""
        if self.elettori_maschi is not None and self.elettori_femmine is not None:
            return self.elettori_maschi + self.elettori_femmine
        return None

    @property
    def totale_votanti(self):
        """Total voters who cast a ballot."""
        if self.votanti_maschi is not None and self.votanti_femmine is not None:
            return self.votanti_maschi + self.votanti_femmine
        return None

    @property
    def affluenza_percentuale(self):
        """Turnout percentage."""
        elettori = self.totale_elettori
        votanti = self.totale_votanti
        if elettori and votanti:
            return round((votanti / elettori) * 100, 2)
        return None


class DatiScheda(models.Model):
    """
    Specific data for each ballot in a section.
    E.g., a section in referendum 2025 will have 5 DatiScheda (one per question).
    """
    dati_sezione = models.ForeignKey(
        DatiSezione,
        on_delete=models.CASCADE,
        related_name='schede',
        verbose_name=_('dati sezione')
    )
    scheda = models.ForeignKey(
        'elections.SchedaElettorale',
        on_delete=models.CASCADE,
        related_name='dati',
        verbose_name=_('scheda')
    )

    # Ballot counts (common to all ballot types)
    schede_ricevute = models.IntegerField(
        _('schede ricevute'),
        null=True,
        blank=True
    )
    schede_autenticate = models.IntegerField(
        _('schede autenticate'),
        null=True,
        blank=True
    )
    schede_bianche = models.IntegerField(
        _('schede bianche'),
        null=True,
        blank=True
    )
    schede_nulle = models.IntegerField(
        _('schede nulle'),
        null=True,
        blank=True
    )
    schede_contestate = models.IntegerField(
        _('schede contestate'),
        null=True,
        blank=True
    )

    # Vote data (structure depends on ballot type - see examples in plan)
    voti = models.JSONField(
        _('voti'),
        null=True,
        blank=True,
        help_text=_('''
Struttura voti dipende dal tipo scheda:
- Referendum: {"si": 523, "no": 300}
- Europee: {"liste": {"M5S": 250, "PD": 180}, "preferenze": {"FERRARA LAURA": 45}}
- Politiche: {"uninominale": {...}, "liste": {...}}
- Comunali: {"sindaco": {...}, "liste": {...}, "preferenze": {...}}
        ''')
    )

    # Validation
    errori_validazione = models.TextField(
        _('errori validazione'),
        null=True,
        blank=True,
        help_text=_('Eventuali errori di validazione rilevati')
    )
    is_valid = models.BooleanField(
        _('valido'),
        default=True,
        help_text=_('False se ci sono errori di validazione')
    )

    # Audit
    inserito_at = models.DateTimeField(_('data inserimento'), null=True, blank=True)
    aggiornato_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('dati scheda')
        verbose_name_plural = _('dati schede')
        unique_together = ['dati_sezione', 'scheda']
        ordering = ['scheda__ordine']

    def __str__(self):
        return f'{self.dati_sezione.sezione} - {self.scheda.nome}'

    @property
    def totale_voti_validi(self):
        """Calculate total valid votes based on ballot type."""
        if not self.voti:
            return None

        # For referendum (SI/NO)
        if 'si' in self.voti and 'no' in self.voti:
            return self.voti.get('si', 0) + self.voti.get('no', 0)

        # For elections with lists
        if 'liste' in self.voti:
            return sum(self.voti['liste'].values())

        return None

    def validate_data(self):
        """
        Validate the data for consistency.
        Returns a list of error messages.
        """
        errors = []

        # Check ballot counts
        if self.schede_ricevute and self.schede_autenticate:
            if self.schede_autenticate > self.schede_ricevute:
                errors.append(_('Schede autenticate > schede ricevute'))

        # Check vote totals
        if self.voti and self.schede_autenticate:
            voti_validi = self.totale_voti_validi or 0
            bianche = self.schede_bianche or 0
            nulle = self.schede_nulle or 0
            contestate = self.schede_contestate or 0

            totale = voti_validi + bianche + nulle + contestate
            if totale > self.schede_autenticate:
                errors.append(_('Totale schede > schede autenticate'))

        self.errori_validazione = '\n'.join(errors) if errors else None
        self.is_valid = len(errors) == 0
        return errors


class SectionDataHistory(models.Model):
    """
    History of changes to section data for audit purposes.
    """
    dati_sezione = models.ForeignKey(
        DatiSezione,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_('dati sezione')
    )
    dati_scheda = models.ForeignKey(
        DatiScheda,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='history',
        verbose_name=_('dati scheda')
    )

    # What changed
    campo = models.CharField(_('campo modificato'), max_length=100)
    valore_precedente = models.TextField(_('valore precedente'), null=True, blank=True)
    valore_nuovo = models.TextField(_('valore nuovo'), null=True, blank=True)

    # Who and when
    modificato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modifiche_dati',
        verbose_name=_('modificato da')
    )
    modificato_at = models.DateTimeField(_('data modifica'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('indirizzo IP'), null=True, blank=True)

    class Meta:
        verbose_name = _('storico dati sezione')
        verbose_name_plural = _('storico dati sezioni')
        ordering = ['-modificato_at']

    def __str__(self):
        return f'{self.dati_sezione.sezione} - {self.campo} ({self.modificato_at})'
