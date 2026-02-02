"""
Management command to import Italian comuni from ISTAT data.

Downloads the official ISTAT CSV and creates/updates Comune records.
Requires Regione and Provincia to already exist in the database.

Usage:
    python manage.py import_comuni_istat
    python manage.py import_comuni_istat --dry-run
"""
import csv
import io
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from territorio.models import Regione, Provincia, Comune


# ISTAT CSV URL (updated periodically by ISTAT)
ISTAT_CSV_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"


class Command(BaseCommand):
    help = 'Import Italian comuni from ISTAT official data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Use local CSV file instead of downloading from ISTAT',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        local_file = options.get('file')

        self.stdout.write("Loading existing province...")

        # Build lookup maps for province by codice_istat
        province_map = {}
        for provincia in Provincia.objects.select_related('regione').all():
            # ISTAT uses 3-digit codes, our DB might have 2 or 3
            province_map[provincia.codice_istat] = provincia
            province_map[provincia.codice_istat.zfill(3)] = provincia
            # Also map by sigla for fallback
            province_map[provincia.sigla] = provincia

        self.stdout.write(f"Loaded {len(province_map) // 3} province")

        # Download or read ISTAT CSV
        if local_file:
            self.stdout.write(f"Reading from local file: {local_file}")
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            self.stdout.write(f"Downloading from ISTAT: {ISTAT_CSV_URL}")
            try:
                response = requests.get(ISTAT_CSV_URL, timeout=30)
                response.raise_for_status()
                # ISTAT CSV is usually in ISO-8859-1 encoding
                content = response.content.decode('latin-1')
            except requests.RequestException as e:
                self.stderr.write(f"Error downloading ISTAT data: {e}")
                return

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content), delimiter=';')

        # Print available columns for debugging
        self.stdout.write(f"CSV columns: {reader.fieldnames}")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        comuni_to_create = []
        comuni_to_update = []

        for row in reader:
            try:
                # ISTAT CSV column names (may vary slightly)
                # Try different possible column names
                codice_provincia = (
                    row.get('Codice Provincia (Storico)(1)') or
                    row.get('Codice Provincia') or
                    row.get('Codice dell\'Unità territoriale sovracomunale \n(valido a fini statistici)') or
                    row.get('Codice Provincia (formato numerico)') or
                    ''
                ).strip()

                sigla_provincia = (
                    row.get('Sigla automobilistica') or
                    row.get('Sigla') or
                    ''
                ).strip()

                # Codice Comune formato numerico is the full 6-digit ISTAT code
                codice_istat = (
                    row.get('Codice Comune formato numerico') or
                    row.get('Codice Comune') or
                    ''
                ).strip()

                codice_catastale = (
                    row.get('Codice Catastale del comune') or
                    row.get('Codice Catastale') or
                    ''
                ).strip()

                nome_comune = (
                    row.get('Denominazione in italiano') or
                    row.get('Denominazione (Italiana e straniera)') or
                    row.get('Denominazione') or
                    ''
                ).strip()

                # Skip empty rows
                if not nome_comune or not codice_istat:
                    continue

                # Find provincia
                provincia = None
                if sigla_provincia and sigla_provincia in province_map:
                    provincia = province_map[sigla_provincia]
                elif codice_provincia:
                    # Try with and without padding
                    provincia = province_map.get(codice_provincia) or province_map.get(codice_provincia.zfill(3))

                if not provincia:
                    errors.append(f"Provincia not found for {nome_comune} (cod: {codice_provincia}, sigla: {sigla_provincia})")
                    skipped_count += 1
                    continue

                # Ensure codice_istat is exactly 6 digits
                codice_istat = codice_istat.zfill(6)[:6]

                if dry_run:
                    self.stdout.write(f"Would import: {nome_comune} ({sigla_provincia}) - {codice_istat}")
                    created_count += 1
                else:
                    # Check if exists
                    existing = Comune.objects.filter(codice_catastale=codice_catastale).first()

                    if existing:
                        # Update
                        existing.nome = nome_comune
                        existing.provincia = provincia
                        existing.codice_istat = codice_istat
                        comuni_to_update.append(existing)
                        updated_count += 1
                    else:
                        # Create new
                        comuni_to_create.append(Comune(
                            codice_istat=codice_istat,
                            codice_catastale=codice_catastale,
                            nome=nome_comune,
                            provincia=provincia,
                        ))
                        created_count += 1

            except Exception as e:
                errors.append(f"Error processing row: {e} - {row}")
                skipped_count += 1

        # Bulk create/update
        if not dry_run:
            with transaction.atomic():
                if comuni_to_create:
                    Comune.objects.bulk_create(comuni_to_create, ignore_conflicts=True)
                    self.stdout.write(f"Created {len(comuni_to_create)} comuni")

                if comuni_to_update:
                    Comune.objects.bulk_update(comuni_to_update, ['nome', 'provincia', 'codice_istat'])
                    self.stdout.write(f"Updated {len(comuni_to_update)} comuni")

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Import complete:"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")

        if errors[:10]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("First 10 errors:"))
            for err in errors[:10]:
                self.stdout.write(f"  - {err}")
            if len(errors) > 10:
                self.stdout.write(f"  ... and {len(errors) - 10} more errors")
