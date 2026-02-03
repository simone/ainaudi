"""
Management command to set up initial data for Referendum Giustizia 2026.

Usage:
    python manage.py setup_referendum_2026

This command:
1. Loads all 20 Italian regions
2. Loads all 107 provinces
3. Sets up European circumscriptions using TerritorialPartitionSet
4. Creates the Referendum Giustizia 2026 consultation
5. Creates the ballot (scheda) with the official question text

Sources:
- ISTAT: https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
- Geopop: https://www.geopop.it/il-referendum-sulla-giustizia-del-22-e-23-marzo-non-avra-il-quorum/
- Pagella Politica: https://pagellapolitica.it/articoli/testo-quesito-referendum-costituzionale-giustizia
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import (
    Regione, Provincia,
    TerritorialPartitionSet, TerritorialPartitionUnit, TerritorialPartitionMembership
)
from elections.models import (
    ConsultazioneElettorale, TipoElezione, SchedaElettorale
)


class Command(BaseCommand):
    help = 'Setup initial data for Referendum Giustizia 2026'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Referendum Giustizia 2026 data...')

        with transaction.atomic():
            self.setup_regioni()
            self.setup_province()
            self.setup_circoscrizioni_europee()
            self.setup_referendum()

        self.stdout.write(self.style.SUCCESS('Successfully set up all data!'))

    def setup_regioni(self):
        """Create all 20 Italian regions."""
        self.stdout.write('  Creating regions...')

        regioni_data = [
            ('01', 'Piemonte', False),
            ('02', "Valle d'Aosta", True),
            ('03', 'Lombardia', False),
            ('04', 'Trentino-Alto Adige', True),
            ('05', 'Veneto', False),
            ('06', 'Friuli-Venezia Giulia', True),
            ('07', 'Liguria', False),
            ('08', 'Emilia-Romagna', False),
            ('09', 'Toscana', False),
            ('10', 'Umbria', False),
            ('11', 'Marche', False),
            ('12', 'Lazio', False),
            ('13', 'Abruzzo', False),
            ('14', 'Molise', False),
            ('15', 'Campania', False),
            ('16', 'Puglia', False),
            ('17', 'Basilicata', False),
            ('18', 'Calabria', False),
            ('19', 'Sicilia', True),
            ('20', 'Sardegna', True),
        ]

        for codice, nome, speciale in regioni_data:
            Regione.objects.update_or_create(
                codice_istat=codice,
                defaults={'nome': nome, 'statuto_speciale': speciale}
            )

        self.stdout.write(f'    Created {Regione.objects.count()} regions')

    def setup_province(self):
        """Create all 107 Italian provinces."""
        self.stdout.write('  Creating provinces...')

        # Province data: (codice_istat, sigla, nome, codice_regione, is_citta_metropolitana)
        province_data = [
            # Piemonte (01)
            ('001', 'TO', 'Torino', '01', True),
            ('002', 'VC', 'Vercelli', '01', False),
            ('003', 'NO', 'Novara', '01', False),
            ('004', 'CN', 'Cuneo', '01', False),
            ('005', 'AT', 'Asti', '01', False),
            ('006', 'AL', 'Alessandria', '01', False),
            ('096', 'BI', 'Biella', '01', False),
            ('103', 'VB', 'Verbano-Cusio-Ossola', '01', False),
            # Valle d'Aosta (02)
            ('007', 'AO', 'Aosta', '02', False),
            # Lombardia (03)
            ('012', 'VA', 'Varese', '03', False),
            ('013', 'CO', 'Como', '03', False),
            ('014', 'SO', 'Sondrio', '03', False),
            ('015', 'MI', 'Milano', '03', True),
            ('016', 'BG', 'Bergamo', '03', False),
            ('017', 'BS', 'Brescia', '03', False),
            ('018', 'PV', 'Pavia', '03', False),
            ('019', 'CR', 'Cremona', '03', False),
            ('020', 'MN', 'Mantova', '03', False),
            ('097', 'LC', 'Lecco', '03', False),
            ('098', 'LO', 'Lodi', '03', False),
            ('108', 'MB', 'Monza e della Brianza', '03', False),
            # Trentino-Alto Adige (04)
            ('021', 'BZ', 'Bolzano', '04', False),
            ('022', 'TN', 'Trento', '04', False),
            # Veneto (05)
            ('023', 'VR', 'Verona', '05', False),
            ('024', 'VI', 'Vicenza', '05', False),
            ('025', 'BL', 'Belluno', '05', False),
            ('026', 'TV', 'Treviso', '05', False),
            ('027', 'VE', 'Venezia', '05', True),
            ('028', 'PD', 'Padova', '05', False),
            ('029', 'RO', 'Rovigo', '05', False),
            # Friuli-Venezia Giulia (06)
            ('030', 'UD', 'Udine', '06', False),
            ('031', 'GO', 'Gorizia', '06', False),
            ('032', 'TS', 'Trieste', '06', False),
            ('093', 'PN', 'Pordenone', '06', False),
            # Liguria (07)
            ('008', 'IM', 'Imperia', '07', False),
            ('009', 'SV', 'Savona', '07', False),
            ('010', 'GE', 'Genova', '07', True),
            ('011', 'SP', 'La Spezia', '07', False),
            # Emilia-Romagna (08)
            ('033', 'PC', 'Piacenza', '08', False),
            ('034', 'PR', 'Parma', '08', False),
            ('035', 'RE', "Reggio nell'Emilia", '08', False),
            ('036', 'MO', 'Modena', '08', False),
            ('037', 'BO', 'Bologna', '08', True),
            ('038', 'FE', 'Ferrara', '08', False),
            ('039', 'RA', 'Ravenna', '08', False),
            ('040', 'FC', 'Forlì-Cesena', '08', False),
            ('099', 'RN', 'Rimini', '08', False),
            # Toscana (09)
            ('045', 'MS', 'Massa-Carrara', '09', False),
            ('046', 'LU', 'Lucca', '09', False),
            ('047', 'PT', 'Pistoia', '09', False),
            ('048', 'FI', 'Firenze', '09', True),
            ('049', 'LI', 'Livorno', '09', False),
            ('050', 'PI', 'Pisa', '09', False),
            ('051', 'AR', 'Arezzo', '09', False),
            ('052', 'SI', 'Siena', '09', False),
            ('053', 'GR', 'Grosseto', '09', False),
            ('100', 'PO', 'Prato', '09', False),
            # Umbria (10)
            ('054', 'PG', 'Perugia', '10', False),
            ('055', 'TR', 'Terni', '10', False),
            # Marche (11)
            ('041', 'PU', 'Pesaro e Urbino', '11', False),
            ('042', 'AN', 'Ancona', '11', False),
            ('043', 'MC', 'Macerata', '11', False),
            ('044', 'AP', 'Ascoli Piceno', '11', False),
            ('109', 'FM', 'Fermo', '11', False),
            # Lazio (12)
            ('056', 'VT', 'Viterbo', '12', False),
            ('057', 'RI', 'Rieti', '12', False),
            ('058', 'RM', 'Roma', '12', True),
            ('059', 'LT', 'Latina', '12', False),
            ('060', 'FR', 'Frosinone', '12', False),
            # Abruzzo (13)
            ('066', 'AQ', "L'Aquila", '13', False),
            ('067', 'TE', 'Teramo', '13', False),
            ('068', 'PE', 'Pescara', '13', False),
            ('069', 'CH', 'Chieti', '13', False),
            # Molise (14)
            ('070', 'CB', 'Campobasso', '14', False),
            ('094', 'IS', 'Isernia', '14', False),
            # Campania (15)
            ('061', 'CE', 'Caserta', '15', False),
            ('062', 'BN', 'Benevento', '15', False),
            ('063', 'NA', 'Napoli', '15', True),
            ('064', 'AV', 'Avellino', '15', False),
            ('065', 'SA', 'Salerno', '15', False),
            # Puglia (16)
            ('071', 'FG', 'Foggia', '16', False),
            ('072', 'BA', 'Bari', '16', True),
            ('073', 'TA', 'Taranto', '16', False),
            ('074', 'BR', 'Brindisi', '16', False),
            ('075', 'LE', 'Lecce', '16', False),
            ('110', 'BT', 'Barletta-Andria-Trani', '16', False),
            # Basilicata (17)
            ('076', 'PZ', 'Potenza', '17', False),
            ('077', 'MT', 'Matera', '17', False),
            # Calabria (18)
            ('078', 'CS', 'Cosenza', '18', False),
            ('079', 'CZ', 'Catanzaro', '18', False),
            ('080', 'RC', 'Reggio di Calabria', '18', True),
            ('101', 'KR', 'Crotone', '18', False),
            ('102', 'VV', 'Vibo Valentia', '18', False),
            # Sicilia (19)
            ('081', 'TP', 'Trapani', '19', False),
            ('082', 'PA', 'Palermo', '19', True),
            ('083', 'ME', 'Messina', '19', True),
            ('084', 'AG', 'Agrigento', '19', False),
            ('085', 'CL', 'Caltanissetta', '19', False),
            ('086', 'EN', 'Enna', '19', False),
            ('087', 'CT', 'Catania', '19', True),
            ('088', 'RG', 'Ragusa', '19', False),
            ('089', 'SR', 'Siracusa', '19', False),
            # Sardegna (20)
            ('090', 'SS', 'Sassari', '20', False),
            ('091', 'NU', 'Nuoro', '20', False),
            ('092', 'CA', 'Cagliari', '20', True),
            ('095', 'OR', 'Oristano', '20', False),
            ('111', 'SU', 'Sud Sardegna', '20', False),
        ]

        for codice, sigla, nome, codice_regione, is_metro in province_data:
            regione = Regione.objects.get(codice_istat=codice_regione)
            Provincia.objects.update_or_create(
                codice_istat=codice,
                defaults={
                    'regione': regione,
                    'sigla': sigla,
                    'nome': nome,
                    'is_citta_metropolitana': is_metro
                }
            )

        self.stdout.write(f'    Created {Provincia.objects.count()} provinces')

    def setup_circoscrizioni_europee(self):
        """Set up European circumscriptions using TerritorialPartitionSet."""
        self.stdout.write('  Creating European circumscriptions...')

        # Create the partition set for European elections
        partition_set, _ = TerritorialPartitionSet.objects.update_or_create(
            partition_type=TerritorialPartitionSet.PartitionType.EU_CIRCOSCRIZIONE,
            defaults={
                'nome': 'Circoscrizioni Europee',
                'descrizione': '5 circoscrizioni per le elezioni del Parlamento Europeo',
                'normative_ref': 'Legge 18/1979'
            }
        )

        # Circoscrizioni Europee con le regioni associate
        circoscrizioni = {
            'NORD_OVEST': ('Italia Nord-Occidentale', ['01', '02', '03', '07']),  # Piemonte, VdA, Lombardia, Liguria
            'NORD_EST': ('Italia Nord-Orientale', ['04', '05', '06', '08']),      # TAA, Veneto, FVG, Emilia-Romagna
            'CENTRO': ('Italia Centrale', ['09', '10', '11', '12']),              # Toscana, Umbria, Marche, Lazio
            'SUD': ('Italia Meridionale', ['13', '14', '15', '16', '17', '18']),  # Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria
            'ISOLE': ('Italia Insulare', ['19', '20']),                           # Sicilia, Sardegna
        }

        for codice, (nome, codici_regioni) in circoscrizioni.items():
            # Create the partition unit
            unit, _ = TerritorialPartitionUnit.objects.update_or_create(
                partition_set=partition_set,
                codice=codice,
                defaults={'nome': nome}
            )

            # Create memberships for each region
            for codice_regione in codici_regioni:
                regione = Regione.objects.get(codice_istat=codice_regione)
                TerritorialPartitionMembership.objects.update_or_create(
                    unit=unit,
                    regione=regione,
                    defaults={'comune': None, 'provincia': None}
                )

        self.stdout.write(f'    Created {TerritorialPartitionUnit.objects.filter(partition_set=partition_set).count()} circumscriptions')

    def setup_referendum(self):
        """Set up the Referendum Giustizia 2026."""
        self.stdout.write('  Creating Referendum Giustizia 2026...')

        # Consultazione elettorale
        consultazione, _ = ConsultazioneElettorale.objects.update_or_create(
            nome='Referendum Costituzionale Giustizia 2026',
            defaults={
                'data_inizio': '2026-03-22',
                'data_fine': '2026-03-23',
                'is_attiva': True,
                'descrizione': """Referendum popolare confermativo della legge costituzionale "Norme in materia di ordinamento giurisdizionale e di istituzione della Corte disciplinare".

Pubblicato in Gazzetta Ufficiale n. 253 del 30 ottobre 2025.

Il referendum riguarda la separazione delle carriere tra magistrati giudicanti (giudici) e requirenti (pubblici ministeri), con modifiche agli articoli 87, 102, 104, 105, 106, 107, 110 della Costituzione.

TIPO: Referendum confermativo ex art. 138 Cost.
QUORUM: NON richiesto (valido indipendentemente dall'affluenza)

ORARI VOTAZIONE:
- Domenica 22 marzo: 7:00 - 23:00
- Lunedì 23 marzo: 7:00 - 15:00

Fonti:
- Gazzetta Ufficiale n. 253 del 30/10/2025
- D.P.R. 14 gennaio 2026 (indizione referendum)"""
            }
        )

        # Tipo elezione
        tipo_elezione, _ = TipoElezione.objects.update_or_create(
            consultazione=consultazione,
            tipo='REFERENDUM',
            regione=None,
            defaults={'ambito_nazionale': True}
        )

        # Scheda elettorale con il quesito ufficiale
        SchedaElettorale.objects.update_or_create(
            tipo_elezione=tipo_elezione,
            nome='Referendum Costituzionale - Separazione Carriere Magistratura',
            defaults={
                'colore': 'azzurro',
                'ordine': 1,
                'testo_quesito': """Approvate il testo della legge costituzionale concernente «Norme in materia di ordinamento giurisdizionale e di istituzione della Corte disciplinare» approvato dal Parlamento e pubblicato nella Gazzetta Ufficiale della Repubblica italiana – Serie generale – n. 253 del 30 ottobre 2025?""",
                'schema_voti': {
                    'tipo': 'si_no',
                    'opzioni': ['SI', 'NO'],
                    'descrizione': 'Referendum confermativo art. 138 Cost. - Nessun quorum richiesto',
                    'articoli_modificati': [87, 102, 104, 105, 106, 107, 110],
                    'materia': 'Separazione delle carriere tra magistrati giudicanti e requirenti',
                    'effetto_si': 'La riforma costituzionale entra in vigore',
                    'effetto_no': 'La riforma costituzionale viene respinta'
                }
            }
        )

        self.stdout.write('    Created referendum consultation and ballot')
