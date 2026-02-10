"""
Management command to cleanup generic section denominazioni.

Removes useless generic terms like "Edificio Scolastico", "SCUOLA ELEMENTARE", etc.
from SezioneElettorale.denominazione field.

Usage:
    python manage.py cleanup_generic_denominazioni
    python manage.py cleanup_generic_denominazioni --dry-run
    python manage.py cleanup_generic_denominazioni --comune-codice=058091
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from territory.models import SezioneElettorale, Comune


class Command(BaseCommand):
    help = 'Cleanup generic denominazioni from electoral sections'

    # Lista termini generici da rimuovere
    GENERIC_TERMS = [
        'edificio scolastico',
        'ex edificio scolastico',
        'scuola elementare',
        'ex scuola elementare',
        'scuola media',
        'ex scuola media',
        'scuola materna',
        'edifici scolastici',
        'altri fabbricati',
        'centro abitato',
        'uffici comunali',
        'sede comunale',
        'palestra comunale',
    ]

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

        # Filter sezioni with generic denominazioni
        query = Q()
        for term in self.GENERIC_TERMS:
            query |= Q(denominazione__iexact=term)

        sezioni_to_clean = sezioni.filter(query)
        count = sezioni_to_clean.count()

        self.stdout.write(f'Found {count} sezioni with generic denominazioni')

        if count == 0:
            self.stdout.write('Nothing to clean!')
            return

        # Show some examples
        if dry_run:
            self.stdout.write('\nExamples (first 20):')
            for sezione in sezioni_to_clean[:20]:
                self.stdout.write(
                    f'  Sezione {sezione.numero} ({sezione.comune.nome}): '
                    f'"{sezione.denominazione}"'
                )

        if dry_run:
            self.stdout.write('\n[DRY RUN] No changes made')
            self.stdout.write(f'\nWould clean {count} sezioni')
            return

        # Clean
        self.stdout.write('\nCleaning...')

        with transaction.atomic():
            updated = sezioni_to_clean.update(denominazione='')

        self.stdout.write(f'\n✓ Cleaned {updated} sezioni')
        self.stdout.write('\nNext steps:')
        self.stdout.write('  python manage.py match_sezioni_plessi  # Match with real school names')
