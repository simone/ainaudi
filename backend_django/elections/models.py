"""
Elections models: Electoral events, ballots, lists and candidates.

This module defines:
- Electoral events: ConsultazioneElettorale, TipoElezione, SchedaElettorale
- Lists and Candidates: ListaElettorale, Candidato
- Partition bindings: ElectionPartitionBinding, BallotActivation, CandidatePartitionEligibility

Territory models (Regione, Provincia, Comune, etc.) and Territorial Partitions
(TerritorialPartitionSet, TerritorialPartitionUnit) are in the 'territorio' app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

# Import territory models from territorio app
from territorio.models import Regione, Comune


# =============================================================================
# ELECTORAL EVENT (Voting event)
# =============================================================================

class ConsultazioneElettorale(models.Model):
    """
    A voting event (e.g., "8-9 June 2024", "25 September 2022").
    Can contain multiple election types on the same day.
    """
    nome = models.CharField(
        _('nome'),
        max_length=200,
        help_text=_('es. "Elezioni 8-9 Giugno 2024"')
    )
    data_inizio = models.DateField(_('data inizio'))
    data_fine = models.DateField(
        _('data fine'),
        help_text=_('Può essere 2 giorni')
    )
    is_attiva = models.BooleanField(
        _('attiva'),
        default=False,
        help_text=_('Se True, questa è la consultazione attualmente in corso')
    )
    descrizione = models.TextField(
        _('descrizione'),
        blank=True
    )

    class Meta:
        verbose_name = _('consultazione elettorale')
        verbose_name_plural = _('consultazioni elettorali')
        ordering = ['-data_inizio']

    def __str__(self):
        return self.nome


class TipoElezione(models.Model):
    """
    Type of election within a consultation.
    A consultation can have multiple types (e.g., European + Municipal + Regional).
    """
    class Tipo(models.TextChoices):
        REFERENDUM = 'REFERENDUM', _('Referendum')
        POLITICHE_CAMERA = 'POLITICHE_CAMERA', _('Politiche - Camera')
        POLITICHE_SENATO = 'POLITICHE_SENATO', _('Politiche - Senato')
        EUROPEE = 'EUROPEE', _('Europee')
        REGIONALI = 'REGIONALI', _('Regionali')
        COMUNALI = 'COMUNALI', _('Comunali')
        MUNICIPALI = 'MUNICIPALI', _('Municipali')

    consultazione = models.ForeignKey(
        ConsultazioneElettorale,
        on_delete=models.CASCADE,
        related_name='tipi_elezione',
        verbose_name=_('consultazione')
    )
    tipo = models.CharField(
        _('tipo'),
        max_length=20,
        choices=Tipo.choices
    )

    # Territorial scope (which territory votes for this election)
    ambito_nazionale = models.BooleanField(
        _('ambito nazionale'),
        default=False,
        help_text=_('True per referendum, politiche, europee')
    )
    regione = models.ForeignKey(
        Regione,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tipi_elezione',
        verbose_name=_('regione'),
        help_text=_('Per regionali')
    )
    comuni = models.ManyToManyField(
        Comune,
        blank=True,
        related_name='tipi_elezione',
        verbose_name=_('comuni'),
        help_text=_('Per comunali (lista comuni che votano)')
    )

    class Meta:
        verbose_name = _('tipo elezione')
        verbose_name_plural = _('tipi elezione')
        unique_together = ['consultazione', 'tipo', 'regione']

    def __str__(self):
        suffix = ''
        if self.regione:
            suffix = f' - {self.regione.nome}'
        return f'{self.consultazione.nome} - {self.get_tipo_display()}{suffix}'


# =============================================================================
# BALLOTS (Different by election type)
# =============================================================================

class SchedaElettorale(models.Model):
    """
    A physical ballot that the voter receives.
    E.g., Referendum 2025 = 5 ballots (one per question, different colors)
    E.g., National 2022 = 2 ballots (Chamber pink, Senate yellow)
    E.g., European = 1 ballot
    E.g., Municipal = 1 ballot (mayor + list)
    """
    tipo_elezione = models.ForeignKey(
        TipoElezione,
        on_delete=models.CASCADE,
        related_name='schede',
        verbose_name=_('tipo elezione')
    )
    nome = models.CharField(
        _('nome'),
        max_length=200,
        help_text=_('es. "Quesito 1 - Cittadinanza", "Camera", "Senato"')
    )
    colore = models.CharField(
        _('colore'),
        max_length=50,
        null=True,
        blank=True,
        help_text=_('es. "verde chiaro", "rosa", "gialla"')
    )
    ordine = models.IntegerField(
        _('ordine'),
        default=0,
        help_text=_('Ordine di visualizzazione')
    )
    turno = models.IntegerField(
        _('turno'),
        default=1,
        help_text=_('1 = primo turno, 2 = ballottaggio')
    )
    data_inizio_turno = models.DateField(
        _('data inizio turno'),
        null=True,
        blank=True,
        help_text=_('Per turno=2: data del ballottaggio. Se null, usa data_inizio consultazione')
    )

    # For referendum: question text
    testo_quesito = models.TextField(
        _('testo quesito'),
        null=True,
        blank=True,
        help_text=_('Testo completo del quesito referendario')
    )

    # Data schema for this ballot (defines what to collect)
    schema_voti = models.JSONField(
        _('schema voti'),
        default=dict,
        help_text=_('''
Schema dati per questa scheda. Esempi:
- Referendum: {"tipo": "si_no"}
- Camera/Senato: {"tipo": "liste_candidati", "uninominale": true, "plurinominale": true}
- Europee: {"tipo": "liste_preferenze", "max_preferenze": 3}
- Comunali <15k: {"tipo": "sindaco_lista", "preferenze": 1}
- Comunali >=15k: {"tipo": "sindaco_liste", "preferenze": 2, "ballottaggio": true}
        ''')
    )

    class Meta:
        verbose_name = _('scheda elettorale')
        verbose_name_plural = _('schede elettorali')
        ordering = ['tipo_elezione', 'ordine']

    def __str__(self):
        return f'{self.tipo_elezione} - {self.nome}'


# =============================================================================
# LISTS AND CANDIDATES (For elections with lists)
# =============================================================================

class ListaElettorale(models.Model):
    """
    Electoral list/party for a specific ballot.
    """
    scheda = models.ForeignKey(
        SchedaElettorale,
        on_delete=models.CASCADE,
        related_name='liste',
        verbose_name=_('scheda')
    )
    nome = models.CharField(_('nome'), max_length=200)
    nome_breve = models.CharField(
        _('nome breve'),
        max_length=50,
        blank=True,
        help_text=_('Abbreviazione (es. "M5S", "PD")')
    )
    simbolo = models.ImageField(
        _('simbolo'),
        upload_to='simboli/',
        null=True,
        blank=True
    )
    ordine_scheda = models.IntegerField(
        _('ordine scheda'),
        default=0,
        help_text=_('Posizione sulla scheda')
    )

    # For coalitions (national elections)
    coalizione = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='liste_collegate',
        verbose_name=_('coalizione'),
        help_text=_('Lista capofila della coalizione')
    )

    class Meta:
        verbose_name = _('lista elettorale')
        verbose_name_plural = _('liste elettorali')
        ordering = ['scheda', 'ordine_scheda']

    def __str__(self):
        return f'{self.nome} ({self.scheda.nome})'


class Candidato(models.Model):
    """
    Candidate in a list or single-member constituency.
    """
    # Can belong to a list (proportional) or directly to a ballot (single-member)
    lista = models.ForeignKey(
        ListaElettorale,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='candidati',
        verbose_name=_('lista')
    )
    scheda = models.ForeignKey(
        SchedaElettorale,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='candidati_uninominali',
        verbose_name=_('scheda'),
        help_text=_('Per candidati uninominali')
    )

    nome = models.CharField(_('nome'), max_length=200)
    cognome = models.CharField(_('cognome'), max_length=200)
    data_nascita = models.DateField(
        _('data di nascita'),
        null=True,
        blank=True
    )
    luogo_nascita = models.CharField(
        _('luogo di nascita'),
        max_length=100,
        blank=True
    )
    posizione_lista = models.IntegerField(
        _('posizione in lista'),
        null=True,
        blank=True,
        help_text=_('Per candidati plurinominali')
    )

    # For single-member constituencies (national elections)
    collegio_uninominale = models.CharField(
        _('collegio uninominale'),
        max_length=100,
        null=True,
        blank=True
    )

    # For mayor (municipal elections)
    is_sindaco = models.BooleanField(
        _('candidato sindaco'),
        default=False
    )

    # For regional president
    is_presidente = models.BooleanField(
        _('candidato presidente'),
        default=False
    )

    class Meta:
        verbose_name = _('candidato')
        verbose_name_plural = _('candidati')
        ordering = ['lista', 'posizione_lista', 'cognome']

    def __str__(self):
        return f'{self.cognome} {self.nome}'

    @property
    def nome_completo(self):
        return f'{self.nome} {self.cognome}'


# =============================================================================
# PARTITION BINDINGS (Link election → partitions)
# =============================================================================

class ElectionPartitionBinding(models.Model):
    """
    Binding tra consultazione e set di partizioni.

    Indica quale set di partizioni (circoscrizioni/collegi) viene usato
    per una specifica consultazione elettorale.

    Esempio:
    - Europee 2024 → usa "Circoscrizioni Europee"
    - Politiche 2022 → usa "Collegi Camera 2020" + "Collegi Senato 2020"
    """
    consultazione = models.ForeignKey(
        ConsultazioneElettorale,
        on_delete=models.CASCADE,
        related_name='partition_bindings',
        verbose_name=_('consultazione')
    )
    partition_set = models.ForeignKey(
        'territorio.TerritorialPartitionSet',
        on_delete=models.CASCADE,
        related_name='election_bindings',
        verbose_name=_('set partizioni')
    )
    note = models.TextField(_('note'), blank=True)

    class Meta:
        verbose_name = _('binding partizioni elezione')
        verbose_name_plural = _('binding partizioni elezioni')
        unique_together = ['consultazione', 'partition_set']

    def __str__(self):
        return f'{self.consultazione} → {self.partition_set}'


class BallotActivation(models.Model):
    """
    Attivazione di una scheda per una specifica partizione.

    Indica che una scheda è attiva (votabile) in una specifica
    circoscrizione/collegio. Usato quando schede diverse sono
    disponibili in territori diversi.

    Esempio:
    - Scheda "Europee" attiva in tutte e 5 le circoscrizioni
    - Scheda "Camera Uninominale Lazio 1" attiva solo nel collegio Lazio 1
    """
    scheda = models.ForeignKey(
        SchedaElettorale,
        on_delete=models.CASCADE,
        related_name='activations',
        verbose_name=_('scheda')
    )
    partition_unit = models.ForeignKey(
        'territorio.TerritorialPartitionUnit',
        on_delete=models.CASCADE,
        related_name='ballot_activations',
        verbose_name=_('unità partizione')
    )
    is_active = models.BooleanField(_('attiva'), default=True)

    class Meta:
        verbose_name = _('attivazione scheda')
        verbose_name_plural = _('attivazioni schede')
        unique_together = ['scheda', 'partition_unit']

    def __str__(self):
        status = '✓' if self.is_active else '✗'
        return f'{self.scheda.nome} → {self.partition_unit.nome} [{status}]'


class CandidatePartitionEligibility(models.Model):
    """
    Eleggibilità di un candidato per una specifica partizione.

    Indica in quale circoscrizione/collegio un candidato è eleggibile.
    Fondamentale per:
    - Europee: candidato X è nella lista del Nord-Ovest
    - Politiche: candidato Y è nel collegio uninominale Roma 1

    Esempio:
    - "Ferrara Carolina" eleggibile in "Nord-Ovest" per lista "M5S"
    - "Rossi Mario" eleggibile in "Roma - Collegio 1" (uninominale)
    """
    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.CASCADE,
        related_name='partition_eligibilities',
        verbose_name=_('candidato')
    )
    partition_unit = models.ForeignKey(
        'territorio.TerritorialPartitionUnit',
        on_delete=models.CASCADE,
        related_name='candidate_eligibilities',
        verbose_name=_('unità partizione')
    )
    lista = models.ForeignKey(
        ListaElettorale,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='candidate_eligibilities',
        verbose_name=_('lista'),
        help_text=_('Lista di appartenenza in questa partizione (per plurinominale)')
    )
    posizione = models.IntegerField(
        _('posizione'),
        null=True,
        blank=True,
        help_text=_('Posizione in lista (per plurinominale)')
    )

    class Meta:
        verbose_name = _('eleggibilità candidato per partizione')
        verbose_name_plural = _('eleggibilità candidati per partizione')
        unique_together = ['candidato', 'partition_unit']

    def __str__(self):
        if self.lista:
            return f'{self.candidato} → {self.partition_unit.nome} ({self.lista.nome_breve})'
        return f'{self.candidato} → {self.partition_unit.nome}'
