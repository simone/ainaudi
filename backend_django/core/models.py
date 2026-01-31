"""
Core models: User, IdentityProviderLink, RoleAssignment

Custom User model supporting multi-provider authentication and hierarchical roles.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


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


class IdentityProviderLink(models.Model):
    """
    Links a User to an identity provider (Google, Magic Link, M5S SSO).

    Allows users to authenticate via multiple providers with the same account.
    """
    class Provider(models.TextChoices):
        GOOGLE = 'google', _('Google')
        MAGIC_LINK = 'magic_link', _('Magic Link')
        M5S_SSO = 'm5s_sso', _('M5S SSO')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='identity_links',
        verbose_name=_('utente')
    )
    provider = models.CharField(
        _('provider'),
        max_length=20,
        choices=Provider.choices
    )
    provider_uid = models.CharField(
        _('ID provider'),
        max_length=255,
        help_text=_('ID univoco dell\'utente presso il provider')
    )
    provider_email = models.EmailField(
        _('email provider'),
        blank=True,
        null=True,
        help_text=_('Email associata al provider (può differire da quella principale)')
    )

    # Metadata
    linked_at = models.DateTimeField(_('data collegamento'), auto_now_add=True)
    last_used_at = models.DateTimeField(_('ultimo utilizzo'), blank=True, null=True)
    is_primary = models.BooleanField(
        _('provider primario'),
        default=False,
        help_text=_('Se True, questo è il provider principale per l\'utente')
    )

    class Meta:
        verbose_name = _('collegamento identity provider')
        verbose_name_plural = _('collegamenti identity provider')
        unique_together = ['provider', 'provider_uid']
        ordering = ['-is_primary', '-last_used_at']

    def __str__(self):
        return f'{self.user.email} - {self.get_provider_display()}'


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
        'territorio.Regione',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('regione')
    )
    scope_provincia = models.ForeignKey(
        'territorio.Provincia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('provincia')
    )
    scope_comune = models.ForeignKey(
        'territorio.Comune',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name=_('comune')
    )

    # Audit
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roles_assigned',
        verbose_name=_('assegnato da')
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

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('utente')
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
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def __str__(self):
        return f'{self.timestamp} - {self.user} - {self.get_action_display()}'
