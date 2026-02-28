#!/usr/bin/env python3
"""
Ricalcola sezioni_vicine solo per RDL che hanno tra i vicini delle sezioni spostate.

Sezioni spostate nel 2026:
- 7 eliminate (9001-9007)
- 27 con indirizzo cambiato
- 3 con indirizzo + municipio cambiati

Usage:
    python manage.py ricalcola_rdl_sezioni_spostate
    python manage.py ricalcola_rdl_sezioni_spostate --comune-id 058091
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from campaign.models import RdlRegistration


# Sezioni che sono state spostate/eliminate nel 2026
SEZIONI_SPOSTATE = {
    9001, 9002, 9003, 9004, 9005, 9006, 9007,  # Eliminate
    173, 174, 175,  # Indirizzo cambiato
    1393, 1394, 1395, 1396,
    1714, 1715, 1717,
    1927, 1928, 1929, 1931, 1932,
    2071, 2072, 2073, 2074, 2075, 2097, 2280, 2405, 2475, 2476, 2477, 2554,
    2569, 2571, 2579,  # Indirizzo + municipio cambiati
}


class Command(BaseCommand):
    help = "Ricalcola sezioni_vicine per RDL che hanno sezioni spostate nel 2026"

    def add_arguments(self, parser):
        parser.add_argument(
            "--comune-id",
            dest="comune_id",
            help="Codice ISTAT del comune (es. 058091 per Roma)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quanti RDL verrebbero aggiornati senza farlo",
        )

    def handle(self, *args, **options):
        comune_id = options["comune_id"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Cercando RDL con sezioni spostate...")
        self.stdout.write(f"Sezioni spostate: {SEZIONI_SPOSTATE}")
        self.stdout.write()

        # Filtra RDL che hanno sezioni_vicine non vuote
        qs = RdlRegistration.objects.filter(
            latitudine__isnull=False,
            longitudine__isnull=False,
        ).exclude(sezioni_vicine=[])

        if comune_id:
            qs = qs.filter(comune__codice_istat=comune_id)

        # Conta RDL che hanno sezioni spostate nei vicini
        rdl_da_aggiornare = []
        for rdl in qs:
            sezioni_vicine = rdl.sezioni_vicine or []
            # Estrai i numeri sezione dai vicini
            numeri_sezioni = set()
            for plesso in sezioni_vicine:
                if 'sezioni' in plesso:
                    numeri_sezioni.update(plesso.get('sezioni', []))

            # Se ha almeno una sezione spostata, aggiungi alla lista
            if numeri_sezioni & SEZIONI_SPOSTATE:
                rdl_da_aggiornare.append(rdl)

        total = len(rdl_da_aggiornare)
        self.stdout.write(self.style.SUCCESS(f"RDL con sezioni spostate: {total}"))

        if total == 0:
            self.stdout.write("Niente da fare.")
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] Nessun cambiamento effettuato."))
            self.stdout.write()
            self.stdout.write("RDL che verrebbero aggiornati:")
            for i, rdl in enumerate(rdl_da_aggiornare[:20], 1):
                sezioni_spostate = set()
                sezioni_vicine = rdl.sezioni_vicine or []
                for plesso in sezioni_vicine:
                    numeri = set(plesso.get('sezioni', []))
                    sezioni_spostate.update(numeri & SEZIONI_SPOSTATE)
                self.stdout.write(f"  {i}. {rdl.email} - Sezioni spostate: {sorted(sezioni_spostate)}")
            if total > 20:
                self.stdout.write(f"  ... e {total - 20} altri RDL")
            self.stdout.write()
            self.stdout.write(f"Per aggiornare veramente, esegui senza --dry-run")
            return

        # Aggiorna i RDL (scatena il post_save signal che ricalcola i plessi)
        updated = 0
        for i, rdl in enumerate(rdl_da_aggiornare, 1):
            rdl.save()
            updated += 1
            if i % 50 == 0:
                self.stdout.write(f"  {i}/{total}...")

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(
            f"Completato: {updated} RDL aggiornati"
        ))
