"""
Management command to cleanup generic section denominazioni.

Removes denominazioni ONLY IF they are duplicated within the same comune
with different addresses (making them ambiguous).

Logic:
- If Comune A has 3 sections all called "Scuola Elementare" at different addresses,
  clear all 3 (ambiguous)
- If Comune B has 1 section called "Scuola Elementare", keep it (unique identifier)

Usage:
    python manage.py cleanup_generic_denominazioni
    python manage.py cleanup_generic_denominazioni --dry-run
    python manage.py cleanup_generic_denominazioni --comune-codice=058091
"""
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import SezioneElettorale, Comune


class Command(BaseCommand):
    help = 'Cleanup duplicate denominazioni from electoral sections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--comune-codice',
            type=str,
            help='Filtra per codice ISTAT comune (es: 058091 = Roma)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually cleaning'
        )

    def handle(self, *args, **options):
        comune_codice = options.get('comune_codice')
        dry_run = options['dry_run']

        # Build queryset
        sezioni = SezioneElettorale.objects.all()

        if comune_codice:
            try:
                comune = Comune.objects.get(codice_istat=comune_codice)
                sezioni = sezioni.filter(comune=comune)
                self.stdout.write(f'Filtering by comune: {comune.nome}')
            except Comune.DoesNotExist:
                self.stderr.write(f'Comune {comune_codice} not found!')
                return

        # Group sections by comune
        self.stdout.write('Analyzing denominazioni by comune...')

        sezioni_by_comune = defaultdict(list)
        for sezione in sezioni.select_related('comune'):
            if sezione.denominazione:  # Only consider non-empty denominazioni
                sezioni_by_comune[sezione.comune_id].append(sezione)

        # Find duplicate denominazioni within each comune
        sezioni_to_clean = []

        for comune_id, sezioni_list in sezioni_by_comune.items():
            # Group by denominazione (case-insensitive)
            denom_groups = defaultdict(list)
            for sezione in sezioni_list:
                denom = sezione.denominazione.lower().strip()
                if denom:
                    denom_groups[denom].append(sezione)

            # Mark as duplicates if same denominazione appears multiple times
            # with different addresses
            for denom, group in denom_groups.items():
                if len(group) > 1:
                    # Check if they have different addresses
                    addresses = set()
                    for s in group:
                        addr = s.indirizzo.strip().lower() if s.indirizzo else ''
                        if addr:
                            addresses.add(addr)

                    # If multiple sections with same denom but different addresses -> duplicate
                    if len(addresses) > 1:
                        sezioni_to_clean.extend(group)

        count = len(sezioni_to_clean)
        self.stdout.write(f'Found {count} sezioni with duplicate denominazioni')

        if count == 0:
            self.stdout.write('Nothing to clean!')
            return

        # Show some examples
        if dry_run or count <= 50:
            self.stdout.write('\nExamples:')
            for sezione in sezioni_to_clean[:20]:
                self.stdout.write(
                    f'  {sezione.comune.nome} - Sez {sezione.numero}: '
                    f'"{sezione.denominazione}" @ {sezione.indirizzo or "N/A"}'
                )

        if dry_run:
            self.stdout.write('\n[DRY RUN] No changes made')
            self.stdout.write(f'\nWould clean {count} sezioni')
            return

        # Clean
        self.stdout.write('\nCleaning...')

        with transaction.atomic():
            updated = 0
            for sezione in sezioni_to_clean:
                sezione.denominazione = ''
                sezione.save(update_fields=['denominazione'])
                updated += 1

        self.stdout.write(f'\n✓ Cleaned {updated} sezioni')
        self.stdout.write('\nNext steps:')
        self.stdout.write('  python manage.py match_sezioni_plessi  # Match with real school names')
