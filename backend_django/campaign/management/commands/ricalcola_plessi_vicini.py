"""
Ricalcola sezioni_vicine per gli RDL geocodificati.

Esegue una save() su ogni RDL per scatenare il post_save signal
che ricalcola i plessi vicini se la lista è vuota.

Usage:
    python manage.py ricalcola_plessi_vicini
    python manage.py ricalcola_plessi_vicini --force
    python manage.py ricalcola_plessi_vicini --comune-id 058091
"""
from django.core.management.base import BaseCommand

from campaign.models import RdlRegistration


class Command(BaseCommand):
    help = "Ricalcola sezioni_vicine per RDL geocodificati (triggera post_save)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--comune-id",
            dest="comune_id",
            help="Codice ISTAT del comune (es. 058091)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ricalcola anche RDL che hanno già sezioni_vicine",
        )

    def handle(self, *args, **options):
        comune_id = options["comune_id"]
        force = options["force"]

        qs = RdlRegistration.objects.filter(
            latitudine__isnull=False,
            longitudine__isnull=False,
        )

        if comune_id:
            qs = qs.filter(comune__codice_istat=comune_id)

        if not force:
            # Solo quelli con sezioni_vicine vuota
            qs = qs.filter(sezioni_vicine=[])

        total = qs.count()
        self.stdout.write(f"RDL da aggiornare: {total}")

        if total == 0:
            self.stdout.write("Niente da fare.")
            return

        updated = 0
        for i, rdl in enumerate(qs.iterator(), 1):
            rdl.save()
            updated += 1
            if i % 50 == 0:
                self.stdout.write(f"  {i}/{total}...")

        self.stdout.write(self.style.SUCCESS(
            f"Completato: {updated} RDL aggiornati"
        ))
