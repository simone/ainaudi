"""
Territorio models: Italian administrative divisions.

This module defines the Italian administrative hierarchy:
- Regione (20 regions)
- Provincia (107 provinces / metropolitan cities)
- Comune (7896 municipalities)
- Municipio (city districts, for large cities like Rome)
- SezioneElettorale (electoral sections, 500-1200 voters each)

Data sources:
- ISTAT: https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class Regione(models.Model):
    """
    Italian regions (20 total).
    5 regions have special statute (statuto speciale).
    """
    codice_istat = models.CharField(
        _('codice ISTAT'),
        max_length=2,
        unique=True,
        help_text=_('Codice ISTAT a 2 cifre (es. "12" per Lazio)')
    )
    nome = models.CharField(_('nome'), max_length=100)
    statuto_speciale = models.BooleanField(
        _('statuto speciale'),
        default=False,
        help_text=_('Regione a statuto speciale')
    )

    class Meta:
        verbose_name = _('regione')
        verbose_name_plural = _('regioni')
        ordering = ['codice_istat']

    def __str__(self):
        return self.nome


class Provincia(models.Model):
    """
    Italian provinces / Metropolitan cities.
    107 provinces as of 2024.
    """
    regione = models.ForeignKey(
        Regione,
        on_delete=models.CASCADE,
        related_name='province',
        verbose_name=_('regione')
    )
    codice_istat = models.CharField(
        _('codice ISTAT'),
        max_length=3,
        unique=True,
        help_text=_('Codice ISTAT a 3 cifre')
    )
    sigla = models.CharField(
        _('sigla'),
        max_length=2,
        help_text=_('Sigla automobilistica (es. "RM")')
    )
    nome = models.CharField(_('nome'), max_length=100)
    is_citta_metropolitana = models.BooleanField(
        _('città metropolitana'),
        default=False
    )

    class Meta:
        verbose_name = _('provincia')
        verbose_name_plural = _('province')
        ordering = ['regione__codice_istat', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.sigla})'


class Comune(models.Model):
    """
    Italian municipalities (comuni).
    7896 municipalities as of January 2024.
    """
    provincia = models.ForeignKey(
        Provincia,
        on_delete=models.CASCADE,
        related_name='comuni',
        verbose_name=_('provincia')
    )
    codice_istat = models.CharField(
        _('codice ISTAT'),
        max_length=6,
        unique=True,
        help_text=_('Codice ISTAT a 6 cifre')
    )
    codice_catastale = models.CharField(
        _('codice catastale'),
        max_length=4,
        unique=True,
        help_text=_('Codice Belfiore/catastale')
    )
    nome = models.CharField(_('nome'), max_length=100)
    popolazione = models.IntegerField(
        _('popolazione'),
        null=True,
        blank=True,
        help_text=_('Popolazione residente (per determinare sistema elettorale)')
    )
    cap = models.CharField(
        _('CAP'),
        max_length=5,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('comune')
        verbose_name_plural = _('comuni')
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.provincia.sigla})'

    @property
    def sistema_elettorale_comunali(self):
        """Determine electoral system based on population."""
        if self.popolazione is None:
            return None
        if self.popolazione < 15000:
            return 'turno_unico'
        return 'doppio_turno'


class Municipio(models.Model):
    """
    Municipal districts (for large cities like Rome, Milan, etc.).
    Sub-divisions of large municipalities.
    """
    comune = models.ForeignKey(
        Comune,
        on_delete=models.CASCADE,
        related_name='municipi',
        verbose_name=_('comune')
    )
    numero = models.IntegerField(_('numero'))
    nome = models.CharField(
        _('nome'),
        max_length=100,
        blank=True,
        help_text=_('Nome del municipio (es. "Municipio I - Centro Storico")')
    )

    class Meta:
        verbose_name = _('municipio')
        verbose_name_plural = _('municipi')
        unique_together = ['comune', 'numero']
        ordering = ['comune', 'numero']

    def __str__(self):
        return self.nome or f'Municipio {self.numero} - {self.comune.nome}'


class SezioneElettorale(models.Model):
    """
    Electoral section: 500-1200 voters, min 50 in remote areas.
    This is the actual vote collection unit, independent of election type.
    """
    comune = models.ForeignKey(
        Comune,
        on_delete=models.CASCADE,
        related_name='sezioni',
        verbose_name=_('comune')
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sezioni',
        verbose_name=_('municipio')
    )
    numero = models.IntegerField(
        _('numero sezione'),
        help_text=_('Numero progressivo nel comune')
    )
    indirizzo = models.CharField(
        _('indirizzo'),
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Indirizzo del seggio')
    )
    denominazione = models.CharField(
        _('denominazione'),
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Nome del seggio (es. "Scuola Elementare Mazzini")')
    )
    n_elettori = models.IntegerField(
        _('numero elettori'),
        null=True,
        blank=True,
        help_text=_('Numero di elettori iscritti')
    )
    is_attiva = models.BooleanField(
        _('attiva'),
        default=True
    )

    # Geolocation
    latitudine = models.DecimalField(
        _('latitudine'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitudine = models.DecimalField(
        _('longitudine'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('sezione elettorale')
        verbose_name_plural = _('sezioni elettorali')
        unique_together = ['comune', 'numero']
        ordering = ['comune', 'numero']

    def __str__(self):
        return f'Sezione {self.numero} - {self.comune.nome}'

    def get_partition_unit(self, partition_type):
        """
        Restituisce la partizione (circoscrizione/collegio) di questa sezione
        per un dato tipo di partizione.

        Args:
            partition_type: TerritorialPartitionSet.PartitionType value

        Returns:
            TerritorialPartitionUnit or None
        """
        # Risale: sezione → comune → membership → partition_unit
        membership = TerritorialPartitionMembership.objects.filter(
            comune=self.comune,
            unit__partition_set__partition_type=partition_type
        ).select_related('unit').first()

        if membership:
            return membership.unit

        # Fallback: prova con la provincia
        membership = TerritorialPartitionMembership.objects.filter(
            provincia=self.comune.provincia,
            unit__partition_set__partition_type=partition_type
        ).select_related('unit').first()

        if membership:
            return membership.unit

        # Fallback: prova con la regione
        membership = TerritorialPartitionMembership.objects.filter(
            regione=self.comune.provincia.regione,
            unit__partition_set__partition_type=partition_type
        ).select_related('unit').first()

        return membership.unit if membership else None


# =============================================================================
# TERRITORIAL PARTITIONS (Circoscrizioni, Collegi)
# =============================================================================

class TerritorialPartitionSet(models.Model):
    """
    Set di partizioni territoriali (circoscrizioni, collegi).

    Esempi:
    - "Circoscrizioni Europee" (5 unità: Nord-Ovest, Nord-Est, Centro, Sud, Isole)
    - "Circoscrizioni Camera" (26 unità)
    - "Collegi Uninominali Camera 2020" (~200 unità)
    - "Collegi Plurinominali Camera 2020" (~60 unità)
    """
    class PartitionType(models.TextChoices):
        EU_CIRCOSCRIZIONE = 'EU_CIRCOSCRIZIONE', _('Circoscrizione Europee')
        CAMERA_CIRCOSCRIZIONE = 'CAMERA_CIRCOSCRIZIONE', _('Circoscrizione Camera')
        SENATO_CIRCOSCRIZIONE = 'SENATO_CIRCOSCRIZIONE', _('Circoscrizione Senato')
        COLLEGIO_UNINOMINALE_CAMERA = 'COLLEGIO_UNINOMINALE_CAMERA', _('Collegio Uninominale Camera')
        COLLEGIO_PLURINOMINALE_CAMERA = 'COLLEGIO_PLURINOMINALE_CAMERA', _('Collegio Plurinominale Camera')
        COLLEGIO_UNINOMINALE_SENATO = 'COLLEGIO_UNINOMINALE_SENATO', _('Collegio Uninominale Senato')
        COLLEGIO_PLURINOMINALE_SENATO = 'COLLEGIO_PLURINOMINALE_SENATO', _('Collegio Plurinominale Senato')

    partition_type = models.CharField(
        _('tipo partizione'),
        max_length=40,
        choices=PartitionType.choices
    )
    nome = models.CharField(
        _('nome'),
        max_length=100,
        help_text=_('es. "Circoscrizioni Europee", "Collegi Camera 2020"')
    )
    descrizione = models.TextField(_('descrizione'), blank=True)
    normative_ref = models.CharField(
        _('riferimento normativo'),
        max_length=200,
        blank=True,
        help_text=_('es. "Legge 165/2017", "DPR 361/1957"')
    )

    class Meta:
        verbose_name = _('set partizioni territoriali')
        verbose_name_plural = _('set partizioni territoriali')

    def __str__(self):
        return f'{self.nome} ({self.get_partition_type_display()})'


class TerritorialPartitionUnit(models.Model):
    """
    Singola unità di partizione (circoscrizione, collegio).

    Esempi:
    - "Nord-Ovest" (circoscrizione europee)
    - "Lazio 1" (circoscrizione camera)
    - "Roma - Collegio 1" (collegio uninominale)
    """
    partition_set = models.ForeignKey(
        TerritorialPartitionSet,
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name=_('set partizioni')
    )
    codice = models.CharField(
        _('codice'),
        max_length=30,
        help_text=_('es. "NORD_OVEST", "LAZIO_1", "U01"')
    )
    nome = models.CharField(_('nome'), max_length=150)
    parent_unit = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_units',
        verbose_name=_('unità padre'),
        help_text=_('Per gerarchie: collegio uninominale → collegio plurinominale → circoscrizione')
    )

    class Meta:
        verbose_name = _('unità partizione territoriale')
        verbose_name_plural = _('unità partizioni territoriali')
        unique_together = ['partition_set', 'codice']
        ordering = ['partition_set', 'codice']

    def __str__(self):
        return f'{self.nome} ({self.partition_set.nome})'


class TerritorialPartitionMembership(models.Model):
    """
    Appartenenza di un territorio a una partizione.

    Indica che un territorio (regione, provincia o comune) fa parte
    di una specifica unità di partizione.

    Il livello più specifico vince: se un comune ha membership diretta,
    quella ha precedenza sulla membership della provincia/regione.
    """
    unit = models.ForeignKey(
        TerritorialPartitionUnit,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('unità partizione')
    )
    # Uno di questi tre è valorizzato (dal più specifico al più generico)
    comune = models.ForeignKey(
        Comune,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='partition_memberships',
        verbose_name=_('comune')
    )
    provincia = models.ForeignKey(
        Provincia,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='partition_memberships',
        verbose_name=_('provincia')
    )
    regione = models.ForeignKey(
        Regione,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='partition_memberships',
        verbose_name=_('regione')
    )

    class Meta:
        verbose_name = _('appartenenza partizione')
        verbose_name_plural = _('appartenenze partizioni')
        # Un territorio può appartenere a una sola unità per partition_set
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(comune__isnull=False, provincia__isnull=True, regione__isnull=True) |
                    models.Q(comune__isnull=True, provincia__isnull=False, regione__isnull=True) |
                    models.Q(comune__isnull=True, provincia__isnull=True, regione__isnull=False)
                ),
                name='membership_one_territory_level'
            ),
        ]

    def __str__(self):
        territorio = self.comune or self.provincia or self.regione
        return f'{territorio} → {self.unit}'
