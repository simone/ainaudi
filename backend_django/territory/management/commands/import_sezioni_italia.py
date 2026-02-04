"""
Management command to import all Italian electoral sections from CSV.
The CSV is generated from Eligendo data (Europee 2024).
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, SezioneElettorale


class Command(BaseCommand):
    help = 'Import electoral sections from sezioni_italia_2024.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/sezioni_italia_2024.csv',
            help='Path to CSV file (default: data/sezioni_italia_2024.csv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing sections before importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        clear = options['clear']

        self.stdout.write(f'Reading {file_path}...')

        # Build comune lookup by codice_istat
        comuni_map = {}
        for comune in Comune.objects.all():
            comuni_map[comune.codice_istat] = comune
        
        self.stdout.write(f'Loaded {len(comuni_map)} comuni from database')

        # Read CSV
        sections_to_create = []
        errors = []
        missing_comuni = set()

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                codice_istat = row.get('codice_istat', '').strip()
                numero = row.get('numero_sezione', '').strip()

                if not codice_istat or not numero:
                    errors.append(f'Row {row_num}: missing codice_istat or numero_sezione')
                    continue

                comune = comuni_map.get(codice_istat)
                if not comune:
                    missing_comuni.add(codice_istat)
                    continue

                try:
                    sections_to_create.append(SezioneElettorale(
                        comune=comune,
                        numero=int(numero),
                        is_attiva=True
                    ))
                except Exception as e:
                    errors.append(f'Row {row_num}: {e}')

        self.stdout.write(f'Parsed {len(sections_to_create)} sections')
        
        if missing_comuni:
            self.stdout.write(
                self.style.WARNING(f'Missing {len(missing_comuni)} comuni in database')
            )
            if len(missing_comuni) <= 20:
                for cod in sorted(missing_comuni):
                    self.stdout.write(f'  - {cod}')

        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} errors'))
            for err in errors[:10]:
                self.stdout.write(f'  - {err}')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY RUN - no changes made'))
            return

        # Import
        with transaction.atomic():
            if clear:
                deleted, _ = SezioneElettorale.objects.all().delete()
                self.stdout.write(f'Deleted {deleted} existing sections')

            # Use bulk_create with ignore_conflicts to skip existing
            created = SezioneElettorale.objects.bulk_create(
                sections_to_create,
                ignore_conflicts=True,
                batch_size=5000
            )
            
            # Count actual records (bulk_create with ignore_conflicts doesn't return count)
            final_count = SezioneElettorale.objects.count()
            
        self.stdout.write(self.style.SUCCESS(
            f'Import complete. Total sections in database: {final_count}'
        ))
