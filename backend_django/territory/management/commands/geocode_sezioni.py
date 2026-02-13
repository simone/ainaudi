"""
Geocode electoral sections using Google Geocoding API.

Works in two phases:
1. PROPAGATE: sections sharing an address with already-geocoded sections
   get coordinates copied (zero API calls).
2. GEOCODE: resolve --limit unique addresses via API, then update all
   sections at those addresses.

So --limit 5 means 5 API calls, but could update 25 sections if each
address has 5 sections.

Usage:
    python manage.py geocode_sezioni --provincia RM --limit 500 --dry-run
    python manage.py geocode_sezioni --provincia RM --limit 5
    python manage.py geocode_sezioni --provincia RM --force
    python manage.py geocode_sezioni --comune-id 058091 --limit 100
"""
import re
import time
import unicodedata
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from territory.geocoding import build_section_address, geocode_address
from territory.models import SezioneElettorale


def _normalize_key(address):
    """Normalize address for grouping/deduplication."""
    if not address:
        return ""
    s = str(address).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class Command(BaseCommand):
    help = (
        "Geocode electoral sections via Google Geocoding API. "
        "--limit controls unique addresses resolved, not individual sections."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--provincia",
            default="RM",
            help="Sigla provincia da filtrare (default: RM)",
        )
        parser.add_argument(
            "--comune-id",
            dest="comune_id",
            help="Codice ISTAT del comune (es. 058091). Se specificato, --provincia viene ignorato.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Numero massimo di indirizzi unici da geocodificare (default: 500)",
        )
        parser.add_argument(
            "--sleep-ms",
            type=int,
            default=120,
            help="Pausa tra richieste API in millisecondi (default: 120)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra risultati senza scrivere nel database",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ricalcola anche sezioni già geocodificate",
        )

    def handle(self, *args, **options):
        provincia = options["provincia"]
        comune_id = options["comune_id"]
        limit = options["limit"]
        sleep_ms = options["sleep_ms"]
        dry_run = options["dry_run"]
        force = options["force"]

        qs = SezioneElettorale.objects.exclude(
            indirizzo__isnull=True
        ).exclude(
            indirizzo=""
        ).select_related("comune", "comune__provincia")

        if comune_id:
            qs = qs.filter(comune__codice_istat=comune_id)
            self.stdout.write(f"Geocoding sezioni comune {comune_id}...\n")
        else:
            qs = qs.filter(comune__provincia__sigla=provincia)
            self.stdout.write(f"Geocoding sezioni provincia {provincia}...\n")

        all_sezioni = list(qs)

        # ── Phase 1: propagate from already-geocoded siblings ──────────
        propagated = self._propagate(all_sezioni, dry_run)

        # ── Phase 2: group remaining non-geocoded by unique address ────
        if force:
            pending = [s for s in all_sezioni]
        else:
            pending = [s for s in all_sezioni if s.latitudine is None]

        # Group by normalized address
        addr_groups = defaultdict(list)
        for s in pending:
            key = _normalize_key(build_section_address(s))
            addr_groups[key].append(s)

        unique_addrs = list(addr_groups.keys())
        total_unique = len(unique_addrs)
        to_resolve = unique_addrs[:limit]

        self.stdout.write(
            f"Fase 2: {total_unique} indirizzi unici senza coordinate "
            f"({len(pending)} sezioni), limit: {limit}\n"
        )

        if not to_resolve:
            self.stdout.write("Nessun indirizzo da geocodificare.")
            self._summary(propagated, 0, 0, 0)
            return

        geocoded_count = self._geocode_addresses(
            to_resolve, addr_groups, sleep_ms, dry_run
        )

        if not dry_run:
            self._summary(
                propagated,
                geocoded_count["ok_sections"],
                geocoded_count["fail_addrs"],
                geocoded_count["api_calls"],
            )

    # ────────────────────────────────────────────────────────────────────

    def _propagate(self, all_sezioni, dry_run):
        """
        Copy coordinates from geocoded sections to non-geocoded siblings
        sharing the same address. Returns number of sections updated.
        """
        # Build index: normalized_address → list of sezioni
        by_addr = defaultdict(list)
        for s in all_sezioni:
            key = _normalize_key(build_section_address(s))
            by_addr[key].append(s)

        propagated = 0
        now = timezone.now()

        for key, group in by_addr.items():
            # Find a geocoded donor in this group
            donor = None
            for s in group:
                if s.latitudine is not None and s.longitudine is not None:
                    donor = s
                    break

            if donor is None:
                continue

            # Propagate to siblings without coordinates
            for s in group:
                if s.latitudine is not None:
                    continue

                if dry_run:
                    self.stdout.write(
                        f"  [propaga] Sez. {s.numero} {s.comune.nome} "
                        f"<- Sez. {donor.numero} "
                        f"({donor.latitudine}, {donor.longitudine})"
                    )
                else:
                    s.latitudine = donor.latitudine
                    s.longitudine = donor.longitudine
                    s.geocoded_at = now
                    s.geocode_source = donor.geocode_source or "propagated"
                    s.geocode_quality = donor.geocode_quality
                    s.geocode_place_id = donor.geocode_place_id
                    s.save(update_fields=[
                        "latitudine", "longitudine",
                        "geocoded_at", "geocode_source",
                        "geocode_quality", "geocode_place_id",
                    ])
                propagated += 1

        label = "DRY RUN " if dry_run else ""
        self.stdout.write(
            f"Fase 1: {label}{propagated} sezioni propagate "
            f"da siblings geocodificati\n"
        )
        return propagated

    def _geocode_addresses(self, addr_keys, addr_groups, sleep_ms, dry_run):
        """
        Geocode unique addresses via API and update all sections at each address.
        """
        sleep_sec = sleep_ms / 1000.0
        total = len(addr_keys)
        pad = len(str(total))

        ok_sections = 0
        fail_addrs = 0
        api_calls = 0
        now = timezone.now()

        for i, key in enumerate(addr_keys, 1):
            sections = addr_groups[key]
            # Use first section to build the display address
            address = build_section_address(sections[0])
            n_sez = len(sections)
            sez_nums = ", ".join(str(s.numero) for s in sections[:5])
            if n_sez > 5:
                sez_nums += f" (+{n_sez - 5})"

            if dry_run:
                self.stdout.write(
                    f"[{i:>{pad}}/{total}] {address} "
                    f"({n_sez} sez: {sez_nums}) [DRY RUN]"
                )
                ok_sections += n_sez
                continue

            result = geocode_address(address)
            api_calls += 1

            if result is None:
                fail_addrs += 1
                self.stderr.write(
                    f"[{i:>{pad}}/{total}] {address} "
                    f"({n_sez} sez) -> FALLITA"
                )
            else:
                lat, lon, place_id, location_type = result

                for s in sections:
                    s.latitudine = lat
                    s.longitudine = lon
                    s.geocoded_at = now
                    s.geocode_source = "google"
                    s.geocode_quality = location_type
                    s.geocode_place_id = place_id
                    s.save(update_fields=[
                        "latitudine", "longitudine",
                        "geocoded_at", "geocode_source",
                        "geocode_quality", "geocode_place_id",
                    ])

                ok_sections += n_sez
                self.stdout.write(
                    f"[{i:>{pad}}/{total}] {address} "
                    f"-> {lat}, {lon} ({location_type}) "
                    f"[{n_sez} sez: {sez_nums}]"
                )

            if sleep_sec > 0 and i < total:
                time.sleep(sleep_sec)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN: {total} indirizzi, {ok_sections} sezioni"
            ))

        return {
            "ok_sections": ok_sections,
            "fail_addrs": fail_addrs,
            "api_calls": api_calls,
        }

    def _summary(self, propagated, geocoded, failed, api_calls):
        self.stdout.write(self.style.SUCCESS(
            f"\nCompletato: "
            f"{propagated} propagate, "
            f"{geocoded} geocodificate, "
            f"{failed} indirizzi falliti, "
            f"{api_calls} chiamate API"
        ))
