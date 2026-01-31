"""
Incidents models: Report and track incidents during elections.

This module defines:
- IncidentReport: Main incident report
- IncidentComment: Comments on incidents
- IncidentAttachment: Attachments (photos, documents)
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class IncidentReport(models.Model):
    """
    Report of an incident during an election.
    """
    class Category(models.TextChoices):
        PROCEDURAL = 'PROCEDURAL', _('Procedurale')
        ACCESS = 'ACCESS', _('Accesso al seggio')
        MATERIALS = 'MATERIALS', _('Materiali')
        INTIMIDATION = 'INTIMIDATION', _('Intimidazione')
        IRREGULARITY = 'IRREGULARITY', _('Irregolarità')
        TECHNICAL = 'TECHNICAL', _('Tecnico')
        OTHER = 'OTHER', _('Altro')

    class Severity(models.TextChoices):
        LOW = 'LOW', _('Bassa')
        MEDIUM = 'MEDIUM', _('Media')
        HIGH = 'HIGH', _('Alta')
        CRITICAL = 'CRITICAL', _('Critica')

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Aperta')
        IN_PROGRESS = 'IN_PROGRESS', _('In corso')
        RESOLVED = 'RESOLVED', _('Risolta')
        CLOSED = 'CLOSED', _('Chiusa')
        ESCALATED = 'ESCALATED', _('Escalata')

    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='incidents',
        verbose_name=_('consultazione')
    )
    sezione = models.ForeignKey(
        'territorio.SezioneElettorale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents',
        verbose_name=_('sezione')
    )

    # Reporter
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_incidents',
        verbose_name=_('segnalante')
    )

    # Classification
    category = models.CharField(
        _('categoria'),
        max_length=20,
        choices=Category.choices
    )
    severity = models.CharField(
        _('gravità'),
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM
    )
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    # Content
    title = models.CharField(_('titolo'), max_length=200)
    description = models.TextField(
        _('descrizione'),
        help_text=_('Descrizione dettagliata dell\'incidente')
    )

    # When it happened
    occurred_at = models.DateTimeField(
        _('data/ora incidente'),
        null=True,
        blank=True,
        help_text=_('Quando è avvenuto l\'incidente')
    )

    # Resolution
    resolution = models.TextField(
        _('risoluzione'),
        null=True,
        blank=True,
        help_text=_('Come è stato risolto l\'incidente')
    )
    resolved_at = models.DateTimeField(_('data risoluzione'), null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_incidents',
        verbose_name=_('risolto da')
    )

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_incidents',
        verbose_name=_('assegnato a')
    )

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('segnalazione')
        verbose_name_plural = _('segnalazioni')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consultazione', 'status']),
            models.Index(fields=['sezione', 'status']),
            models.Index(fields=['reporter', 'created_at']),
            models.Index(fields=['category', 'severity']),
        ]

    def __str__(self):
        return f'#{self.id} - {self.title}'

    @property
    def location_description(self):
        """Human-readable location description."""
        if self.sezione:
            return f'Sezione {self.sezione.numero} - {self.sezione.comune.nome}'
        return _('Non specificata')


class IncidentComment(models.Model):
    """
    Comment on an incident report.
    """
    incident = models.ForeignKey(
        IncidentReport,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('segnalazione')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incident_comments',
        verbose_name=_('autore')
    )
    content = models.TextField(_('contenuto'))
    is_internal = models.BooleanField(
        _('interno'),
        default=False,
        help_text=_('Se True, visibile solo agli operatori')
    )
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)

    class Meta:
        verbose_name = _('commento')
        verbose_name_plural = _('commenti')
        ordering = ['created_at']

    def __str__(self):
        return f'Commento di {self.author.email} su #{self.incident.id}'


class IncidentAttachment(models.Model):
    """
    Attachment to an incident report (photo, document, etc.).
    """
    class FileType(models.TextChoices):
        IMAGE = 'IMAGE', _('Immagine')
        DOCUMENT = 'DOCUMENT', _('Documento')
        VIDEO = 'VIDEO', _('Video')
        OTHER = 'OTHER', _('Altro')

    incident = models.ForeignKey(
        IncidentReport,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('segnalazione')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='incident_attachments',
        verbose_name=_('caricato da')
    )

    file = models.FileField(
        _('file'),
        upload_to='incidents/%Y/%m/%d/'
    )
    file_type = models.CharField(
        _('tipo file'),
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER
    )
    filename = models.CharField(_('nome file'), max_length=255)
    file_size = models.IntegerField(_('dimensione'), help_text=_('In bytes'))
    description = models.CharField(
        _('descrizione'),
        max_length=255,
        blank=True
    )

    uploaded_at = models.DateTimeField(_('data caricamento'), auto_now_add=True)

    class Meta:
        verbose_name = _('allegato')
        verbose_name_plural = _('allegati')
        ordering = ['uploaded_at']

    def __str__(self):
        return f'{self.filename} - #{self.incident.id}'

    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size

            # Detect file type
            ext = self.filename.lower().split('.')[-1] if '.' in self.filename else ''
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                self.file_type = self.FileType.IMAGE
            elif ext in ['pdf', 'doc', 'docx', 'txt']:
                self.file_type = self.FileType.DOCUMENT
            elif ext in ['mp4', 'mov', 'avi', 'webm']:
                self.file_type = self.FileType.VIDEO

        super().save(*args, **kwargs)
