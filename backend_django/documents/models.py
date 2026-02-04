"""
Documents models: PDF generation and templates.

This module will contain:
- Template: PDF templates for delegation forms
- GeneratedDocument: Records of generated PDFs
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Template(models.Model):
    """
    PDF template for document generation.
    Linked to a specific ConsultazioneElettorale.
    """
    class TemplateType(models.TextChoices):
        DELEGATION  = 'DELEGATION', _('Delega Sub-Delegato')
        DESIGNATION = 'DESIGNATION', _('Designazione RDL')

    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name=_('consultazione elettorale'),
        help_text=_('Consultazione elettorale a cui appartiene questo template'),
        null=True,
        blank=True
    )
    name = models.CharField(_('nome'), max_length=100)
    template_type = models.CharField(
        _('tipo template'),
        max_length=20,
        choices=TemplateType.choices
    )
    description = models.TextField(_('descrizione'), blank=True)
    template_file = models.FileField(
        _('file template'),
        upload_to='templates/',
        null=True,
        blank=True
    )
    variables_schema = models.JSONField(
        _('schema variabili'),
        default=dict,
        help_text=_('Schema JSON delle variabili accettate')
    )
    is_active = models.BooleanField(_('attivo'), default=True)
    version = models.IntegerField(_('versione'), default=1)
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    # Template Editor Fields
    field_mappings = models.JSONField(
        _('mappatura campi'),
        default=list,
        help_text=_('Lista di {area: {x, y, width, height}, jsonpath: "$.field", type: "text|loop"}')
    )
    loop_config = models.JSONField(
        _('configurazione loop'),
        default=dict,
        null=True,
        blank=True,
        help_text=_('Configurazione loop: {type: "single|multi_page", rows_first_page: N, rows_per_page: M, data_source: "$.path"}')
    )

    # Merge Mode for stampa unione
    class MergeMode(models.TextChoices):
        SINGLE_DOC_PER_RECORD = 'SINGLE_DOC_PER_RECORD', _('Un documento per record')
        MULTI_PAGE_LOOP = 'MULTI_PAGE_LOOP', _('Documento multi-pagina con loop')

    merge_mode = models.CharField(
        _('modalità unione'),
        max_length=25,
        choices=MergeMode.choices,
        default=MergeMode.SINGLE_DOC_PER_RECORD
    )

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('template')
        ordering = ['consultazione', 'name']
        unique_together = [['consultazione', 'name']]

    def __str__(self):
        return f'{self.name} v{self.version}'


class GeneratedDocument(models.Model):
    """
    Record of a generated PDF document with preview/confirm workflow.
    """
    class Status(models.TextChoices):
        PREVIEW = 'PREVIEW', _('Preview (pending confirmation)')
        CONFIRMED = 'CONFIRMED', _('Confirmed (immutable)')
        EXPIRED = 'EXPIRED', _('Expired (never confirmed)')
        CANCELLED = 'CANCELLED', _('Cancelled by user')

    template = models.ForeignKey(
        Template,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_documents',
        verbose_name=_('template')
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_documents',
        verbose_name=_('generato da')
    )
    input_data = models.JSONField(
        _('dati input'),
        default=dict,
        help_text=_('Dati usati per generare il documento')
    )
    pdf_file = models.FileField(
        _('file PDF'),
        upload_to='generated/%Y/%m/',
        null=True,
        blank=True
    )
    pdf_url = models.URLField(_('URL PDF'), null=True, blank=True)
    generated_at = models.DateTimeField(_('data generazione'), auto_now_add=True)

    # State Machine Fields
    status = models.CharField(
        _('stato'),
        max_length=10,
        choices=Status.choices,
        default=Status.PREVIEW
    )
    review_token = models.CharField(
        _('token revisione'),
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    preview_expires_at = models.DateTimeField(
        _('scadenza preview'),
        null=True,
        blank=True
    )
    confirmed_at = models.DateTimeField(
        _('data conferma'),
        null=True,
        blank=True
    )
    confirmation_ip = models.GenericIPAddressField(
        _('IP conferma'),
        null=True,
        blank=True
    )
    event_id = models.CharField(
        _('ID evento'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_('ID evento Redis per audit trail')
    )

    class Meta:
        verbose_name = _('documento generato')
        verbose_name_plural = _('documenti generati')
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['review_token']),
            models.Index(fields=['status', 'preview_expires_at']),
        ]

    def __str__(self):
        return f'Doc #{self.id} - {self.template.name if self.template else "No template"} [{self.status}]'
