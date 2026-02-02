"""
Management command to import municipi/circoscrizioni for Italian cities.

Based on Italian law (TUEL art. 17), cities over 250k inhabitants must have
circoscrizioni, called differently in each city:
- Municipi: Roma, Milano, Bari, Genova
- Municipalità: Venezia, Napoli
- Quartieri: Firenze, Bologna, Bolzano
- Circoscrizioni: Torino, Verona, Palermo, Catania, Messina, Trento, Trieste

Usage:
    python manage.py import_municipi
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from territorio.models import Comune, Municipio


# Cities with their municipalities
# Format: (city_name, province_sigla, number_of_municipi, denomination)
CITIES_WITH_MUNICIPI = [
    # Regioni a statuto ordinario (> 250k abitanti obbligatorio)
    ('Roma', 'RM', 15, 'Municipio'),
    ('Milano', 'MI', 9, 'Municipio'),
    ('Napoli', 'NA', 10, 'Municipalità'),
    ('Torino', 'TO', 8, 'Circoscrizione'),
    ('Genova', 'GE', 9, 'Municipio'),
    ('Bologna', 'BO', 6, 'Quartiere'),
    ('Firenze', 'FI', 5, 'Quartiere'),
    ('Bari', 'BA', 5, 'Municipio'),
    ('Venezia', 'VE', 6, 'Municipalità'),
    ('Verona', 'VR', 8, 'Circoscrizione'),

    # Regioni a statuto speciale
    ('Palermo', 'PA', 8, 'Circoscrizione'),
    ('Catania', 'CT', 6, 'Circoscrizione'),
    ('Messina', 'ME', 6, 'Circoscrizione'),
    ('Trieste', 'TS', 7, 'Circoscrizione'),
    ('Trento', 'TN', 12, 'Circoscrizione'),
    ('Bolzano', 'BZ', 5, 'Quartiere'),
]

# Special names for some municipalities (optional - can be expanded)
SPECIAL_NAMES = {
    'Roma': {
        1: 'Centro Storico',
        2: 'Parioli/Nomentano',
        3: 'Monte Sacro',
        4: 'Tiburtina',
        5: 'Prenestino/Centocelle',
        6: 'Roma delle Torri',
        7: 'San Giovanni/Cinecittà',
        8: 'Appia Antica',
        9: 'EUR',
        10: 'Ostia',
        11: 'Arvalia/Portuense',
        12: 'Monte Verde',
        13: 'Aurelia',
        14: 'Monte Mario',
        15: 'Cassia/Flaminia',
    },
    'Milano': {
        1: 'Centro storico',
        2: 'Stazione Centrale, Gorla, Turro, Greco, Crescenzago',
        3: 'Città Studi, Lambrate, Venezia',
        4: 'Vittoria, Forlanini',
        5: 'Vigentino, Chiaravalle, Gratosoglio',
        6: 'Barona, Lorenteggio',
        7: 'Baggio, De Angeli, San Siro',
        8: 'Fiera, Gallaratese, Quarto Oggiaro',
        9: 'Stazione Garibaldi, Niguarda',
    },
    'Napoli': {
        1: 'Chiaia, Posillipo, San Ferdinando',
        2: 'Avvocata, Montecalvario, San Giuseppe, Porto, Mercato, Pendino',
        3: 'Stella, San Carlo all\'Arena',
        4: 'San Lorenzo, Vicaria, Poggioreale, Zona Industriale',
        5: 'Vomero, Arenella',
        6: 'Ponticelli, Barra, San Giovanni a Teduccio',
        7: 'Miano, Secondigliano, San Pietro a Patierno',
        8: 'Piscinola, Marianella, Chiaiano, Scampia',
        9: 'Soccavo, Pianura',
        10: 'Bagnoli, Fuorigrotta',
    },
}


class Command(BaseCommand):
    help = 'Import municipi/circoscrizioni for Italian cities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        created_count = 0
        updated_count = 0
        errors = []

        for city_name, provincia_sigla, num_municipi, denomination in CITIES_WITH_MUNICIPI:
            # Find comune
            try:
                comune = Comune.objects.get(
                    nome__iexact=city_name,
                    provincia__sigla=provincia_sigla
                )
            except Comune.DoesNotExist:
                errors.append(f"Comune not found: {city_name} ({provincia_sigla})")
                continue
            except Comune.MultipleObjectsReturned:
                comune = Comune.objects.filter(
                    nome__iexact=city_name,
                    provincia__sigla=provincia_sigla
                ).first()

            self.stdout.write(f"Processing {city_name} ({provincia_sigla}): {num_municipi} {denomination}...")

            # Get special names if available
            special_names = SPECIAL_NAMES.get(city_name, {})

            for numero in range(1, num_municipi + 1):
                # Build name
                special_name = special_names.get(numero, '')
                if special_name:
                    nome = f"{denomination} {numero} - {special_name}"
                else:
                    nome = f"{denomination} {numero}"

                if dry_run:
                    self.stdout.write(f"  Would create: {nome}")
                    created_count += 1
                else:
                    municipio, was_created = Municipio.objects.update_or_create(
                        comune=comune,
                        numero=numero,
                        defaults={'nome': nome}
                    )
                    if was_created:
                        created_count += 1
                    else:
                        updated_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Import complete:"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Errors:"))
            for err in errors:
                self.stdout.write(f"  - {err}")
