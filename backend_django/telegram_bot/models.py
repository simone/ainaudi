"""
Telegram Bot models: identity binding, update log, conversation link.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TelegramIdentityBinding(models.Model):
    """
    Persistent association between a Telegram user and an internal Ainaudi user.
    Only one ACTIVE binding per telegram_user_id and per internal user at a time.
    """
    class BindingStatus(models.TextChoices):
        PENDING = 'PENDING', _('In attesa')
        ACTIVE = 'ACTIVE', _('Attivo')
        REVOKED = 'REVOKED', _('Revocato')
        BLOCKED = 'BLOCKED', _('Bloccato')

    telegram_user_id = models.BigIntegerField(
        _('Telegram user ID'),
        db_index=True,
    )
    telegram_chat_id = models.BigIntegerField(
        _('Telegram chat ID'),
    )
    phone_number_normalized = models.CharField(
        _('numero telefono normalizzato'),
        max_length=20,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_bindings',
        verbose_name=_('utente'),
    )
    binding_status = models.CharField(
        _('stato binding'),
        max_length=10,
        choices=BindingStatus.choices,
        default=BindingStatus.PENDING,
    )
    first_bound_at = models.DateTimeField(_('primo binding'), null=True, blank=True)
    last_seen_at = models.DateTimeField(_('ultimo messaggio'), null=True, blank=True)
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('binding Telegram')
        verbose_name_plural = _('binding Telegram')
        constraints = [
            models.UniqueConstraint(
                fields=['telegram_user_id'],
                condition=models.Q(binding_status='ACTIVE'),
                name='unique_active_telegram_user',
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(binding_status='ACTIVE'),
                name='unique_active_internal_user',
            ),
        ]
        indexes = [
            models.Index(fields=['telegram_user_id', 'binding_status']),
            models.Index(fields=['user', 'binding_status']),
        ]

    def __str__(self):
        return f'TG:{self.telegram_user_id} → {self.user.email} ({self.binding_status})'


class TelegramUpdateLog(models.Model):
    """
    Idempotency log: tracks processed Telegram updates to prevent double processing.
    """
    class ProcessingStatus(models.TextChoices):
        OK = 'OK', _('Elaborato')
        ERROR = 'ERROR', _('Errore')
        SKIPPED = 'SKIPPED', _('Ignorato')

    update_id = models.BigIntegerField(
        _('Telegram update ID'),
        unique=True,
    )
    telegram_user_id = models.BigIntegerField(
        _('Telegram user ID'),
        null=True,
        blank=True,
    )
    chat_id = models.BigIntegerField(
        _('chat ID'),
        null=True,
        blank=True,
    )
    update_type = models.CharField(
        _('tipo update'),
        max_length=30,
    )
    processing_status = models.CharField(
        _('stato elaborazione'),
        max_length=10,
        choices=ProcessingStatus.choices,
    )
    error_message = models.TextField(
        _('messaggio errore'),
        blank=True,
    )
    processed_at = models.DateTimeField(_('elaborato il'), auto_now_add=True)

    class Meta:
        verbose_name = _('log update Telegram')
        verbose_name_plural = _('log update Telegram')
        ordering = ['-processed_at']

    def __str__(self):
        return f'Update {self.update_id} ({self.processing_status})'


class ExternalChannelConversationLink(models.Model):
    """
    Links a Telegram chat to an internal ChatSession for conversation continuity.
    """
    channel = models.CharField(
        _('canale'),
        max_length=20,
        default='telegram',
    )
    telegram_chat_id = models.BigIntegerField(_('Telegram chat ID'))
    telegram_user_id = models.BigIntegerField(_('Telegram user ID'))
    conversation = models.ForeignKey(
        'ai_assistant.ChatSession',
        on_delete=models.CASCADE,
        related_name='external_links',
        verbose_name=_('sessione chat'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='external_conversation_links',
        verbose_name=_('utente'),
    )
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('link conversazione esterna')
        verbose_name_plural = _('link conversazioni esterne')
        indexes = [
            models.Index(fields=['channel', 'telegram_chat_id', 'telegram_user_id']),
        ]

    def __str__(self):
        return f'{self.channel}:{self.telegram_chat_id} → session:{self.conversation_id}'
