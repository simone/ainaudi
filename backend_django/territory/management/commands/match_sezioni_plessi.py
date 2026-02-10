"""
Management command to match electoral sections with school buildings (plessi)
based on address similarity.

Uses CSV from MIUR with school data (SCUANAGRAFESTAT*.csv).

Usage:
    python manage.py match_sezioni_plessi
    python manage.py match_sezioni_plessi --comune-codice=058091
    python manage.py match_sezioni_plessi --dry-run
"""
import csv
import re
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, SezioneElettorale


class Command(BaseCommand):
    help = 'Match electoral sections with school buildings based on address'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='fixtures/SCUANAGRAFESTAT20252620250901.csv',
            help='Path to school CSV file'
        )
        parser.add_argument(
            '--comune-codice',
            type=str,
            default='058091',
            help='Codice ISTAT del comune (default: 058091 = Roma)'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.75,
            help='Similarity threshold (0.0-1.0, default: 0.75)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show matches without updating'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if denominazione exists'
        )

    def normalize_address(self, address):
        """Normalize address for comparison."""
        if not address:
            return ''

        addr = address.lower().strip()
        addr = re.sub(r'\broma\b', '', addr, flags=re.IGNORECASE)

        replacements = {
            r'\bv\.': 'via',
            r'\bv\.le': 'viale',
            r'\bp\.za': 'piazza',
            r'\bl\.go': 'largo',
        }
        for pattern, repl in replacements.items():
            addr = re.sub(pattern, repl, addr, flags=re.IGNORECASE)

        addr = re.sub(r'[,.\'\"]', ' ', addr)
        addr = re.sub(r'\b\d+[a-z]?\b', '', addr)
        addr = re.sub(r'\s+', ' ', addr).strip()

        return addr

    def similarity(self, str1, str2):
        """Calculate similarity ratio (0.0-1.0)."""
        return SequenceMatcher(None, str1, str2).ratio()

    def handle(self, *args, **options):
        file_path = options['file']
        comune_codice = options['comune_codice']
        threshold = options['threshold']
        dry_run = options['dry_run']
        force = options['force']

        try:
            comune = Comune.objects.get(codice_istat=comune_codice)
            self.stdout.write(f'Comune: {comune.nome}')
        except Comune.DoesNotExist:
            self.stderr.write(f'Comune {comune_codice} not found!')
            return

        self.stdout.write(f'Loading schools from {file_path}...')

        schools = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row.get('CODICECOMUNESCUOLA', '').strip() != comune_codice:
                    continue

                denom = row.get('DENOMINAZIONESCUOLA', '').strip()
                indirizzo = row.get('INDIRIZZOSCUOLA', '').strip()

                if denom and indirizzo:
                    schools.append({
                        'denominazione': denom,
                        'indirizzo': indirizzo,
                        'indirizzo_normalized': self.normalize_address(indirizzo)
                    })

        self.stdout.write(f'Loaded {len(schools)} schools')

        if not schools:
            self.stderr.write('No schools found!')
            return

        if force:
            sezioni = SezioneElettorale.objects.filter(
                comune=comune, is_attiva=True
            ).exclude(indirizzo__isnull=True).exclude(indirizzo='')
        else:
            sezioni = SezioneElettorale.objects.filter(
                comune=comune, is_attiva=True
            ).filter(
                denominazione__isnull=True
            ).exclude(indirizzo__isnull=True).exclude(indirizzo='') | \
            SezioneElettorale.objects.filter(
                comune=comune, is_attiva=True, denominazione=''
            ).exclude(indirizzo__isnull=True).exclude(indirizzo='')

        self.stdout.write(f'Processing {sezioni.count()} sezioni...')

        matched_count = 0
        unmatched_count = 0
        matches = []

        for sezione in sezioni:
            sezione_addr_norm = self.normalize_address(sezione.indirizzo)

            if not sezione_addr_norm:
                unmatched_count += 1
                continue

            best_match = None
            best_score = 0.0

            for school in schools:
                score = self.similarity(sezione_addr_norm, school['indirizzo_normalized'])

                if score > best_score:
                    best_score = score
                    best_match = school

            if best_match and best_score >= threshold:
                matches.append({
                    'sezione': sezione,
                    'school': best_match,
                    'score': best_score
                })
                matched_count += 1

                if dry_run:
                    self.stdout.write(
                        f'  Match ({best_score:.2f}): Sezione {sezione.numero} → '
                        f'"{best_match["denominazione"]}"'
                    )
            else:
                unmatched_count += 1

        self.stdout.write(f'\nMatched:   {matched_count}')
        self.stdout.write(f'Unmatched: {unmatched_count}')

        if dry_run:
            self.stdout.write('\n[DRY RUN] No changes made')
            return

        self.stdout.write('\nUpdating database...')

        updated_count = 0
        with transaction.atomic():
            for match in matches:
                sezione = match['sezione']
                school = match['school']
                sezione.denominazione = school['denominazione']
                sezione.save(update_fields=['denominazione'])
                updated_count += 1

        self.stdout.write(f'\n✓ Updated {updated_count} sezioni')
