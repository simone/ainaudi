"""
Core models: User, RoleAssignment

Custom User model supporting multi-provider authentication and hierarchical roles.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group as AuthGroup
from django.db import models
from django.utils.translation import gettext_lazy as _


class Gruppo(AuthGroup):
    """
    Proxy model for Django's Group to move it under core app in admin.
    """
    class Meta:
        proxy = True
        verbose_name = _('gruppo')
        verbose_name_plural = _('gruppi')


def get_user_by_email(email):
    """
    Restituisce l'utente associato all'email, o un oggetto placeholder se non esiste.

    Il placeholder ha attributi minimi per evitare errori nei template/serializer:
    - email: l'email originale
    - display_name: '[Rimosso: {email}]'
    - is_active: False
    - pk: None (non salvato)
    """
    if not email:
        return None

    user = User.objects.filter(email=email).first()
    if user:
        return user

    # Crea un oggetto placeholder (non salvato in DB)
    placeholder = User(email=email)
    placeholder.display_name = f'[Rimosso: {email}]'
    placeholder.first_name = 'N/A'
    placeholder.last_name = ''
    placeholder.is_active = False
    placeholder.pk = None  # Non salvato
    return placeholder


class UserManager(BaseUserManager):
    """Custom manager for User model with email as username."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError(_('L\'indirizzo email è obbligatorio'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser deve avere is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser deve avere is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model.

    Uses email as the unique identifier instead of username.
    Supports linking multiple identity providers (Google, Magic Link, M5S SSO).
    """
    # Remove username field, use email instead
    username = None
    email = models.EmailField(_('indirizzo email'), unique=True)

    # Profile fields
    display_name = models.CharField(
        _('nome visualizzato'),
        max_length=255,
        blank=True,
        help_text=_('Nome da visualizzare nell\'applicazione')
    )
    phone_number = models.CharField(
        _('numero di telefono'),
        max_length=20,
        blank=True,
        null=True
    )
    avatar_url = models.URLField(
        _('URL avatar'),
        blank=True,
        null=True
    )

    # Audit fields
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)
    last_login_ip = models.GenericIPAddressField(
        _('ultimo IP di login'),
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _('utente')
        verbose_name_plural = _('utenti')
        ordering = ['email']

    def __str__(self):
        return self.display_name or self.email

    def get_full_name(self):
        """Return display_name or first_name + last_name or email."""
        if self.display_name:
            return self.display_name
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.email

    def get_short_name(self):
        """Return first_name or display_name or email."""
        return self.first_name or self.display_name or self.email.split('@')[0]


class RoleAssignment(models.Model):
    """
    Assigns roles to users with optional scope (comune, municipio, etc.).

    Supports hierarchical delegation: DELEGATE > SUBDELEGATE > RDL
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Amministratore')
        DELEGATE = 'DELEGATE', _('Delegato')
        SUBDELEGATE = 'SUBDELEGATE', _('Sub-delegato')
        RDL = 'RDL', _('Responsabile di Lista')
        KPI_VIEWER = 'KPI_VIEWER', _('Visualizzatore KPI')
        OBSERVER = 'OBSERVER', _('Osservatore')

    class ScopeType(models.TextChoices):
        GLOBAL = 'global', _('Globale')
        REGIONE = 'regione', _('Regione')
        PROVINCIA = 'provincia', _('Provincia')
        COMUNE = 'comune', _('Comune')
        MUNICIPIO = 'municipio', _('Municipio')
        SEZIONE = 'sezione', _('Sezione')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name=_('utente')
    )
    role = models.CharField(
        _('ruolo'),
        max_length=20,
        choices=Role.choices
    )

    # Scope: defines where the role applies
    scope_type = models.CharField(
        _('tipo ambito'),
        max_length=20,
        choices=ScopeType.choices,
        null=True,
        blank=True,
        help_text=_('Tipo di ambito territoriale')
    )
    scope_value = models.CharField(
        _('valore ambito'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Valore specifico dell\'ambito (es. "Roma", "Municipio I")')
    )

    # Foreign keys to territory (optional, for referential integrity)
    scope_regione = models.ForeignKey(
        'territory.Regione',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('regione')
    )
    scope_provincia = models.ForeignKey(
        'territory.Provincia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('provincia')
    )
    scope_comune = models.ForeignKey(
        'territory.Comune',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('comune')
    )

    # Scoping by consultation (required for all roles - enforced at form level)
    # Database allows null for migration compatibility, but forms/API enforce required
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        null=True,  # DB allows null for migration, but logically required
        related_name='role_assignments',
        verbose_name=_('consultazione'),
        help_text=_('Consultazione per cui il ruolo è valido (obbligatorio)')
    )

    # Audit
    assigned_by_email = models.EmailField(
        _('assegnato da (email)'),
        blank=True,
        help_text=_('Email di chi ha assegnato il ruolo')
    )
    assigned_at = models.DateTimeField(_('data assegnazione'), auto_now_add=True)
    valid_from = models.DateTimeField(_('valido da'), null=True, blank=True)
    valid_to = models.DateTimeField(_('valido fino a'), null=True, blank=True)
    is_active = models.BooleanField(_('attivo'), default=True)
    notes = models.TextField(_('note'), blank=True)

    class Meta:
        verbose_name = _('assegnazione ruolo')
        verbose_name_plural = _('assegnazioni ruoli')
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['scope_type', 'scope_value']),
        ]

    def __str__(self):
        scope = f' ({self.scope_type}: {self.scope_value})' if self.scope_type else ''
        return f'{self.user.email} - {self.get_role_display()}{scope}'

    @property
    def assigned_by(self):
        """Restituisce l'utente che ha assegnato il ruolo."""
        return get_user_by_email(self.assigned_by_email)

    @property
    def is_valid(self):
        """Check if the role assignment is currently valid."""
        from django.utils import timezone
        now = timezone.now()

        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True


class AuditLog(models.Model):
    """
    Audit log for tracking important actions.
    """
    class Action(models.TextChoices):
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        CREATE = 'CREATE', _('Creazione')
        UPDATE = 'UPDATE', _('Modifica')
        DELETE = 'DELETE', _('Eliminazione')
        ASSIGN_ROLE = 'ASSIGN_ROLE', _('Assegnazione ruolo')
        REVOKE_ROLE = 'REVOKE_ROLE', _('Revoca ruolo')
        DELEGATE = 'DELEGATE', _('Delega')
        SUBMIT_DATA = 'SUBMIT_DATA', _('Invio dati')
        GENERATE_PDF = 'GENERATE_PDF', _('Generazione PDF')

    user_email = models.EmailField(
        _('utente (email)'),
        blank=True,
        help_text=_('Email dell\'utente che ha eseguito l\'azione')
    )
    action = models.CharField(
        _('azione'),
        max_length=20,
        choices=Action.choices
    )
    target_model = models.CharField(
        _('modello target'),
        max_length=100,
        blank=True
    )
    target_id = models.CharField(
        _('ID target'),
        max_length=100,
        blank=True
    )
    details = models.JSONField(
        _('dettagli'),
        default=dict,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        _('indirizzo IP'),
        blank=True,
        null=True
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True
    )
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('log audit')
        verbose_name_plural = _('log audit')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_email', 'action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def __str__(self):
        return f'{self.timestamp} - {self.user_email} - {self.get_action_display()}'

    @property
    def user(self):
        """Restituisce l'utente che ha eseguito l'azione."""
        return get_user_by_email(self.user_email)


class CustomPermission(models.Model):
    """
    Proxy model per definire custom permissions per il sistema.
    Non crea tabella, usa django.contrib.auth.Permission.

    Permessi definiti (uno per ogni voce del menu):
    1. can_view_dashboard: Dashboard
    2. can_manage_territory: Territorio (admin territorio)
    3. can_manage_elections: Consultazione (schede elettorali)
    4. can_manage_campaign: Campagne reclutamento RDL
    5. can_manage_rdl: Gestione RDL registrations
    6. can_manage_sections: Gestione Sezioni elettorali
    7. can_manage_mappatura: Mappatura RDL → Sezioni
    8. can_manage_delegations: Catena Deleghe
    9. can_manage_designazioni: Designazioni RDL formali
    10. can_manage_templates: Template PDF
    11. can_generate_documents: Genera Moduli PDF
    12. has_scrutinio_access: Scrutinio (inserimento dati)
    13. can_view_resources: Risorse/Documenti
    14. can_view_live_results: Risultati Live (scrutinio aggregato)
    15. can_view_kpi: Diretta (KPI dashboard)

    Extra:
    - can_manage_events: Gestione eventi (corsi, Zoom)
    - can_ask_to_ai_assistant: Uso chatbot AI (futuro)
    - can_manage_incidents: Gestione segnalazioni (futuro)
    """
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            # Menu principale (15 voci)
            ('can_view_dashboard', 'Can view dashboard'),
            ('can_manage_territory', 'Can manage territory (regions, provinces, comuni)'),
            ('can_manage_elections', 'Can manage elections and ballots'),
            ('can_manage_campaign', 'Can manage RDL recruitment campaigns'),
            ('can_manage_rdl', 'Can manage RDL registrations'),
            ('can_manage_sections', 'Can manage electoral sections'),
            ('can_manage_mappatura', 'Can manage RDL to sections mapping'),
            ('can_manage_delegations', 'Can manage delegations chain'),
            ('can_manage_designazioni', 'Can manage formal RDL designations'),
            ('can_manage_templates', 'Can manage PDF templates'),
            ('can_generate_documents', 'Can generate PDF documents'),
            ('has_scrutinio_access', 'Can enter section scrutinio data'),
            ('can_view_resources', 'Can view resources and documents'),
            ('can_view_live_results', 'Can view live election results'),
            ('can_view_kpi', 'Can view KPI dashboard'),

            # Funzionalità riservate admin
            ('can_manage_mass_email', 'Can manage mass email templates and sending'),
            ('can_manage_events', 'Can manage events (courses, Zoom meetings)'),

            # Funzionalità extra (future)
            ('can_ask_to_ai_assistant', 'Can use AI assistant chatbot'),
            ('can_manage_incidents', 'Can manage incident reports'),
        ]
