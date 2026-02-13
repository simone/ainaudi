"""
Documents models: PDF generation and templates.

This module will contain:
- TemplateType: Types of templates (DELEGATION, DESIGNATION, etc.)
- Template: PDF templates for delegation forms
- GeneratedDocument: Records of generated PDFs
"""
import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def template_upload_path(instance, filename):
    """
    Generate UUID-based filename for template uploads to avoid conflicts.
    """
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    return os.path.join('templates/', new_filename)


class TemplateType(models.Model):
    """
    Type of template that defines schema, merge mode, and use case.

    Examples:
    - DELEGATION: Delega Sub-Delegato (delegato + subdelegato)
    - DESIGNATION_SINGLE: Designazione RDL Singola (one PDF per section)
    - DESIGNATION_MULTI: Designazione RDL Riepilogativa (multi-page loop)
    """
    code = models.CharField(
        _('codice'),
        max_length=50,
        unique=True,
        help_text=_('Codice identificativo univoco (es: DELEGATION, DESIGNATION_SINGLE)')
    )
    name = models.CharField(
        _('nome'),
        max_length=100,
        help_text=_('Nome visualizzato (es: Delega Sub-Delegato)')
    )
    description = models.TextField(
        _('descrizione'),
        blank=True,
        help_text=_('Descrizione del caso d\'uso')
    )
    default_schema = models.JSONField(
        _('schema predefinito'),
        default=dict,
        help_text=_('Schema JSON di esempio per questo tipo di template')
    )

    # Merge Mode for stampa unione
    class MergeMode(models.TextChoices):
        SINGLE_DOC_PER_RECORD = 'SINGLE_DOC_PER_RECORD', _('Un documento per record')
        MULTI_PAGE_LOOP = 'MULTI_PAGE_LOOP', _('Documento multi-pagina con loop')

    default_merge_mode = models.CharField(
        _('modalità unione predefinita'),
        max_length=25,
        choices=MergeMode.choices,
        default=MergeMode.SINGLE_DOC_PER_RECORD,
        help_text=_('Modalità di generazione documenti per questo tipo')
    )
    use_case = models.TextField(
        _('caso d\'uso'),
        blank=True,
        help_text=_('Quando usare questo tipo di template')
    )
    is_active = models.BooleanField(_('attivo'), default=True)
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('ultimo aggiornamento'), auto_now=True)

    class Meta:
        verbose_name = _('tipo template')
        verbose_name_plural = _('tipi template')
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Template(models.Model):
    """
    PDF template for document generation.
    Linked to a specific ConsultazioneElettorale and TemplateType.

    Templates can be:
    - Generic (owner_email=None): visible to all users
    - Personal (owner_email set): visible only to the owner
    """
    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name=_('consultazione elettorale'),
        help_text=_('Consultazione elettorale a cui appartiene questo template'),
        null=True,
        blank=True
    )
    template_type = models.ForeignKey(
        TemplateType,
        on_delete=models.PROTECT,
        related_name='templates',
        verbose_name=_('tipo template'),
        help_text=_('Tipo di template che definisce schema e modalità unione')
    )
    owner_email = models.EmailField(
        _('proprietario (email)'),
        null=True,
        blank=True,
        help_text=_('Se valorizzato, il template è personale e visibile solo al proprietario. Se null, è generico e visibile a tutti.')
    )
    name = models.CharField(_('nome'), max_length=100)
    description = models.TextField(_('descrizione'), blank=True)
    template_file = models.FileField(
        _('file template'),
        upload_to=template_upload_path,
        null=True,
        blank=True,
        help_text=_('File PDF template (rinominato automaticamente con UUID)')
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

    # Merge Mode (can override template_type default)
    merge_mode = models.CharField(
        _('modalità unione'),
        max_length=25,
        choices=TemplateType.MergeMode.choices,
        blank=True,
        null=True,
        help_text=_('Modalità unione (se vuoto, usa default del template_type)')
    )

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('template')
        ordering = ['consultazione', 'name']
        unique_together = [['consultazione', 'name']]
        indexes = [
            models.Index(fields=['owner_email', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'

    def is_generic(self):
        """Check if template is generic (not owned by anyone)."""
        return not self.owner_email

    def is_owned_by(self, email):
        """Check if template is owned by given email."""
        return self.owner_email == email

    def get_merge_mode(self):
        """Get merge mode, falling back to template_type default."""
        return self.merge_mode or self.template_type.default_merge_mode

    def get_variables_schema(self):
        """Get variables schema from registry (preferred) or template_type DB."""
        from .template_types import get_template_type_class
        type_class = get_template_type_class(self.template_type.code)
        if type_class:
            return type_class.example_schema
        return self.template_type.default_schema


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
