#!/usr/bin/env python3
"""
Django management command to update sections from 2026 CSV.

Updates municipio and indirizzo for changed sections, deletes removed sections.
"""

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from territory.models import SezioneElettorale, Comune, Municipio


class Command(BaseCommand):
    help = 'Update electoral sections from 2026 CSV (indirizzo and municipio)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='fixtures/sezioni_2026.csv',
            help='Path to sezioni_2026.csv file (relative to backend_django directory)',
        )
        parser.add_argument(
            '--delete-removed',
            action='store_true',
            help='Delete sections that are no longer in the CSV (sections 9001-9007)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options['csv_path']
        delete_removed = options['delete_removed']
        dry_run = options['dry_run']

        # Get Rome
        try:
            roma = Comune.objects.get(nome__iexact='ROMA')
        except Comune.DoesNotExist:
            raise CommandError('Comune ROMA non trovato')

        # Read CSV
        self.stdout.write(f"Lettura CSV: {csv_path}")
        sezioni_csv = {}
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    num = int(row['numero'])
                    sezioni_csv[num] = {
                        'via': row['via'].strip(),
                        'municipio': int(row['municipio']),
                    }
        except FileNotFoundError:
            raise CommandError(f'File non trovato: {csv_path}')
        except Exception as e:
            raise CommandError(f'Errore lettura CSV: {e}')

        self.stdout.write(f"✓ Letto CSV: {len(sezioni_csv)} sezioni")

        # Get current sections in DB
        sezioni_db = {}
        for sezione in SezioneElettorale.objects.filter(comune=roma):
            sezioni_db[sezione.numero] = sezione

        self.stdout.write(f"✓ DB contiene: {len(sezioni_db)} sezioni")

        # Sections to delete (in DB but not in CSV)
        to_delete = sorted(set(sezioni_db.keys()) - set(sezioni_csv.keys()))

        # Sections to update (in both)
        to_update = []
        for num in sorted(set(sezioni_db.keys()) & set(sezioni_csv.keys())):
            sezione = sezioni_db[num]
            csv_data = sezioni_csv[num]

            # Check if needs update
            needs_update = False
            changes = {}

            # Check indirizzo
            current_via = sezione.indirizzo or ''
            new_via = csv_data['via']
            if current_via.upper() != new_via.upper():
                needs_update = True
                changes['indirizzo'] = (current_via, new_via)

            # Check municipio
            csv_mun_num = csv_data['municipio']
            try:
                csv_municipio = Municipio.objects.get(numero=csv_mun_num, comune=roma)
            except Municipio.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Sezione {num}: Municipio {csv_mun_num} non trovato nel DB"
                    )
                )
                continue

            current_mun = sezione.municipio
            if current_mun != csv_municipio:
                needs_update = True
                changes['municipio'] = (current_mun.numero if current_mun else None, csv_mun_num)

            if needs_update:
                to_update.append({
                    'sezione': sezione,
                    'changes': changes,
                    'csv_data': csv_data,
                })

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"\n{'='*80}"))
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(self.style.SUCCESS(f"{'='*80}"))
        self.stdout.write(f"Sezioni da aggiornare: {len(to_update)}")
        self.stdout.write(f"Sezioni da eliminare:  {len(to_delete)}")
        self.stdout.write()

        if to_delete:
            self.stdout.write(self.style.WARNING(f"SEZIONI DA ELIMINARE ({len(to_delete)}):"))
            for num in to_delete:
                sezione = sezioni_db[num]
                self.stdout.write(
                    self.style.WARNING(f"  Sezione {num}: {sezione.indirizzo} (Mun. {sezione.municipio})")
                )
            self.stdout.write()

        if to_update:
            self.stdout.write(f"SEZIONI DA AGGIORNARE ({len(to_update)}):")
            for item in to_update:
                sezione = item['sezione']
                changes = item['changes']
                self.stdout.write(f"  Sezione {sezione.numero}:")
                for field, (old, new) in changes.items():
                    self.stdout.write(f"    {field}: {old} → {new}")
            self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: Nessun cambiamento effettuato"))
            return

        # Ask for confirmation
        if not (to_update or to_delete):
            self.stdout.write(self.style.SUCCESS("✓ Nessun aggiornamento necessario"))
            return

        confirm = input(f"Proseguire con aggiornamento di {len(to_update) + len(to_delete)} sezioni? (s/n): ")
        if confirm.lower() != 's':
            self.stdout.write(self.style.WARNING("Operazione annullata"))
            return

        # Apply updates
        updated_count = 0
        for item in to_update:
            sezione = item['sezione']
            csv_data = item['csv_data']

            # Update indirizzo
            sezione.indirizzo = csv_data['via']

            # Update municipio
            try:
                sezione.municipio = Municipio.objects.get(
                    numero=csv_data['municipio'],
                    comune=roma
                )
            except Municipio.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Sezione {sezione.numero}: Municipio {csv_data['municipio']} non trovato"
                    )
                )
                continue

            sezione.save()
            updated_count += 1
            self.stdout.write(f"✓ Aggiornata sezione {sezione.numero}")

        # Apply deletions
        deleted_count = 0
        if delete_removed:
            for num in to_delete:
                sezione = sezioni_db[num]
                sezione.delete()
                deleted_count += 1
                self.stdout.write(f"✗ Eliminata sezione {num}")

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(f"{'='*80}"))
        self.stdout.write(self.style.SUCCESS("OPERAZIONE COMPLETATA"))
        self.stdout.write(self.style.SUCCESS(f"{'='*80}"))
        self.stdout.write(f"✓ Aggiornate:  {updated_count} sezioni")
        self.stdout.write(f"✗ Eliminate:   {deleted_count} sezioni")
        self.stdout.write()
