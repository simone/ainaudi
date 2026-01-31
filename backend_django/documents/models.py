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
    """
    class TemplateType(models.TextChoices):
        SCRUTINY = 'SCRUTINY', _('Scrutinio')
        INCIDENT = 'INCIDENT', _('Segnalazione')
        DELEGATION = 'DELEGATION', _('Delega')

    name = models.CharField(_('nome'), max_length=100, unique=True)
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

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('template')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} v{self.version}'


class GeneratedDocument(models.Model):
    """
    Record of a generated PDF document.
    """
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

    class Meta:
        verbose_name = _('documento generato')
        verbose_name_plural = _('documenti generati')
        ordering = ['-generated_at']

    def __str__(self):
        return f'Doc #{self.id} - {self.template.name if self.template else "No template"}'
