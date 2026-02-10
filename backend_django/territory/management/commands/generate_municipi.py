"""
Management command to generate municipi for major Italian cities.

Creates municipal districts (municipi, circoscrizioni, zone) for cities
that have administrative subdivisions.

Usage:
    python manage.py generate_municipi
    python manage.py generate_municipi --city milano
    python manage.py generate_municipi --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, Municipio


# Configuration for Italian cities with municipi/circoscrizioni
CITIES_CONFIG = {
    'roma': {
        'codice_istat': '058091',
        'n_municipi': 15,
        'label': 'Municipio',
        'names': {
            1: 'Municipio I - Centro Storico',
            2: 'Municipio II - Parioli/Nomentano',
            3: 'Municipio III - Monte Sacro',
            4: 'Municipio IV - Tiburtino',
            5: 'Municipio V - Prenestino-Casilino',
            6: 'Municipio VI - Torre Angela/Romanina',
            7: 'Municipio VII - Appio-Latino',
            8: 'Municipio VIII - Ostiense',
            9: 'Municipio IX - EUR',
            10: 'Municipio X - Ostia',
            11: 'Municipio XI - Portuense',
            12: 'Municipio XII - Monte Verde',
            13: 'Municipio XIII - Aurelia',
            14: 'Municipio XIV - Monte Mario',
            15: 'Municipio XV - Cassia/Flaminia',
        }
    },
    'milano': {
        'codice_istat': '015146',
        'n_municipi': 9,
        'label': 'Municipio',
        'names': {
            1: 'Municipio 1 - Centro Storico',
            2: 'Municipio 2 - Stazione Centrale/Gorla/Turro/Greco',
            3: 'Municipio 3 - Città Studi/Lambrate/Porta Venezia',
            4: 'Municipio 4 - Porta Vittoria/Forlanini',
            5: 'Municipio 5 - Vigentino/Chiaravalle/Gratosoglio',
            6: 'Municipio 6 - Barona/Lorenteggio',
            7: 'Municipio 7 - Baggio/De Angeli/San Siro',
            8: 'Municipio 8 - Fiera/Gallaratese/Quarto Oggiaro',
            9: 'Municipio 9 - Garibaldi/Niguarda',
        }
    },
    'torino': {
        'codice_istat': '001272',
        'n_municipi': 8,
        'label': 'Circoscrizione',
        'names': {
            1: 'Circoscrizione 1 - Centro/Crocetta',
            2: 'Circoscrizione 2 - Santa Rita/Mirafiori Nord',
            3: 'Circoscrizione 3 - San Paolo/Cenisia/Pozzo Strada',
            4: 'Circoscrizione 4 - San Donato/Parella/Campidoglio',
            5: 'Circoscrizione 5 - Borgo Vittoria/Madonna di Campagna',
            6: 'Circoscrizione 6 - Barriera di Milano/Rebaudengo/Falchera',
            7: 'Circoscrizione 7 - Aurora/Vanchiglia/Sassi',
            8: 'Circoscrizione 8 - San Salvario/Cavoretto/Borgo Po',
        }
    },
    'napoli': {
        'codice_istat': '063049',
        'n_municipi': 10,
        'label': 'Municipalità',
        'names': {
            1: 'Municipalità 1 - Chiaia/Posillipo/San Ferdinando',
            2: 'Municipalità 2 - Avvocata/Montecalvario/Mercato',
            3: 'Municipalità 3 - Stella/San Carlo all\'Arena',
            4: 'Municipalità 4 - San Lorenzo/Vicaria/Poggioreale/Zona Industriale',
            5: 'Municipalità 5 - Vomero/Arenella',
            6: 'Municipalità 6 - Barra/Ponticelli/San Giovanni a Teduccio',
            7: 'Municipalità 7 - Miano/Secondigliano/San Pietro a Patierno',
            8: 'Municipalità 8 - Piscinola/Marianella/Chiaiano/Scampia',
            9: 'Municipalità 9 - Pianura/Soccavo',
            10: 'Municipalità 10 - Bagnoli/Fuorigrotta',
        }
    },
    'bari': {
        'codice_istat': '072006',
        'n_municipi': 5,
        'label': 'Municipio',
        'names': {
            1: 'Municipio I - Palese/Macchie/Santo Spirito/San Pio',
            2: 'Municipio II - San Paolo/Stanic/Villaggio del Lavoratore',
            3: 'Municipio III - Picone/Poggiofranco/Carrassi/San Pasquale',
            4: 'Municipio IV - Carbonara/Ceglie/Loseto/Triggiano',
            5: 'Municipio V - Japigia/Torre a Mare/San Giorgio',
        }
    },
    'palermo': {
        'codice_istat': '082053',
        'n_municipi': 8,
        'label': 'Circoscrizione',
        'names': {
            1: 'Circoscrizione 1 - Kalsa/Tribunali/Castellammare',
            2: 'Circoscrizione 2 - Settecannoli/Brancaccio',
            3: 'Circoscrizione 3 - Villagrazia/Falsomiele',
            4: 'Circoscrizione 4 - Montegrappa/Santa Rosalia',
            5: 'Circoscrizione 5 - Zisa/Borgo Nuovo',
            6: 'Circoscrizione 6 - Resuttana/San Lorenzo',
            7: 'Circoscrizione 7 - Pallavicino/Tommaso Natale',
            8: 'Circoscrizione 8 - Partanna Mondello/Sferracavallo',
        }
    },
    'genova': {
        'codice_istat': '010025',
        'n_municipi': 9,
        'label': 'Municipio',
        'names': {
            1: 'Municipio I - Centro Est',
            2: 'Municipio II - Centro Ovest',
            3: 'Municipio III - Bassa Val Bisagno',
            4: 'Municipio IV - Media Val Bisagno',
            5: 'Municipio V - Valpolcevera',
            6: 'Municipio VI - Medio Ponente',
            7: 'Municipio VII - Ponente',
            8: 'Municipio VIII - Medio Levante',
            9: 'Municipio IX - Levante',
        }
    },
}


class Command(BaseCommand):
    help = 'Generate municipi for major Italian cities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            help=f'Generate only for specific city: {", ".join(CITIES_CONFIG.keys())}'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        city_filter = options.get('city')

        if city_filter:
            if city_filter.lower() not in CITIES_CONFIG:
                self.stderr.write(f'Unknown city: {city_filter}')
                self.stdout.write(f'Available cities: {", ".join(CITIES_CONFIG.keys())}')
                return
            cities_to_process = {city_filter.lower(): CITIES_CONFIG[city_filter.lower()]}
        else:
            cities_to_process = CITIES_CONFIG

        total_created = 0

        for city_name, config in cities_to_process.items():
            codice_istat = config['codice_istat']
            n_municipi = config['n_municipi']
            label = config['label']
            names = config.get('names', {})

            # Get comune
            try:
                comune = Comune.objects.get(codice_istat=codice_istat)
            except Comune.DoesNotExist:
                self.stderr.write(f'Comune not found: {city_name} ({codice_istat})')
                continue

            self.stdout.write(f'\n{comune.nome.upper()} - {n_municipi} {label}')
            self.stdout.write('-' * 60)

            created_count = 0

            for numero in range(1, n_municipi + 1):
                # Get custom name or generate default
                nome = names.get(numero, f'{label} {numero}')

                # Check if already exists
                existing = Municipio.objects.filter(
                    comune=comune,
                    numero=numero
                ).first()

                if existing:
                    if dry_run:
                        self.stdout.write(f'  [{numero:2d}] ⏭️  SKIP: {existing.nome}')
                    continue

                if dry_run:
                    self.stdout.write(f'  [{numero:2d}] ✨ CREATE: {nome}')
                    created_count += 1
                else:
                    Municipio.objects.create(
                        comune=comune,
                        numero=numero,
                        nome=nome
                    )
                    self.stdout.write(f'  [{numero:2d}] ✅ {nome}')
                    created_count += 1

            total_created += created_count

            if created_count > 0:
                if dry_run:
                    self.stdout.write(f'  → Would create {created_count} municipi')
                else:
                    self.stdout.write(f'  → Created {created_count} municipi')

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN - would create {total_created} municipi'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {total_created} municipi'))
