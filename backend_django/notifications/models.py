"""
Notifications models: Events, scheduled notifications, and device tokens.

This module defines:
- Event: Scheduled events (courses, Zoom meetings) with external links
- Notification: Scheduled push/email notifications triggered via Cloud Tasks
- DeviceToken: FCM registration tokens for push notifications
"""
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Event(models.Model):
    """
    A scheduled event (e.g., training course, Zoom meeting).

    Events are linked to a consultazione and can have an external URL.
    Notifications are auto-generated when an event is created/modified.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Attivo')
        CANCELLED = 'CANCELLED', _('Annullato')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name=_('consultazione'),
        null=True,
        blank=True,
        help_text=_('Se impostato, le notifiche vengono inviate agli utenti della consultazione')
    )
    title = models.CharField(_('titolo'), max_length=300)
    description = models.TextField(_('descrizione'), blank=True)
    start_at = models.DateTimeField(_('inizio'))
    end_at = models.DateTimeField(_('fine'))
    external_url = models.URLField(
        _('link esterno'),
        blank=True,
        help_text=_('Es. link Zoom per meeting online')
    )
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Territory filters: if all empty → visible to everyone
    # If any populated → visible only to users with sections in those territories
    regioni = models.ManyToManyField(
        'territory.Regione',
        blank=True,
        verbose_name=_('regioni'),
        help_text=_('Se vuoto, evento visibile a tutti. Se valorizzato, solo utenti con sezioni in queste regioni.')
    )
    province = models.ManyToManyField(
        'territory.Provincia',
        blank=True,
        verbose_name=_('province'),
        help_text=_('Filtro aggiuntivo per province.')
    )
    comuni = models.ManyToManyField(
        'territory.Comune',
        blank=True,
        verbose_name=_('comuni'),
        help_text=_('Filtro aggiuntivo per comuni.')
    )

    created_at = models.DateTimeField(_('creato il'), auto_now_add=True)
    updated_at = models.DateTimeField(_('aggiornato il'), auto_now=True)

    class Meta:
        verbose_name = _('evento')
        verbose_name_plural = _('eventi')
        ordering = ['start_at']
        indexes = [
            models.Index(fields=['status', 'start_at']),
            models.Index(fields=['consultazione', 'status']),
        ]

    def __str__(self):
        return f'{self.title} ({self.start_at:%d/%m/%Y %H:%M})'

    @property
    def temporal_status(self):
        """Returns FUTURO, IN_CORSO, or CONCLUSO based on current time."""
        now = timezone.now()
        if now < self.start_at:
            return 'FUTURO'
        elif now <= self.end_at:
            return 'IN_CORSO'
        return 'CONCLUSO'

    @property
    def is_live(self):
        return self.temporal_status == 'IN_CORSO'

    @property
    def has_territory_filter(self):
        """True if event is restricted to specific territories."""
        return (
            self.regioni.exists() or
            self.province.exists() or
            self.comuni.exists()
        )


class Notification(models.Model):
    """
    A scheduled notification to be sent via push and/or email.

    Created by the notification generator, dispatched by Cloud Tasks
    at the scheduled time. The internal send endpoint processes each
    notification idempotently.
    """
    class Channel(models.TextChoices):
        PUSH = 'PUSH', _('Push')
        EMAIL = 'EMAIL', _('Email')
        BOTH = 'BOTH', _('Push + Email')

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Programmata')
        SENT = 'SENT', _('Inviata')
        FAILED = 'FAILED', _('Fallita')
        CANCELLED = 'CANCELLED', _('Annullata')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('utente')
    )

    # Exactly one of these must be set (XOR constraint)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('evento'),
        null=True,
        blank=True
    )
    section_assignment = models.ForeignKey(
        'data.SectionAssignment',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('assegnazione sezione'),
        null=True,
        blank=True
    )

    title = models.CharField(_('titolo'), max_length=300)
    body = models.TextField(_('corpo'))
    deep_link = models.CharField(
        _('deep link'),
        max_length=500,
        help_text=_('Es. /events/<id> o /assignments/<id>')
    )

    scheduled_at = models.DateTimeField(_('programmata per'))
    channel = models.CharField(
        _('canale'),
        max_length=10,
        choices=Channel.choices,
        default=Channel.BOTH
    )
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    sent_at = models.DateTimeField(_('inviata il'), null=True, blank=True)

    # Cloud Tasks tracking
    cloud_task_name = models.CharField(
        _('nome Cloud Task'),
        max_length=500,
        blank=True,
        help_text=_('Full resource name del task GCP per cancellazione')
    )

    created_at = models.DateTimeField(_('creata il'), auto_now_add=True)
    updated_at = models.DateTimeField(_('aggiornata il'), auto_now=True)

    class Meta:
        verbose_name = _('notifica')
        verbose_name_plural = _('notifiche')
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['section_assignment', 'status']),
        ]
        constraints = [
            # XOR: exactly one source must be set
            models.CheckConstraint(
                check=(
                    models.Q(event__isnull=False, section_assignment__isnull=True) |
                    models.Q(event__isnull=True, section_assignment__isnull=False)
                ),
                name='notification_xor_source'
            ),
        ]

    def __str__(self):
        return f'{self.title} → {self.user.email} ({self.get_status_display()})'

    @property
    def source_type(self):
        """Returns 'event' or 'assignment'."""
        if self.event_id:
            return 'event'
        return 'assignment'

    @property
    def source_object(self):
        """Returns the linked Event or SectionAssignment."""
        if self.event_id:
            return self.event
        return self.section_assignment

    @property
    def is_source_active(self):
        """Check if the linked source is still active."""
        if self.event_id:
            return self.event.status == Event.Status.ACTIVE
        if self.section_assignment_id:
            return self.section_assignment.consultazione.is_attiva
        return False


class DeviceToken(models.Model):
    """
    FCM registration token for push notifications.

    Each device/browser gets a unique token. Tokens are deactivated
    when they become invalid (FCM returns NOT_FOUND or UNREGISTERED).
    """
    class Platform(models.TextChoices):
        WEB = 'WEB', _('Web (PWA)')
        ANDROID = 'ANDROID', _('Android')
        IOS = 'IOS', _('iOS')
        UNKNOWN = 'UNKNOWN', _('Sconosciuto')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name=_('utente')
    )
    token = models.TextField(
        _('token FCM'),
        help_text=_('Firebase Cloud Messaging registration token')
    )
    platform = models.CharField(
        _('piattaforma'),
        max_length=10,
        choices=Platform.choices,
        default=Platform.WEB
    )
    origin = models.CharField(
        _('origin'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('window.location.origin del browser (es. https://ainaudi.it)')
    )
    is_active = models.BooleanField(_('attivo'), default=True)
    last_seen_at = models.DateTimeField(_('ultimo utilizzo'), null=True, blank=True)

    created_at = models.DateTimeField(_('creato il'), auto_now_add=True)
    updated_at = models.DateTimeField(_('aggiornato il'), auto_now=True)

    class Meta:
        verbose_name = _('token dispositivo')
        verbose_name_plural = _('token dispositivi')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'token'],
                name='unique_device_token_per_user'
            ),
        ]

    def __str__(self):
        token_preview = self.token[:20] + '...' if len(self.token) > 20 else self.token
        return f'{self.user.email} - {self.get_platform_display()} ({token_preview})'
