"""
Management command to import/update electoral sections for Roma from CSV.

CSV format (comma-separated):
SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO,

Usage:
    python manage.py import_sezioni_roma
    python manage.py import_sezioni_roma --file=fixtures/roma_sezioni.csv
    python manage.py import_sezioni_roma --clear-denominazione
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, Municipio, SezioneElettorale


class Command(BaseCommand):
    help = 'Import/update Roma electoral sections from CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='fixtures/ROMA - Sezioni.csv',
            help='Path to CSV file (default: fixtures/ROMA - Sezioni.csv)'
        )
        parser.add_argument(
            '--clear-denominazione',
            action='store_true',
            help='Clear denominazione field (set to empty) for all Roma sections'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        clear_denominazione = options['clear_denominazione']
        dry_run = options['dry_run']

        # Get Roma comune
        try:
            roma = Comune.objects.get(codice_istat='058091')
            self.stdout.write(f'Found Comune: {roma.nome} (codice: {roma.codice_istat})')
        except Comune.DoesNotExist:
            self.stderr.write(self.style.ERROR('Comune Roma (058091) not found!'))
            self.stdout.write('Run: python manage.py import_comuni_istat')
            return

        # Clear denominazione if requested
        if clear_denominazione:
            self.stdout.write('Clearing denominazione for all Roma sections...')

            if not dry_run:
                updated = SezioneElettorale.objects.filter(
                    comune=roma
                ).update(denominazione='')

                self.stdout.write(self.style.SUCCESS(
                    f'✓ Cleared denominazione for {updated} Roma sections'
                ))
            else:
                count = SezioneElettorale.objects.filter(comune=roma).count()
                self.stdout.write(f'[DRY RUN] Would clear {count} sections')

            if not file_path or file_path == 'fixtures/ROMA - Sezioni.csv':
                # Only clear, no import
                return

        # Build municipi map
        municipi_map = {}
        for municipio in Municipio.objects.filter(comune=roma):
            municipi_map[municipio.numero] = municipio

        self.stdout.write(f'Loaded {len(municipi_map)} municipi for Roma')

        # Read CSV
        self.stdout.write(f'Reading {file_path}...')

        sections_data = []
        errors = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    numero_str = row.get('SEZIONE', '').strip()
                    comune_nome = row.get('COMUNE', '').strip()
                    municipio_num_str = row.get('MUNICIPIO', '').strip()
                    indirizzo = row.get('INDIRIZZO', '').strip()

                    if not numero_str:
                        errors.append(f'Row {row_num}: missing SEZIONE')
                        continue

                    if comune_nome and comune_nome.upper() != 'ROMA':
                        errors.append(f'Row {row_num}: COMUNE is not ROMA ({comune_nome})')
                        continue

                    numero = int(numero_str)
                    municipio = None

                    if municipio_num_str:
                        try:
                            municipio_num = int(municipio_num_str)
                            municipio = municipi_map.get(municipio_num)
                            if not municipio:
                                errors.append(
                                    f'Row {row_num}: Municipio {municipio_num} not found'
                                )
                        except ValueError:
                            errors.append(
                                f'Row {row_num}: Invalid municipio number: {municipio_num_str}'
                            )

                    sections_data.append({
                        'numero': numero,
                        'indirizzo': indirizzo if indirizzo else None,
                        'municipio': municipio
                    })

                except Exception as e:
                    errors.append(f'Row {row_num}: {e}')

        self.stdout.write(f'Parsed {len(sections_data)} sections from CSV')

        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} errors:'))
            for err in errors[:20]:
                self.stdout.write(f'  - {err}')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('[DRY RUN] No changes made'))
            return

        # Import/Update sections
        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in sections_data:
                sezione, created = SezioneElettorale.objects.update_or_create(
                    comune=roma,
                    numero=data['numero'],
                    defaults={
                        'indirizzo': data['indirizzo'],
                        'municipio': data['municipio'],
                        'is_attiva': True,
                        # Keep existing denominazione, don't override
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(f'  ✓ Created: Sezione {data["numero"]}')
                else:
                    # Check if updated
                    if sezione.indirizzo != data['indirizzo'] or sezione.municipio != data['municipio']:
                        updated_count += 1
                        self.stdout.write(
                            f'  ↻ Updated: Sezione {data["numero"]} '
                            f'(indirizzo, municipio)'
                        )
                    else:
                        skipped_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
        self.stdout.write(f'Created:  {created_count}')
        self.stdout.write(f'Updated:  {updated_count}')
        self.stdout.write(f'Skipped:  {skipped_count}')
        self.stdout.write(f'Total:    {len(sections_data)}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Import completed'))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. python manage.py match_sezioni_plessi  # Match with school names')
