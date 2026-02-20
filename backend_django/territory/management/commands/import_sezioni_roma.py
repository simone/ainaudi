"""
Management command to import/update electoral sections for Roma from CSV.

CSV format (comma-separated):
SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO,

Updates municipio and indirizzo for existing sections. When indirizzo changes,
geocoding fields are invalidated to force re-geocoding. Sections present in DB
but absent from CSV are deleted.

Usage:
    python manage.py import_sezioni_roma
    python manage.py import_sezioni_roma --file=fixtures/roma_sezioni.csv
    python manage.py import_sezioni_roma --dry-run
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

        # Prefetch all Roma sections for efficient lookup
        self.stdout.write('Loading existing Roma sections...')
        sezioni_map = {}
        for sezione in SezioneElettorale.objects.filter(comune=roma).select_related('municipio'):
            sezioni_map[sezione.numero] = sezione

        self.stdout.write(f'Loaded {len(sezioni_map)} existing sections')

        # Track CSV section numbers for deletion check
        csv_numeri = {data['numero'] for data in sections_data}

        # Find sections in DB but not in CSV
        sezioni_to_delete = [
            sezione for numero, sezione in sezioni_map.items()
            if numero not in csv_numeri
        ]

        # Update municipio+indirizzo for existing sections, create missing ones
        skipped_count = 0
        geocode_invalidated_count = 0
        sezioni_to_update = []
        sezioni_to_create = []

        for data in sections_data:
            sezione = sezioni_map.get(data['numero'])

            if not sezione:
                # Sezione not found -> create it
                sezioni_to_create.append(SezioneElettorale(
                    comune=roma,
                    numero=data['numero'],
                    indirizzo=data['indirizzo'],
                    municipio=data['municipio'],
                    is_attiva=True
                ))
                mun_str = f"Municipio {data['municipio'].numero}" if data['municipio'] else "N/A"
                addr_str = data['indirizzo'] if data['indirizzo'] else "N/A"
                self.stdout.write(
                    f'  + CREATE Sezione {data["numero"]:4d} - {mun_str:13s} - {addr_str}'
                )
                continue

            changed = False

            # Update municipio if different
            if sezione.municipio != data['municipio']:
                old_mun_str = f"Mun {sezione.municipio.numero}" if sezione.municipio else "NULL"
                new_mun_str = f"Mun {data['municipio'].numero}" if data['municipio'] else "NULL"
                self.stdout.write(
                    f'  ~ Sezione {data["numero"]:4d}: municipio {old_mun_str} -> {new_mun_str}'
                )
                sezione.municipio = data['municipio']
                changed = True

            # Update indirizzo if different
            old_indirizzo = sezione.indirizzo or ''
            new_indirizzo = data['indirizzo'] or ''
            if old_indirizzo != new_indirizzo:
                self.stdout.write(
                    f'  ~ Sezione {data["numero"]:4d}: indirizzo "{old_indirizzo}" -> "{new_indirizzo}"'
                )
                sezione.indirizzo = data['indirizzo']
                # Invalidate geocoding to force re-geocoding
                sezione.latitudine = None
                sezione.longitudine = None
                sezione.geocoded_at = None
                sezione.geocode_source = ''
                sezione.geocode_quality = ''
                sezione.geocode_place_id = ''
                geocode_invalidated_count += 1
                changed = True

            if changed:
                sezioni_to_update.append(sezione)
            else:
                skipped_count += 1

        updated_count = len(sezioni_to_update)
        created_count = len(sezioni_to_create)
        deleted_count = len(sezioni_to_delete)

        if sezioni_to_delete:
            for sez in sezioni_to_delete:
                self.stdout.write(self.style.WARNING(
                    f'  - DELETE Sezione {sez.numero:4d} (in DB but not in CSV)'
                ))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n[DRY RUN]'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
            self.stdout.write(f'Would create:              {created_count}')
            self.stdout.write(f'Would update:              {updated_count}')
            self.stdout.write(f'  (geocoding invalidated): {geocode_invalidated_count}')
            self.stdout.write(f'Would delete:              {deleted_count}')
            self.stdout.write(f'Unchanged:                 {skipped_count}')
            self.stdout.write(f'Total in CSV:              {len(sections_data)}')
            self.stdout.write(f'Total in DB:               {len(sezioni_map)}')
            return

        # Bulk operations
        with transaction.atomic():
            # Delete sections not in CSV
            if sezioni_to_delete:
                delete_ids = [sez.id for sez in sezioni_to_delete]
                SezioneElettorale.objects.filter(id__in=delete_ids).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'Deleted {deleted_count} sezioni not in CSV'
                ))

            # Create missing sections
            if sezioni_to_create:
                SezioneElettorale.objects.bulk_create(
                    sezioni_to_create,
                    batch_size=500
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Created {created_count} sezioni'
                ))

            # Update existing sections
            if sezioni_to_update:
                SezioneElettorale.objects.bulk_update(
                    sezioni_to_update,
                    ['municipio', 'indirizzo', 'latitudine', 'longitudine',
                     'geocoded_at', 'geocode_source', 'geocode_quality',
                     'geocode_place_id'],
                    batch_size=500
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Updated {updated_count} sezioni'
                ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
        self.stdout.write(f'Sezioni created:           {created_count}')
        self.stdout.write(f'Sezioni updated:           {updated_count}')
        self.stdout.write(f'  (geocoding invalidated): {geocode_invalidated_count}')
        self.stdout.write(f'Sezioni deleted:           {deleted_count}')
        self.stdout.write(f'Unchanged:                 {skipped_count}')
        self.stdout.write(f'Total in CSV:              {len(sections_data)}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Import completed'))
