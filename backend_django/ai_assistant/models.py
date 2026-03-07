"""
AI Assistant models: RAG-based chat system.

This module contains:
- KnowledgeSource: Knowledge base documents with vector embeddings
- ChatSession: User chat sessions
- ChatMessage: Individual messages in a session
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField

from core.models import get_user_by_email


class KnowledgeSource(models.Model):
    """
    Source document in the knowledge base.
    """
    class SourceType(models.TextChoices):
        FAQ = 'FAQ', _('FAQ')
        PROCEDURE = 'PROCEDURE', _('Procedura')
        SLIDE = 'SLIDE', _('Slide')
        MANUAL = 'MANUAL', _('Manuale')

    title = models.CharField(_('titolo'), max_length=200)
    source_type = models.CharField(
        _('tipo'),
        max_length=20,
        choices=SourceType.choices
    )
    content = models.TextField(_('contenuto'))
    embedding = VectorField(dimensions=768, null=True, blank=True)  # text-embedding-004

    # Optional reference to source document (for PDF preview links)
    source_url = models.URLField(
        _('URL sorgente'),
        max_length=500,
        blank=True,
        help_text=_('URL del documento PDF originale (per preview)')
    )

    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)
    is_active = models.BooleanField(_('attivo'), default=True)

    class Meta:
        verbose_name = _('fonte conoscenza')
        verbose_name_plural = _('fonti conoscenza')
        ordering = ['source_type', 'title']

    def __str__(self):
        return f'{self.title} ({self.get_source_type_display()})'


class ChatSession(models.Model):
    """
    Chat session with the AI assistant.
    """
    user_email = models.EmailField(_('utente (email)'), default='')
    title = models.CharField(
        _('titolo'),
        max_length=100,
        blank=True,
        help_text=_('Titolo auto-generato dal primo messaggio')
    )
    context = models.CharField(
        _('contesto'),
        max_length=50,
        null=True,
        blank=True,
        help_text=_('es. SCRUTINY, INCIDENT')
    )
    sezione = models.ForeignKey(
        'territory.SezioneElettorale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_sessions',
        verbose_name=_('sezione')
    )
    parent_session = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches',
        verbose_name=_('sessione parent'),
        help_text=_('Sessione da cui è stato fatto il branch (edit messaggio)')
    )
    metadata = models.JSONField(
        _('metadati'),
        default=dict,
        blank=True,
        help_text=_('Dati aggiuntivi per funzionalità agentiche (es. pending_incident)')
    )
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('sessione chat')
        verbose_name_plural = _('sessioni chat')
        ordering = ['-updated_at']

    def __str__(self):
        return f'Chat {self.id} - {self.user_email}'

    @property
    def user(self):
        """Restituisce l'utente della sessione."""
        return get_user_by_email(self.user_email)


class ChatMessage(models.Model):
    """
    Individual message in a chat session.
    """
    class Role(models.TextChoices):
        USER = 'user', _('Utente')
        ASSISTANT = 'assistant', _('Assistente')

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('sessione')
    )
    role = models.CharField(
        _('ruolo'),
        max_length=20,
        choices=Role.choices
    )
    content = models.TextField(_('contenuto'))
    sources_cited = models.JSONField(
        _('fonti citate'),
        null=True,
        blank=True,
        help_text=_('IDs delle fonti usate nella risposta')
    )
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)

    class Meta:
        verbose_name = _('messaggio chat')
        verbose_name_plural = _('messaggi chat')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_role_display()}: {self.content[:50]}...'


class ChatAttachment(models.Model):
    """
    File attachment on a chat message (image, audio, document).
    Used for multimodal AI processing (Gemini vision/audio).
    """
    class FileType(models.TextChoices):
        IMAGE = 'IMAGE', _('Immagine')
        AUDIO = 'AUDIO', _('Audio')
        DOCUMENT = 'DOCUMENT', _('Documento')

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('messaggio')
    )
    file = models.FileField(
        _('file'),
        upload_to='chat_attachments/%Y/%m/%d/'
    )
    file_type = models.CharField(
        _('tipo file'),
        max_length=20,
        choices=FileType.choices
    )
    mime_type = models.CharField(_('MIME type'), max_length=100)
    filename = models.CharField(_('nome file'), max_length=255)
    file_size = models.IntegerField(_('dimensione (bytes)'))
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)

    class Meta:
        verbose_name = _('allegato chat')
        verbose_name_plural = _('allegati chat')

    def __str__(self):
        return f'{self.filename} ({self.get_file_type_display()})'

    @staticmethod
    def detect_file_type(mime_type):
        """Detect FileType from MIME type."""
        if mime_type.startswith('image/'):
            return ChatAttachment.FileType.IMAGE
        if mime_type.startswith('audio/'):
            return ChatAttachment.FileType.AUDIO
        return ChatAttachment.FileType.DOCUMENT

    # Supported MIME types for Gemini multimodal
    SUPPORTED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    SUPPORTED_AUDIO_TYPES = {'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/aac', 'audio/flac', 'audio/mp4', 'audio/x-m4a'}
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
