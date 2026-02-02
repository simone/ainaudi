"""
Resources models: Documents and FAQ with scope-based filtering.

Documents and FAQ can be scoped to specific election types (Referendum, Comunali, etc.)
or to a specific consultation.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ScopeChoices(models.TextChoices):
    """Scope per documenti e FAQ - determina in quali consultazioni sono visibili."""
    TUTTI = 'TUTTI', _('Tutte le consultazioni')
    REFERENDUM = 'REFERENDUM', _('Solo Referendum')
    COMUNALI = 'COMUNALI', _('Solo Comunali')
    REGIONALI = 'REGIONALI', _('Solo Regionali')
    POLITICHE = 'POLITICHE', _('Solo Politiche')
    EUROPEE = 'EUROPEE', _('Solo Europee')
    SPECIFICO = 'SPECIFICO', _('Consultazione specifica')


class RisorsaManager(models.Manager):
    """Manager per filtrare risorse in base alla consultazione attiva."""

    def per_consultazione(self, consultazione):
        """
        Filtra risorse visibili per la consultazione data.

        Logica:
        - TUTTI: sempre visibile
        - SPECIFICO: solo se consultazione_specifica corrisponde
        - REFERENDUM/COMUNALI/etc: visibile se la consultazione ha quel tipo
        """
        if not consultazione:
            # Senza consultazione, mostra solo TUTTI
            return self.filter(scope=ScopeChoices.TUTTI, is_attivo=True)

        from elections.models import TipoElezione

        # Determina i tipi di elezione nella consultazione
        tipi_elezione = list(
            consultazione.tipi_elezione.values_list('tipo', flat=True)
        )

        # Mapping scope -> tipo elezione
        scope_to_tipo = {
            ScopeChoices.REFERENDUM: 'REFERENDUM',
            ScopeChoices.COMUNALI: 'COMUNALI',
            ScopeChoices.REGIONALI: 'REGIONALI',
            ScopeChoices.POLITICHE: ['POLITICHE_CAMERA', 'POLITICHE_SENATO'],
            ScopeChoices.EUROPEE: 'EUROPEE',
        }

        # Costruisci filtro Q
        from django.db.models import Q

        q = Q(scope=ScopeChoices.TUTTI)  # TUTTI sempre visibile
        q |= Q(scope=ScopeChoices.SPECIFICO, consultazione_specifica=consultazione)

        for scope, tipo in scope_to_tipo.items():
            if isinstance(tipo, list):
                if any(t in tipi_elezione for t in tipo):
                    q |= Q(scope=scope)
            elif tipo in tipi_elezione:
                q |= Q(scope=scope)

        return self.filter(q, is_attivo=True)


# =============================================================================
# DOCUMENTI
# =============================================================================

class CategoriaDocumento(models.Model):
    """Categoria per organizzare i documenti (es. Modulistica, Guide, Normativa)."""
    nome = models.CharField(_('nome'), max_length=100)
    descrizione = models.TextField(_('descrizione'), blank=True)
    icona = models.CharField(
        _('icona FontAwesome'),
        max_length=50,
        default='fa-folder',
        help_text=_('Classe FontAwesome (es. fa-file-pdf, fa-book)')
    )
    ordine = models.IntegerField(_('ordine'), default=0)
    is_attiva = models.BooleanField(_('attiva'), default=True)

    class Meta:
        verbose_name = _('categoria documento')
        verbose_name_plural = _('categorie documenti')
        ordering = ['ordine', 'nome']

    def __str__(self):
        return self.nome


class Documento(models.Model):
    """
    Documento scaricabile (PDF, Word, Excel, etc.).
    Filtrato per scope in base alla consultazione attiva.
    """
    titolo = models.CharField(_('titolo'), max_length=200)
    descrizione = models.TextField(_('descrizione'), blank=True)
    categoria = models.ForeignKey(
        CategoriaDocumento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documenti',
        verbose_name=_('categoria')
    )

    # File (uno dei due: file caricato o URL esterno)
    file = models.FileField(
        _('file'),
        upload_to='documenti/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('File caricato. Alternativa a URL esterno.')
    )
    url_esterno = models.URLField(
        _('URL esterno'),
        max_length=500,
        blank=True,
        help_text=_('Link a documento esterno (es. Ministero). Alternativa a file caricato.')
    )
    tipo_file = models.CharField(
        _('tipo file'),
        max_length=20,
        blank=True,
        help_text=_('Determinato automaticamente dal file o dall\'URL')
    )
    dimensione = models.BigIntegerField(_('dimensione (bytes)'), default=0)

    # Scope
    scope = models.CharField(
        _('visibilità'),
        max_length=20,
        choices=ScopeChoices.choices,
        default=ScopeChoices.TUTTI,
        help_text=_('Determina in quali consultazioni il documento è visibile')
    )
    consultazione_specifica = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documenti_specifici',
        verbose_name=_('consultazione specifica'),
        help_text=_('Solo se scope = SPECIFICO')
    )

    # Visibilità
    is_pubblico = models.BooleanField(
        _('pubblico'),
        default=True,
        help_text=_('Se False, visibile solo a utenti autenticati')
    )
    in_evidenza = models.BooleanField(
        _('in evidenza'),
        default=False,
        help_text=_('Mostrato in cima alla lista')
    )
    is_attivo = models.BooleanField(_('attivo'), default=True)
    ordine = models.IntegerField(_('ordine'), default=0)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documenti_creati',
        verbose_name=_('creato da')
    )

    objects = RisorsaManager()

    class Meta:
        verbose_name = _('documento')
        verbose_name_plural = _('documenti')
        ordering = ['-in_evidenza', 'ordine', '-created_at']

    def __str__(self):
        return self.titolo

    def save(self, *args, **kwargs):
        # Determina tipo file dall'estensione (file o URL)
        source = self.file.name if self.file else self.url_esterno
        if source:
            # Estrai estensione, rimuovi query params
            ext = source.split('.')[-1].lower().split('?')[0].split('#')[0]
            # Solo estensioni valide (corte)
            if len(ext) > 5 or '/' in ext:
                ext = ''
            tipo_map = {
                'pdf': 'PDF',
                'doc': 'Word',
                'docx': 'Word',
                'xls': 'Excel',
                'xlsx': 'Excel',
                'ppt': 'PowerPoint',
                'pptx': 'PowerPoint',
                'zip': 'ZIP',
                'rar': 'ZIP',
            }
            self.tipo_file = tipo_map.get(ext, 'LINK')

        # Dimensione file (solo per file caricati)
        if self.file and hasattr(self.file, 'size'):
            self.dimensione = self.file.size

        super().save(*args, **kwargs)

    @property
    def download_url(self):
        """URL per scaricare il documento (file caricato o URL esterno)."""
        if self.url_esterno:
            return self.url_esterno
        elif self.file:
            return self.file.url
        return None

    @property
    def dimensione_formattata(self):
        """Formatta la dimensione in KB/MB."""
        if self.dimensione < 1024:
            return f'{self.dimensione} B'
        elif self.dimensione < 1024 * 1024:
            return f'{self.dimensione / 1024:.0f} KB'
        else:
            return f'{self.dimensione / (1024 * 1024):.1f} MB'


# =============================================================================
# FAQ
# =============================================================================

class CategoriaFAQ(models.Model):
    """Categoria per organizzare le FAQ (es. Operazioni di voto, Scrutinio, App)."""
    nome = models.CharField(_('nome'), max_length=100)
    descrizione = models.TextField(_('descrizione'), blank=True)
    icona = models.CharField(
        _('icona FontAwesome'),
        max_length=50,
        default='fa-question-circle',
        help_text=_('Classe FontAwesome (es. fa-vote-yea, fa-calculator)')
    )
    ordine = models.IntegerField(_('ordine'), default=0)
    is_attiva = models.BooleanField(_('attiva'), default=True)

    class Meta:
        verbose_name = _('categoria FAQ')
        verbose_name_plural = _('categorie FAQ')
        ordering = ['ordine', 'nome']

    def __str__(self):
        return self.nome


class FAQ(models.Model):
    """
    Domanda frequente con risposta.
    Filtrata per scope in base alla consultazione attiva.
    """
    domanda = models.CharField(_('domanda'), max_length=500)
    risposta = models.TextField(_('risposta'))
    categoria = models.ForeignKey(
        CategoriaFAQ,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faqs',
        verbose_name=_('categoria')
    )

    # Scope
    scope = models.CharField(
        _('visibilità'),
        max_length=20,
        choices=ScopeChoices.choices,
        default=ScopeChoices.TUTTI,
        help_text=_('Determina in quali consultazioni la FAQ è visibile')
    )
    consultazione_specifica = models.ForeignKey(
        'elections.ConsultazioneElettorale',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='faq_specifiche',
        verbose_name=_('consultazione specifica'),
        help_text=_('Solo se scope = SPECIFICO')
    )

    # Visibilità
    is_pubblico = models.BooleanField(
        _('pubblico'),
        default=True,
        help_text=_('Se False, visibile solo a utenti autenticati')
    )
    in_evidenza = models.BooleanField(
        _('in evidenza'),
        default=False,
        help_text=_('Mostrata in cima alla lista')
    )
    is_attivo = models.BooleanField(_('attivo'), default=True)
    ordine = models.IntegerField(_('ordine'), default=0)

    # Statistiche
    visualizzazioni = models.PositiveIntegerField(_('visualizzazioni'), default=0)
    utile_si = models.PositiveIntegerField(_('voti utile: sì'), default=0)
    utile_no = models.PositiveIntegerField(_('voti utile: no'), default=0)

    # Audit
    created_at = models.DateTimeField(_('data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('data modifica'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faq_create',
        verbose_name=_('creato da')
    )

    objects = RisorsaManager()

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQ')
        ordering = ['-in_evidenza', 'categoria__ordine', 'ordine', '-created_at']

    def __str__(self):
        return self.domanda[:60] + ('...' if len(self.domanda) > 60 else '')

    def incrementa_visualizzazioni(self):
        """Incrementa contatore visualizzazioni."""
        self.visualizzazioni += 1
        self.save(update_fields=['visualizzazioni'])

    def vota_utile(self, utile: bool):
        """Registra voto utile sì/no."""
        if utile:
            self.utile_si += 1
        else:
            self.utile_no += 1
        self.save(update_fields=['utile_si', 'utile_no'])

    @property
    def percentuale_utile(self):
        """Percentuale di voti 'utile: sì'."""
        totale = self.utile_si + self.utile_no
        if totale == 0:
            return None
        return round(self.utile_si / totale * 100)
