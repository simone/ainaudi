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

        # Prefetch all Roma sections for efficient lookup
        self.stdout.write('Loading existing Roma sections...')
        sezioni_map = {}
        for sezione in SezioneElettorale.objects.filter(comune=roma).select_related('municipio'):
            sezioni_map[sezione.numero] = sezione

        self.stdout.write(f'Loaded {len(sezioni_map)} existing sections')

        # Update municipio ONLY for existing sections with denominazione/indirizzo
        updated_count = 0
        skipped_count = 0
        not_found_count = 0
        sezioni_to_update = []
        not_found_details = []  # Track missing sections

        for data in sections_data:
            sezione = sezioni_map.get(data['numero'])

            if not sezione:
                not_found_count += 1
                not_found_details.append({
                    'numero': data['numero'],
                    'municipio': data['municipio'].numero if data['municipio'] else None,
                    'indirizzo': data['indirizzo']
                })
                if dry_run:
                    mun_str = f"Mun {data['municipio'].numero}" if data['municipio'] else "N/A"
                    self.stdout.write(
                        f'  ✗ Sezione {data["numero"]}: not found in DB '
                        f'({mun_str}, {data["indirizzo"][:50] if data["indirizzo"] else "N/A"})'
                    )
                continue

            # Check if sezione has denominazione OR indirizzo (at least one)
            has_data = bool(sezione.denominazione or sezione.indirizzo)

            if not has_data:
                skipped_count += 1
                if dry_run:
                    self.stdout.write(
                        f'  ⊘ Sezione {data["numero"]}: skipped (no denominazione/indirizzo)'
                    )
                continue

            # Only update municipio if different
            old_municipio = sezione.municipio
            if old_municipio != data['municipio']:
                sezione.municipio = data['municipio']
                sezioni_to_update.append(sezione)
                old_mun_str = f"Mun {old_municipio.numero}" if old_municipio else "NULL"
                new_mun_str = f"Mun {data['municipio'].numero}" if data['municipio'] else "NULL"
                if dry_run or len(sezioni_to_update) <= 20:
                    self.stdout.write(
                        f'  ↻ Sezione {data["numero"]}: {old_mun_str} → {new_mun_str}'
                    )
            else:
                skipped_count += 1

        updated_count = len(sezioni_to_update)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n[DRY RUN] Would update {updated_count} sezioni'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
            self.stdout.write(f'Would update:      {updated_count}')
            self.stdout.write(f'Skipped:           {skipped_count}')
            self.stdout.write(f'Not found in DB:   {not_found_count}')
            self.stdout.write(f'Total in CSV:      {len(sections_data)}')
            return

        # Bulk update
        if sezioni_to_update:
            self.stdout.write(f'\nBulk updating {len(sezioni_to_update)} sezioni...')
            with transaction.atomic():
                SezioneElettorale.objects.bulk_update(
                    sezioni_to_update,
                    ['municipio'],
                    batch_size=500
                )
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {len(sezioni_to_update)} sezioni'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
        self.stdout.write(f'Municipio updated: {updated_count}')
        self.stdout.write(f'Skipped:           {skipped_count}')
        self.stdout.write(f'Not found in DB:   {not_found_count}')
        self.stdout.write(f'Total in CSV:      {len(sections_data)}')
        self.stdout.write('')

        if not_found_details:
            self.stdout.write(self.style.WARNING(
                f'⚠️  {len(not_found_details)} sezioni from CSV not found in database:'
            ))
            self.stdout.write('')
            for detail in not_found_details:
                mun_str = f"Municipio {detail['municipio']}" if detail['municipio'] else "N/A"
                self.stdout.write(
                    f'  • Sezione {detail["numero"]:4d} - {mun_str:13s} - {detail["indirizzo"]}'
                )
            self.stdout.write('')
            self.stdout.write('   To create these sections, use:')
            self.stdout.write('     python manage.py import_sezioni_italia  # Import from Eligendo')
            self.stdout.write('     OR add --create flag to this command (not yet implemented)')
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('✓ Municipio assignment completed'))
