"""
Management command to update electoral sections with additional details
(municipio, indirizzo, denominazione) from CSV files.

Supports two CSV formats:
1. Generic: codice_istat,numero_sezione,municipio_numero,indirizzo,denominazione
2. Roma format: SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, Municipio, SezioneElettorale


class Command(BaseCommand):
    help = 'Update electoral sections with details from CSV (auto-detects format)'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path to CSV file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='CSV file encoding (default: utf-8)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        encoding = options['encoding']

        self.stdout.write(f'Reading {file_path} (encoding: {encoding})...')

        # Build comune lookup
        comuni_map = {c.codice_istat: c for c in Comune.objects.all()}
        comuni_by_name = {c.nome.upper(): c for c in Comune.objects.all()}

        # Build municipio lookup
        municipi_map = {}
        for m in Municipio.objects.select_related('comune').all():
            key = (m.comune.codice_istat, m.numero)
            municipi_map[key] = m

        updated = 0
        created = 0
        errors = []

        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)

            # Auto-detect format from columns
            columns = reader.fieldnames
            is_roma_format = 'SEZIONE' in columns and 'COMUNE' in columns and 'MUNICIPIO' in columns

            if is_roma_format:
                self.stdout.write('Detected ROMA format (SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO)')
            else:
                self.stdout.write('Detected GENERIC format (codice_istat,numero_sezione,...)')

            for row_num, row in enumerate(reader, start=2):
                try:
                    if is_roma_format:
                        # Roma format: SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO
                        numero_str = row.get('SEZIONE', '').strip()
                        comune_nome = row.get('COMUNE', '').strip().upper()
                        municipio_num = row.get('MUNICIPIO', '').strip()
                        indirizzo = row.get('INDIRIZZO', '').strip()

                        if not numero_str or not comune_nome:
                            errors.append(f'Row {row_num}: missing SEZIONE or COMUNE')
                            continue

                        comune = comuni_by_name.get(comune_nome)
                        if not comune:
                            errors.append(f'Row {row_num}: comune {comune_nome} not found')
                            continue

                        codice_istat = comune.codice_istat
                        denominazione = None

                    else:
                        # Generic format: codice_istat,numero_sezione,municipio_numero,indirizzo,denominazione
                        codice_istat = row.get('codice_istat', '').strip()
                        numero_str = row.get('numero_sezione', '').strip()
                        municipio_num = row.get('municipio_numero', '').strip()
                        indirizzo = row.get('indirizzo', '').strip()
                        denominazione = row.get('denominazione', '').strip()

                        if not codice_istat or not numero_str:
                            errors.append(f'Row {row_num}: missing codice_istat or numero_sezione')
                            continue

                        comune = comuni_map.get(codice_istat)
                        if not comune:
                            errors.append(f'Row {row_num}: comune {codice_istat} not found')
                            continue

                    try:
                        numero = int(numero_str)
                    except ValueError:
                        errors.append(f'Row {row_num}: invalid numero_sezione')
                        continue

                    # Build update dict
                    update_data = {}
                    if indirizzo:
                        update_data['indirizzo'] = indirizzo
                    if denominazione:
                        update_data['denominazione'] = denominazione
                    if municipio_num:
                        try:
                            mun_num = int(municipio_num)
                            municipio = municipi_map.get((codice_istat, mun_num))
                            if municipio:
                                update_data['municipio'] = municipio
                            else:
                                # Try to create municipio
                                if not dry_run:
                                    municipio, _ = Municipio.objects.get_or_create(
                                        comune=comune,
                                        numero=mun_num,
                                        defaults={'nome': f'Municipio {mun_num}'}
                                    )
                                    municipi_map[(codice_istat, mun_num)] = municipio
                                    update_data['municipio'] = municipio
                        except ValueError:
                            pass

                    if not update_data:
                        continue

                    if dry_run:
                        self.stdout.write(f'Would update {comune.nome} sez. {numero}: {update_data}')
                        updated += 1
                    else:
                        # Try to update first
                        count = SezioneElettorale.objects.filter(
                            comune=comune,
                            numero=numero
                        ).update(**update_data)

                        if count:
                            updated += count
                        else:
                            # Sezione doesn't exist, create it
                            SezioneElettorale.objects.create(
                                comune=comune,
                                numero=numero,
                                **update_data
                            )
                            created += 1

                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')

        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} errors'))
            for err in errors[:10]:
                self.stdout.write(f'  - {err}')
            if len(errors) > 10:
                self.stdout.write(f'  ... and {len(errors) - 10} more errors')

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN - would update {updated} sections'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} sections, created {created} sections'))
