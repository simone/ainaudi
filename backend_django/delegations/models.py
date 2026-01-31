"""
Delegations models: Hierarchical delegation management.

This module defines:
- DelegationRelationship: Principal-delegate relationships
- FreezeBatch: Snapshot of delegation state at a point in time
- ProxyDelegationDocument: PDF documents for delegation
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DelegationRelationship(models.Model):
    """
    Relationship between a principal (delegator) and a delegate.
    Supports hierarchical delegation: DELEGATE > SUBDELEGATE > RDL
    """
    class RelationshipType(models.TextChoices):
        ADMIN_TO_DELEGATE = 'ADMIN_TO_DELEGATE', _('Admin → Delegato')
        DELEGATE_TO_SUBDELEGATE = 'DELEGATE_TO_SUBDELEGATE', _('Delegato → Sub-delegato')
        SUBDELEGATE_TO_RDL = 'SUBDELEGATE_TO_RDL', _('Sub-delegato → RDL')
        DIRECT_TO_RDL = 'DIRECT_TO_RDL', _('Diretto → RDL')

    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='delegation_relationships',
        verbose_name=_('consultazione')
    )
    principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_given',
        verbose_name=_('delegante'),
        help_text=_('Chi conferisce la delega')
    )
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_received',
        verbose_name=_('delegato'),
        help_text=_('Chi riceve la delega')
    )
    relationship_type = models.CharField(
        _('tipo relazione'),
        max_length=30,
        choices=RelationshipType.choices
    )

    # Scope: what the delegate can do
    scope_regione = models.ForeignKey(
        'territorio.Regione',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegation_relationships',
        verbose_name=_('regione')
    )
    scope_provincia = models.ForeignKey(
        'territorio.Provincia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegation_relationships',
        verbose_name=_('provincia')
    )
    scope_comune = models.ForeignKey(
        'territorio.Comune',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegation_relationships',
        verbose_name=_('comune')
    )
    scope_municipio = models.ForeignKey(
        'territorio.Municipio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegation_relationships',
        verbose_name=_('municipio')
    )

    # Validity period
    valid_from = models.DateTimeField(
        _('valido da'),
        help_text=_('Data inizio validità')
    )
    valid_to = models.DateTimeField(
        _('valido fino a'),
        null=True,
        blank=True,
        help_text=_('Data fine validità (opzionale)')
    )
    is_active = models.BooleanField(_('attiva'), default=True)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegations_created',
        verbose_name=_('creato da')
    )
    revoked_at = models.DateTimeField(_('data revoca'), null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegations_revoked',
        verbose_name=_('revocato da')
    )
    notes = models.TextField(_('note'), blank=True)

    class Meta:
        verbose_name = _('relazione di delega')
        verbose_name_plural = _('relazioni di delega')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['principal', 'consultazione']),
            models.Index(fields=['delegate', 'consultazione']),
            models.Index(fields=['relationship_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.principal.email} → {self.delegate.email} ({self.get_relationship_type_display()})'

    @property
    def scope_description(self):
        """Human-readable description of the scope."""
        if self.scope_municipio:
            return f'{self.scope_municipio}'
        if self.scope_comune:
            return f'{self.scope_comune}'
        if self.scope_provincia:
            return f'{self.scope_provincia}'
        if self.scope_regione:
            return f'{self.scope_regione}'
        return _('Nazionale')


class FreezeBatch(models.Model):
    """
    Snapshot of delegation state at a point in time.
    Used to "freeze" the current state before generating official documents.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Bozza')
        FROZEN = 'FROZEN', _('Congelato')
        APPROVED = 'APPROVED', _('Approvato')
        SENT = 'SENT', _('Inviato')

    consultazione = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        related_name='freeze_batches',
        verbose_name=_('consultazione')
    )
    name = models.CharField(
        _('nome'),
        max_length=100,
        help_text=_('es. "Freeze Roma 15/05/2025"')
    )
    description = models.TextField(_('descrizione'), blank=True)
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Scope (what this batch covers)
    scope_regione = models.ForeignKey(
        'territorio.Regione',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='freeze_batches',
        verbose_name=_('regione')
    )
    scope_provincia = models.ForeignKey(
        'territorio.Provincia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='freeze_batches',
        verbose_name=_('provincia')
    )
    scope_comune = models.ForeignKey(
        'territorio.Comune',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='freeze_batches',
        verbose_name=_('comune')
    )

    # Snapshot data
    snapshot_data = models.JSONField(
        _('dati snapshot'),
        default=dict,
        help_text=_('Stato congelato delle deleghe e assegnazioni')
    )
    frozen_at = models.DateTimeField(_('data congelamento'), null=True, blank=True)

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='freeze_batches_created',
        verbose_name=_('creato da')
    )
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='freeze_batches_approved',
        verbose_name=_('approvato da')
    )
    approved_at = models.DateTimeField(_('data approvazione'), null=True, blank=True)

    class Meta:
        verbose_name = _('batch congelamento')
        verbose_name_plural = _('batch congelamenti')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    @property
    def scope_description(self):
        """Human-readable description of the scope."""
        if self.scope_comune:
            return f'{self.scope_comune}'
        if self.scope_provincia:
            return f'{self.scope_provincia}'
        if self.scope_regione:
            return f'{self.scope_regione}'
        return _('Nazionale')


class ProxyDelegationDocument(models.Model):
    """
    PDF document generated for proxy delegation.
    Can be individual (one person) or summary (multiple people).
    """
    class DocumentType(models.TextChoices):
        INDIVIDUALE = 'INDIVIDUALE', _('Individuale')
        RIEPILOGATIVO = 'RIEPILOGATIVO', _('Riepilogativo')

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Bozza')
        READY = 'READY', _('Pronto')
        APPROVED = 'APPROVED', _('Approvato')
        SENT = 'SENT', _('Inviato')

    freeze_batch = models.ForeignKey(
        FreezeBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('batch')
    )
    delegation = models.ForeignKey(
        DelegationRelationship,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('delega'),
        help_text=_('Per documenti individuali')
    )

    document_type = models.CharField(
        _('tipo documento'),
        max_length=20,
        choices=DocumentType.choices
    )
    status = models.CharField(
        _('stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # PDF storage
    pdf_file = models.FileField(
        _('file PDF'),
        upload_to='deleghe/%Y/%m/',
        null=True,
        blank=True
    )
    pdf_url = models.URLField(
        _('URL PDF'),
        null=True,
        blank=True,
        help_text=_('URL su Cloud Storage')
    )

    # Template data (for regeneration)
    template_data = models.JSONField(
        _('dati template'),
        null=True,
        blank=True,
        help_text=_('Dati usati per generare il PDF')
    )

    # Audit
    generated_at = models.DateTimeField(_('data generazione'), null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_generated',
        verbose_name=_('generato da')
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_approved',
        verbose_name=_('approvato da')
    )
    approved_at = models.DateTimeField(_('data approvazione'), null=True, blank=True)
    sent_at = models.DateTimeField(_('data invio'), null=True, blank=True)

    class Meta:
        verbose_name = _('documento delega')
        verbose_name_plural = _('documenti delega')
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.get_document_type_display()} - {self.get_status_display()}'
