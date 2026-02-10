"""
Management command to import all Italian electoral sections from CSV.

Supports two CSV formats:
1. Eligendo format (semicolon-separated):
   REGIONE;PROVINCIA;COMUNE;COD. ISTAT;N. SEZIONE;INDIRIZZO;DESCRIZIONE PLESSO;UBICAZIONE;OSPEDALIERA

2. Generic format (comma-separated):
   codice_istat,numero_sezione
"""
import csv
import re
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

        # Read CSV and auto-detect format
        sections_to_create = []
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
                        denominazione_raw = row.get('UBICAZIONE', '').strip()

                        # Skip generic/useless denominazioni (case-insensitive)
                        generic_terms = [
                            # Generic school terms
                            'scuola',
                            'scuola elementare',
                            'scuola media',
                            'scuola primaria',
                            'scuola materna',
                            'scuola dell\'infanzia',
                            'scuola secondaria',
                            'scuola secondaria di primo grado',
                            'scuola secondaria di secondo grado',
                            'ex scuola elementare',
                            'ex scuola media',
                            'ex scuola materna',
                            'ex scuola primaria',
                            'ex scuole elementari',
                            'ex scuole medie',
                            'scuola media statale',
                            'scuola elementare statale',
                            'scuola materna statale',
                            'scuola primaria statale',
                            'scuola media inferiore',
                            'scuola elementare capoluogo',
                            'scuola elementare e materna',
                            'scuola elementare e media',
                            'edificio scuola elementare',
                            'edificio scolastico',
                            'edifici scolastici',
                            'plesso scolastico',
                            # Other buildings
                            'ex edificio scolastico',
                            'centro sociale',
                            'centro civico',
                            'edificio comunale',
                            'centro per la terza eta',
                            'centro per la terza età',
                            'centro anziani',
                            'sala civica',
                            'locali comunali',
                            'altri fabbricati',
                            'centro polifunzionale',
                            'centro polivalente',
                            'sala polivalente',
                            'biblioteca comunale',
                            'casa sociale',
                            'edificio privato',
                            'centro abitato',
                            # Municipal buildings
                            'municipio',
                            'palazzo comunale',
                            'palazzo municipale',
                            'uffici comunali',
                            'sede comunale',
                            'sede municipale',
                            'casa comunale',
                            'comune',
                            'sala consiliare',
                        ]
                        denominazione = denominazione_raw
                        if denominazione.lower() in generic_terms:
                            denominazione = ''  # Empty, will be matched later
                    else:
                        # Generic format
                        codice_istat = row.get('codice_istat', '').strip()
                        numero_str = row.get('numero_sezione', '').strip()
                        indirizzo = row.get('indirizzo', '').strip() if 'indirizzo' in row else None
                        denominazione = row.get('denominazione', '').strip() if 'denominazione' in row else None

                    if not codice_istat or not numero_str:
                        errors.append(f'Row {row_num}: missing codice_istat or numero_sezione')
                        continue

                    comune = comuni_map.get(codice_istat)
                    if not comune:
                        missing_comuni.add(codice_istat)
                        continue

                    sections_to_create.append(SezioneElettorale(
                        comune=comune,
                        numero=int(numero_str),
                        indirizzo=indirizzo if indirizzo else None,
                        denominazione=denominazione if denominazione else None,
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
