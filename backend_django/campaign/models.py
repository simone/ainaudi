"""
Campaign models: Recruitment campaigns and RDL registrations.

This module defines:
- CampagnaReclutamento: Recruitment campaigns for RDLs
- RdlRegistration: RDL registration requests
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import get_user_by_email


class CampagnaReclutamento(models.Model):
    """
    Campagna di reclutamento RDL.

    Permette ai delegati di creare link pubblici per raccogliere candidature RDL.
    Ogni campagna ha uno slug univoco che può essere usato come URL pubblico:
    /campagna/{slug}

    La campagna può essere limitata per:
    - Territorio (regioni, province, comuni)
    - Periodo (data_apertura, data_chiusura)
    - Numero massimo di registrazioni
    """
    class Stato(models.TextChoices):
        BOZZA = 'BOZZA', _('Bozza')
        ATTIVA = 'ATTIVA', _('Attiva')
        CHIUSA = 'CHIUSA', _('Chiusa')

    # Consultazione di riferimento
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='campagne_reclutamento',
        verbose_name=_('consultazione')
    )

    # Identificazione campagna
    nome = models.CharField(
        _('nome'),
        max_length=200,
        help_text=_('Nome identificativo della campagna')
    )
    slug = models.SlugField(
        _('slug'),
        max_length=100,
        unique=True,
        help_text=_('URL pubblico: /campagna/{slug}')
    )
    descrizione = models.TextField(
        _('descrizione'),
        blank=True,
        help_text=_('Descrizione mostrata nella pagina di registrazione')
    )

    # Periodo di validità
    data_apertura = models.DateTimeField(
        _('data apertura'),
        help_text=_('Quando la campagna diventa accessibile')
    )
    data_chiusura = models.DateTimeField(
        _('data chiusura'),
        help_text=_('Quando la campagna termina')
    )

    # Territorio di competenza
    territorio_regioni = models.ManyToManyField(
        'territory.Regione',
        blank=True,
        related_name='campagne_reclutamento',
        verbose_name=_('regioni'),
        help_text=_('Regioni dove è possibile registrarsi')
    )
    territorio_province = models.ManyToManyField(
        'territory.Provincia',
        blank=True,
        related_name='campagne_reclutamento',
        verbose_name=_('province'),
        help_text=_('Province dove è possibile registrarsi')
    )
    territorio_comuni = models.ManyToManyField(
        'territory.Comune',
        blank=True,
        related_name='campagne_reclutamento',
        verbose_name=_('comuni'),
        help_text=_('Comuni dove è possibile registrarsi')
    )

    # Stato
    stato = models.CharField(
        _('stato'),
        max_length=15,
        choices=Stato.choices,
        default=Stato.BOZZA
    )

    # Chi ha creato la campagna
    delegato = models.ForeignKey(
        'delegations.Delegato',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='campagne_reclutamento',
        verbose_name=_('delegato'),
        help_text=_('Delegato che ha creato la campagna')
    )
    sub_delega = models.ForeignKey(
        'delegations.SubDelega',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='campagne_reclutamento',
        verbose_name=_('sub-delega'),
        help_text=_('Sub-delegato che ha creato la campagna')
    )
    created_by_email = models.EmailField(_('creato da (email)'), blank=True)

    # Configurazione
    richiedi_approvazione = models.BooleanField(
        _('richiedi approvazione'),
        default=True,
        help_text=_('Se True, le registrazioni devono essere approvate manualmente')
    )
    max_registrazioni = models.IntegerField(
        _('max registrazioni'),
        null=True,
        blank=True,
        help_text=_('Numero massimo di registrazioni (null = illimitato)')
    )
    messaggio_conferma = models.TextField(
        _('messaggio conferma'),
        blank=True,
        help_text=_('Messaggio mostrato dopo la registrazione')
    )

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)

    class Meta:
        verbose_name = _('Campagna di Reclutamento')
        verbose_name_plural = _('Campagne di Reclutamento')
        ordering = ['-data_apertura']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['stato', 'data_apertura', 'data_chiusura']),
        ]

    def __str__(self):
        return f"{self.nome} ({self.consultazione})"

    @property
    def created_by(self):
        """Restituisce l'utente che ha creato questo record."""
        return get_user_by_email(self.created_by_email)

    @property
    def is_aperta(self):
        """True se la campagna è attualmente aperta per registrazioni"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.stato == self.Stato.ATTIVA and
            self.data_apertura <= now <= self.data_chiusura
        )

    @property
    def n_registrazioni(self):
        """Numero di registrazioni ricevute"""
        return self.registrazioni.count()

    @property
    def posti_disponibili(self):
        """Numero di posti ancora disponibili (None = illimitato)"""
        if self.max_registrazioni is None:
            return None
        return max(0, self.max_registrazioni - self.n_registrazioni)

    def get_comuni_disponibili(self):
        """
        Restituisce i comuni dove è possibile registrarsi.
        Logica: se specificati comuni, usa quelli; altrimenti province; altrimenti regioni.
        """
        from territory.models import Comune

        if self.territorio_comuni.exists():
            return self.territorio_comuni.all()

        if self.territorio_province.exists():
            return Comune.objects.filter(
                provincia__in=self.territorio_province.all()
            )

        if self.territorio_regioni.exists():
            return Comune.objects.filter(
                provincia__regione__in=self.territorio_regioni.all()
            )

        # Nessun territorio specificato = tutti i comuni
        return Comune.objects.all()


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

    # Fuorisede info
    fuorisede = models.BooleanField(
        _('fuorisede'),
        null=True,
        blank=True,
        help_text=_('Lavora o studia in un comune diverso dalla residenza')
    )
    comune_domicilio = models.CharField(
        _('comune di domicilio'),
        max_length=100,
        blank=True,
        help_text=_('Se fuorisede, comune dove lavora/studia')
    )
    indirizzo_domicilio = models.CharField(
        _('indirizzo di domicilio'),
        max_length=255,
        blank=True,
        help_text=_('Se fuorisede, indirizzo di domicilio')
    )

    # Assignment preferences
    seggio_preferenza = models.CharField(
        _('seggio/plesso di preferenza'),
        max_length=255,
        blank=True,
        help_text=_('Dove fare il Rappresentante di Lista')
    )

    # Scope (where they can operate)
    comune = models.ForeignKey(
        'territory.Comune',
        on_delete=models.CASCADE,
        related_name='rdl_registrations',
        verbose_name=_('comune operativo')
    )
    municipio = models.ForeignKey(
        'territory.Municipio',
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

    # Audit
    requested_at = models.DateTimeField(_('data richiesta'), auto_now_add=True)
    approved_by_email = models.EmailField(_('approvato da (email)'), blank=True)
    approved_at = models.DateTimeField(_('data approvazione'), null=True, blank=True)
    rejection_reason = models.TextField(_('motivo rifiuto'), blank=True)
    notes = models.TextField(_('note'), blank=True)

    # Geolocation
    latitudine = models.DecimalField(
        _('latitudine'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitudine = models.DecimalField(
        _('longitudine'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    geocoded_at = models.DateTimeField(
        _('data geocodifica'),
        null=True,
        blank=True
    )
    geocode_source = models.CharField(
        _('sorgente geocodifica'),
        max_length=30,
        blank=True,
        default='',
        help_text=_('es. "google", "manual"')
    )
    geocode_quality = models.CharField(
        _('qualità geocodifica'),
        max_length=30,
        blank=True,
        default='',
        help_text=_('ROOFTOP, RANGE_INTERPOLATED, GEOMETRIC_CENTER, APPROXIMATE')
    )
    geocode_place_id = models.CharField(
        _('Google Place ID'),
        max_length=255,
        blank=True,
        default=''
    )
    sezioni_vicine = models.JSONField(
        _('sezioni vicine'),
        default=list,
        blank=True,
        help_text=_('Top 10 plessi più vicini [{indirizzo, distanza_km, sezioni: [numeri]}]')
    )

    # Source of registration
    source = models.CharField(
        _('origine'),
        max_length=20,
        choices=[
            ('SELF', 'Auto-registrazione'),
            ('IMPORT', 'Import CSV'),
            ('MANUAL', 'Inserimento manuale'),
            ('CAMPAGNA', 'Campagna di reclutamento'),
        ],
        default='SELF'
    )

    # Campaign link (if registered via campaign)
    campagna = models.ForeignKey(
        CampagnaReclutamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrazioni',
        verbose_name=_('campagna di reclutamento')
    )

    # Consultation link (for RBAC scoping)
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='rdl_registrations',
        verbose_name=_('consultazione'),
        help_text=_('Consultazione per cui l\'RDL si è registrato')
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

    def __str__(self):
        return f'{self.cognome} {self.nome} ({self.email}) - {self.comune}'

    @property
    def full_name(self):
        return f'{self.nome} {self.cognome}'

    @property
    def user(self):
        """Restituisce l'utente associato a questa email."""
        return get_user_by_email(self.email)

    @property
    def approved_by(self):
        """Restituisce l'utente che ha approvato questa registrazione."""
        return get_user_by_email(self.approved_by_email)

    def approve(self, approved_by_user):
        """Approve this registration and create/link user."""
        from django.utils import timezone
        from core.models import User, RoleAssignment

        # Accetta sia stringa email che oggetto User
        if hasattr(approved_by_user, 'email'):
            approved_by_email = approved_by_user.email
        else:
            approved_by_email = approved_by_user

        self.status = self.Status.APPROVED
        self.approved_by_email = approved_by_email
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

        # Create RDL role assignment scoped to consultazione
        RoleAssignment.objects.get_or_create(
            user=user,
            role='RDL',
            consultazione=self.consultazione,
            defaults={
                'assigned_by_email': approved_by_email,
                'is_active': True,
            }
        )

        self.save()
        return user

    def reject(self, rejected_by_user, reason=''):
        """Reject this registration."""
        from django.utils import timezone

        # Accetta sia stringa email che oggetto User
        if hasattr(rejected_by_user, 'email'):
            rejected_by_email = rejected_by_user.email
        else:
            rejected_by_email = rejected_by_user

        self.status = self.Status.REJECTED
        self.approved_by_email = rejected_by_email  # Store who rejected
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
