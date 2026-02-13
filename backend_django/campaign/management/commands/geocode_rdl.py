"""
Geocode RDL registrations using Google Geocoding API.

Uses in-memory address cache to avoid duplicate API calls for RDLs
with the same normalized address.

Usage:
    python manage.py geocode_rdl --limit 500 --dry-run
    python manage.py geocode_rdl --comune-id 123 --limit 500
    python manage.py geocode_rdl --force  # ricalcola tutti
"""
import re
import time
import unicodedata

from django.core.management.base import BaseCommand
from django.utils import timezone

from campaign.models import RdlRegistration
from territory.geocoding import build_rdl_address, geocode_address


def _normalize_address_key(address):
    """
    Normalize an address for cache deduplication.
    Uppercase, strip accents, collapse whitespace.
    """
    if not address:
        return ""
    s = str(address).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class Command(BaseCommand):
    help = "Geocode RDL registrations via Google Geocoding API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--comune-id",
            type=int,
            help="Filtra per ID comune operativo",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Numero massimo di RDL da geocodificare (default: 500)",
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
            help="Ricalcola anche RDL già geocodificati",
        )

    def handle(self, *args, **options):
        comune_id = options.get("comune_id")
        limit = options["limit"]
        sleep_ms = options["sleep_ms"]
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write("Geocoding RDL registrations...")

        qs = RdlRegistration.objects.filter(
            status=RdlRegistration.Status.APPROVED,
        ).select_related("comune")

        if comune_id:
            qs = qs.filter(comune_id=comune_id)

        if not force:
            qs = qs.filter(latitudine__isnull=True)

        total = qs.count()
        rdl_list = list(qs[:limit])
        batch_size = len(rdl_list)

        self.stdout.write(
            f"Trovati {total} RDL senza coordinate (limit: {limit})"
        )

        if not rdl_list:
            self.stdout.write("Nessun RDL da geocodificare.")
            return

        # In-memory cache: normalized_address → (lat, lon, place_id, quality)
        cache = {}
        ok_count = 0
        fail_count = 0
        cache_hit_count = 0
        api_call_count = 0
        sleep_sec = sleep_ms / 1000.0

        for i, rdl in enumerate(rdl_list, 1):
            address = build_rdl_address(rdl)
            cache_key = _normalize_address_key(address)

            # Check cache
            if cache_key in cache:
                result = cache[cache_key]
                cache_hit_count += 1
            elif dry_run:
                result = None  # Don't call API in dry-run
            else:
                result = geocode_address(address)
                api_call_count += 1
                if result is not None:
                    cache[cache_key] = result

                if sleep_sec > 0 and i < batch_size:
                    time.sleep(sleep_sec)

            label = f"{rdl.cognome} {rdl.nome}"
            pad = len(str(batch_size))

            if dry_run:
                self.stdout.write(
                    f"[{i:>{pad}}/{batch_size}] "
                    f"{label} - {address} [DRY RUN]"
                )
                ok_count += 1
                continue

            if result is None:
                fail_count += 1
                self.stderr.write(
                    f"[{i:>{pad}}/{batch_size}] "
                    f"{label} - {address} → FALLITA"
                )
            else:
                lat, lon, place_id, location_type = result
                rdl.latitudine = lat
                rdl.longitudine = lon
                rdl.geocoded_at = timezone.now()
                rdl.geocode_source = "google"
                rdl.geocode_quality = location_type
                rdl.geocode_place_id = place_id
                rdl.save(update_fields=[
                    "latitudine", "longitudine",
                    "geocoded_at", "geocode_source",
                    "geocode_quality", "geocode_place_id",
                ])
                ok_count += 1
                hit = " [cache]" if cache_key in cache and api_call_count == 0 else ""
                self.stdout.write(
                    f"[{i:>{pad}}/{batch_size}] "
                    f"{label} - {address} → "
                    f"{lat}, {lon} ({location_type}){hit}"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN completato: {ok_count} RDL trovati"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nCompletato: {ok_count} ok, {fail_count} falliti, "
                f"{api_call_count} chiamate API, {cache_hit_count} cache hit"
            ))
