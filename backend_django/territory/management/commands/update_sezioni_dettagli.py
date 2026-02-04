"""
Management command to update electoral sections with additional details
(municipio, indirizzo, denominazione) from CSV files.

CSV format: codice_istat,numero_sezione,municipio_numero,indirizzo,denominazione
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, Municipio, SezioneElettorale


class Command(BaseCommand):
    help = 'Update electoral sections with details from CSV'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path to CSV file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']

        self.stdout.write(f'Reading {file_path}...')

        # Build comune lookup
        comuni_map = {c.codice_istat: c for c in Comune.objects.all()}
        
        # Build municipio lookup
        municipi_map = {}
        for m in Municipio.objects.select_related('comune').all():
            key = (m.comune.codice_istat, m.numero)
            municipi_map[key] = m

        updated = 0
        errors = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):
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
                else:
                    count = SezioneElettorale.objects.filter(
                        comune=comune,
                        numero=numero
                    ).update(**update_data)
                    if count:
                        updated += count

        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} errors'))
            for err in errors[:10]:
                self.stdout.write(f'  - {err}')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY RUN - no changes made'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} sections'))
