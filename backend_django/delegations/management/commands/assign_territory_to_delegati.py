"""
Management command per assegnare il territorio ai delegati.
Assegna il Comune di Roma a tutti i delegati esistenti senza territorio.

Usage:
    python manage.py assign_territory_to_delegati
    python manage.py assign_territory_to_delegati --comune-codice=058091
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from delegations.models import Delegato
from territory.models import Comune


class Command(BaseCommand):
    help = 'Assegna il territorio (Comune di Roma) ai delegati senza territorio configurato'

    def add_arguments(self, parser):
        parser.add_argument(
            '--comune-codice',
            type=str,
            default='058091',
            help='Codice ISTAT del comune da assegnare (default: 058091 = Roma)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forza assegnazione anche se il delegato ha già territori configurati'
        )

    def handle(self, *args, **options):
        comune_codice = options['comune_codice']
        force = options['force']

        self.stdout.write(f"Ricerca comune con codice ISTAT: {comune_codice}...")

        try:
            comune = Comune.objects.get(codice_istat=comune_codice)
            self.stdout.write(self.style.SUCCESS(f"✓ Trovato: {comune.nome} ({comune.provincia.sigla})"))
        except Comune.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f"✗ Comune con codice {comune_codice} non trovato nel database!"
            ))
            self.stdout.write("\nAssicurati di aver importato i comuni:")
            self.stdout.write("  python manage.py import_comuni_istat")
            return

        # Find delegati senza territorio o forzati
        if force:
            delegati = Delegato.objects.all()
            self.stdout.write(f"\nModalità FORCE: aggiorno tutti i {delegati.count()} delegati...")
        else:
            # Delegati senza comuni assegnati
            delegati = Delegato.objects.filter(comuni__isnull=True)
            count = delegati.count()
            self.stdout.write(f"\nTrovati {count} delegati senza comuni assegnati")

        if not delegati.exists():
            self.stdout.write(self.style.WARNING("Nessun delegato da aggiornare"))
            return

        updated_count = 0

        with transaction.atomic():
            for delegato in delegati:
                # Check if already has this comune
                if comune in delegato.comuni.all():
                    self.stdout.write(f"  - {delegato.nome} {delegato.cognome}: già assegnato")
                    continue

                # Assign comune
                delegato.comuni.add(comune)
                updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {delegato.nome} {delegato.cognome} ({delegato.email}): "
                        f"assegnato {comune.nome}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Aggiornati {updated_count} delegati"))
        self.stdout.write(f"  Comune assegnato: {comune.nome} ({comune.codice_istat})")
