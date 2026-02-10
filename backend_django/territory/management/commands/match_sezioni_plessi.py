"""
Management command to match electoral sections with school buildings (plessi)
from SCUANA CSV files (Anagrafe Edilizia Scolastica).

This enriches section data with more precise addresses and additional info.

Usage:
    python manage.py match_sezioni_plessi --stat fixtures/SCUANAGRAFESTAT*.csv --par fixtures/SCUANAGRAFEPAR*.csv
"""
import csv
import re
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune, SezioneElettorale


class Command(BaseCommand):
    help = 'Match electoral sections with school buildings from SCUANA CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stat',
            required=True,
            help='Path to SCUANAGRAFESTAT CSV file'
        )
        parser.add_argument(
            '--par',
            required=False,
            help='Path to SCUANAGRAFEPAR CSV file'
        )
        parser.add_argument(
            '--aut-stat',
            required=False,
            help='Path to SCUANAAUTSTAT CSV file'
        )
        parser.add_argument(
            '--aut-par',
            required=False,
            help='Path to SCUANAAUTPAR CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show matches without updating database'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.6,
            help='Similarity threshold (0.0-1.0, default: 0.6)'
        )
        parser.add_argument(
            '--comune',
            type=str,
            help='Process only sections from specific comune (codice_istat)'
        )

    def clean_text(self, text):
        """Normalize text for comparison."""
        if not text:
            return ''
        # Convert to uppercase, remove extra spaces
        text = text.upper().strip()
        # Remove common prefixes
        text = re.sub(r'^(SCUOLA|SC\.|PLESSO|EDIFICIO|SEDE)\s+', '', text)
        # Normalize street types
        text = text.replace('VIA ', 'V.').replace('VIALE ', 'VLE ').replace('PIAZZA ', 'P.')
        return text

    def similarity(self, a, b):
        """Calculate similarity between two strings (0.0-1.0)."""
        return SequenceMatcher(None, self.clean_text(a), self.clean_text(b)).ratio()

    def load_plessi(self, file_path, file_type):
        """Load plessi from CSV file."""
        plessi = []

        if not file_path:
            return plessi

        self.stdout.write(f'Loading {file_type} from {file_path}...')

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get codice belfiore (comune)
                codice_belfiore = row.get('CODICECOMUNESCUOLA', '').strip()

                # Get plesso info
                denominazione = row.get('DENOMINAZIONESCUOLA', '').strip()
                indirizzo = row.get('INDIRIZZOSCUOLA', '').strip()
                cap = row.get('CAPSCUOLA', '').strip()

                if not codice_belfiore or not denominazione:
                    continue

                plessi.append({
                    'codice_belfiore': codice_belfiore,
                    'denominazione': denominazione,
                    'indirizzo': indirizzo,
                    'cap': cap,
                    'tipo': file_type
                })

        self.stdout.write(f'  Loaded {len(plessi)} plessi')
        return plessi

    def build_index(self, plessi_list):
        """Build index: codice_belfiore -> [plessi]."""
        index = {}
        for plesso in plessi_list:
            codice = plesso['codice_belfiore']
            if codice not in index:
                index[codice] = []
            index[codice].append(plesso)
        return index

    def find_best_match(self, sezione, plessi, threshold):
        """Find best matching plesso for a section."""
        best_match = None
        best_score = 0.0

        # Try matching by denomination
        if sezione.denominazione:
            for plesso in plessi:
                score = self.similarity(sezione.denominazione, plesso['denominazione'])
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = plesso

        # If no good match on denomination, try address
        if not best_match and sezione.indirizzo:
            for plesso in plessi:
                if plesso['indirizzo']:
                    score = self.similarity(sezione.indirizzo, plesso['indirizzo'])
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = plesso

        return best_match, best_score

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']
        comune_filter = options.get('comune')

        # Load all plessi from CSV files
        all_plessi = []
        all_plessi.extend(self.load_plessi(options['stat'], 'STAT'))

        if options.get('par'):
            all_plessi.extend(self.load_plessi(options['par'], 'PAR'))
        if options.get('aut_stat'):
            all_plessi.extend(self.load_plessi(options['aut_stat'], 'AUT_STAT'))
        if options.get('aut_par'):
            all_plessi.extend(self.load_plessi(options['aut_par'], 'AUT_PAR'))

        self.stdout.write(f'Total plessi loaded: {len(all_plessi)}')

        # Build codice_catastale -> codice_belfiore mapping
        comuni_belfiore_map = {}
        for comune in Comune.objects.all():
            comuni_belfiore_map[comune.codice_catastale] = comune

        # Build index: codice_belfiore -> [plessi]
        plessi_index = self.build_index(all_plessi)
        self.stdout.write(f'Indexed plessi for {len(plessi_index)} comuni')

        # Process sections
        sezioni_query = SezioneElettorale.objects.select_related('comune')

        if comune_filter:
            sezioni_query = sezioni_query.filter(comune__codice_istat=comune_filter)

        sezioni = sezioni_query.all()
        self.stdout.write(f'Processing {sezioni.count()} sections...')

        matched = 0
        updated = 0
        skipped = 0

        for sezione in sezioni:
            # Get codice belfiore for this comune
            codice_belfiore = sezione.comune.codice_catastale

            # Get plessi for this comune
            plessi_comune = plessi_index.get(codice_belfiore, [])

            if not plessi_comune:
                skipped += 1
                continue

            # Find best match
            best_match, score = self.find_best_match(sezione, plessi_comune, threshold)

            if best_match:
                matched += 1

                if dry_run:
                    self.stdout.write(
                        f'[{score:.2f}] Sez {sezione.comune.nome} #{sezione.numero}: '
                        f'{sezione.denominazione or sezione.indirizzo} → '
                        f'{best_match["denominazione"]} ({best_match["indirizzo"]})'
                    )
                else:
                    # Update section with plesso data
                    changed = False

                    # Update denomination if better
                    if not sezione.denominazione or score > 0.8:
                        sezione.denominazione = best_match['denominazione']
                        changed = True

                    # Update address if better
                    if best_match['indirizzo'] and (not sezione.indirizzo or score > 0.8):
                        sezione.indirizzo = best_match['indirizzo']
                        changed = True

                    if changed:
                        sezione.save()
                        updated += 1
            else:
                skipped += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Matching complete:'))
        self.stdout.write(f'  Matched: {matched}')
        if not dry_run:
            self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Skipped: {skipped}')
