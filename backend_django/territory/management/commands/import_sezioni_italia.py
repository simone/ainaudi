"""
Management command to import all Italian electoral sections from CSV.

Supports two CSV formats:
1. Eligendo format (semicolon-separated):
   REGIONE;PROVINCIA;COMUNE;COD. ISTAT;N. SEZIONE;INDIRIZZO;DESCRIZIONE PLESSO;UBICAZIONE;OSPEDALIERA

2. Generic format (comma-separated):
   codice_istat,numero_sezione

Logic for denominazioni:
- Import denominazione from UBICAZIONE column (Eligendo) or denominazione column (generic)
- Exclude denominazione ONLY IF it's duplicated within the same comune with different addresses
- Example: If Comune A has 3 sections all called "Scuola Elementare" at different addresses,
  then all 3 get denominazione='', otherwise keep it even if generic term
"""
import csv
import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, SezioneElettorale


class Command(BaseCommand):
    help = 'Import electoral sections from CSV (auto-detects Eligendo or generic format)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='fixtures/sezioni_eligendo.csv',
            help='Path to CSV file (default: fixtures/sezioni_eligendo.csv)'
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
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='CSV file encoding (default: utf-8)'
        )

    def clean_istat_code(self, raw_code):
        """
        Clean ISTAT code from Excel formula format.
        Example: ="069001" -> 069001
        """
        if not raw_code:
            return ''
        # Remove Excel formula: ="..." -> ...
        cleaned = re.sub(r'^=?"?([0-9]+)"?$', r'\1', raw_code.strip())
        # Ensure 6 digits
        return cleaned.zfill(6)

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        clear = options['clear']
        encoding = options['encoding']

        self.stdout.write(f'Reading {file_path} (encoding: {encoding})...')

        # Build comune lookup by codice_istat
        comuni_map = {}
        for comune in Comune.objects.all():
            comuni_map[comune.codice_istat] = comune

        self.stdout.write(f'Loaded {len(comuni_map)} comuni from database')

        # First pass: read all sections and group by comune
        self.stdout.write('First pass: analyzing denominazioni...')
        sections_by_comune = defaultdict(list)  # codice_istat -> list of section dicts
        errors = []
        missing_comuni = set()

        with open(file_path, 'r', encoding=encoding) as f:
            # Detect delimiter (semicolon or comma)
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else ','
            f.seek(0)

            reader = csv.DictReader(f, delimiter=delimiter)
            columns = reader.fieldnames

            # Auto-detect format
            is_eligendo = 'COD. ISTAT' in columns and 'N. SEZIONE' in columns

            if is_eligendo:
                self.stdout.write('Detected ELIGENDO format (semicolon-separated)')
            else:
                self.stdout.write('Detected GENERIC format (comma-separated)')

            for row_num, row in enumerate(reader, start=2):
                try:
                    if is_eligendo:
                        # Eligendo format
                        codice_istat_raw = row.get('COD. ISTAT', '').strip()
                        codice_istat = self.clean_istat_code(codice_istat_raw)
                        numero_str = row.get('N. SEZIONE', '').strip()
                        indirizzo = row.get('INDIRIZZO', '').strip()
                        # UBICAZIONE contains specific school name (if any)
                        denominazione = row.get('UBICAZIONE', '').strip()
                    else:
                        # Generic format
                        codice_istat = row.get('codice_istat', '').strip()
                        numero_str = row.get('numero_sezione', '').strip()
                        indirizzo = row.get('indirizzo', '').strip() if 'indirizzo' in row else ''
                        denominazione = row.get('denominazione', '').strip() if 'denominazione' in row else ''

                    if not codice_istat or not numero_str:
                        errors.append(f'Row {row_num}: missing codice_istat or numero_sezione')
                        continue

                    if codice_istat not in comuni_map:
                        missing_comuni.add(codice_istat)
                        continue

                    # Store all sections grouped by comune
                    sections_by_comune[codice_istat].append({
                        'numero': int(numero_str),
                        'indirizzo': indirizzo if indirizzo else '',
                        'denominazione': denominazione if denominazione else '',
                        'row_num': row_num,
                    })

                except Exception as e:
                    errors.append(f'Row {row_num}: {e}')

        self.stdout.write(f'Read {sum(len(sections) for sections in sections_by_comune.values())} sections from {len(sections_by_comune)} comuni')

        # Second pass: identify duplicate denominazioni within each comune
        self.stdout.write('Second pass: identifying duplicate denominazioni...')

        duplicates_count = 0
        for codice_istat, sections in sections_by_comune.items():
            # Group sections by denominazione (case-insensitive)
            denom_groups = defaultdict(list)
            for section in sections:
                denom = section['denominazione'].lower() if section['denominazione'] else ''
                if denom:  # Only check non-empty denominazioni
                    denom_groups[denom].append(section)

            # Mark denominazioni as duplicates if they appear multiple times
            # with different addresses
            for denom, group in denom_groups.items():
                if len(group) > 1:
                    # Check if they have different addresses
                    addresses = set()
                    for s in group:
                        addr = s['indirizzo'].strip().lower()
                        if addr:
                            addresses.add(addr)

                    # If multiple sections with same denom but different addresses -> duplicate
                    if len(addresses) > 1:
                        # Mark all sections in this group as having duplicate denominazione
                        for section in group:
                            section['is_duplicate'] = True
                            duplicates_count += 1

        self.stdout.write(f'Found {duplicates_count} sections with duplicate denominazioni (will be cleared)')

        # Third pass: create SezioneElettorale objects
        sections_to_create = []
        for codice_istat, sections in sections_by_comune.items():
            comune = comuni_map[codice_istat]

            for section in sections:
                # Clear denominazione if it's a duplicate in this comune
                denominazione = section['denominazione']
                if section.get('is_duplicate', False):
                    denominazione = ''

                sections_to_create.append(SezioneElettorale(
                    comune=comune,
                    numero=section['numero'],
                    indirizzo=section['indirizzo'] if section['indirizzo'] else None,
                    denominazione=denominazione if denominazione else None,
                    is_attiva=True
                ))

        self.stdout.write(f'Prepared {len(sections_to_create)} sections for import')

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
            # Show some examples of duplicate denominazioni
            self.stdout.write('\nExamples of duplicate denominazioni that would be cleared:')
            examples_shown = 0
            for codice_istat, sections in sections_by_comune.items():
                comune = comuni_map.get(codice_istat)
                if not comune:
                    continue
                for section in sections:
                    if section.get('is_duplicate', False) and examples_shown < 10:
                        self.stdout.write(
                            f'  {comune.nome} - Sez {section["numero"]}: '
                            f'"{section["denominazione"]}" @ {section["indirizzo"]}'
                        )
                        examples_shown += 1
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
