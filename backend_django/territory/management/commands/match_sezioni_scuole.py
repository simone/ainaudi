#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Match electoral sections addresses to school names using MIM Open Data files.

This command loads all Italian schools (public and private) from MIM CSV files
and matches them to electoral sections in the database based on:
1. Same municipality (by codice catastale)
2. Normalized address matching

Usage:
    python manage.py match_sezioni_scuole

The command will update the `denominazione` field of SezioneElettorale records.
"""
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models, transaction

from territory.models import Comune, SezioneElettorale


def normalize_text(s: str) -> str:
    """
    Normalize text for robust matching:
    - Uppercase
    - Strip accents
    - Remove punctuation
    - Collapse spaces
    """
    if not s or pd.isna(s):
        return ""
    s = str(s).strip().upper()
    # Normalize unicode (NFD decomposes accented chars)
    s = unicodedata.normalize("NFKD", s)
    # Remove combining diacritical marks (accents)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Keep only letters, numbers, and spaces
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_street_and_civic(address: str):
    """
    Extract street name and civic number from an address.

    Examples:
        "VIA ROMA, 123" -> ("VIA ROMA", "123")
        "VIA ROMA 123/A" -> ("VIA ROMA", "123 A")
        "PIAZZA GARIBALDI 5" -> ("PIAZZA GARIBALDI", "5")
    """
    if not address:
        return "", ""

    addr_norm = normalize_text(address)
    if not addr_norm:
        return "", ""

    # Try to split on comma first
    if "," in address:
        parts = [p.strip() for p in address.split(",", 1)]
        street = normalize_text(parts[0])
        civic = normalize_text(parts[1]) if len(parts) > 1 else ""
        return street, civic

    # Otherwise, try to extract last token as civic number
    tokens = addr_norm.split()
    if len(tokens) <= 1:
        return addr_norm, ""

    # Check if last token looks like a civic number
    last = tokens[-1]
    # Civic patterns: "123", "123A", "123 A", "SNC" (senza numero civico)
    if re.match(r"^\d+[A-Z]?$", last) or last == "SNC":
        return " ".join(tokens[:-1]), last

    # Check second-to-last + last (for "123 A" patterns)
    if len(tokens) >= 2:
        second_last = tokens[-2]
        if re.match(r"^\d+$", second_last) and re.match(r"^[A-Z]$", last):
            return " ".join(tokens[:-2]), f"{second_last} {last}"

    # No clear civic number found
    return addr_norm, ""


def address_similarity(addr1: str, addr2: str) -> float:
    """
    Calculate similarity between two addresses (0.0 to 1.0).
    Uses token-based matching.
    """
    tokens1 = set(normalize_text(addr1).split())
    tokens2 = set(normalize_text(addr2).split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


class Command(BaseCommand):
    help = "Match electoral sections to school names using MIM Open Data files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show matches without updating the database",
        )
        parser.add_argument(
            "--comune",
            type=str,
            help="Filter by comune name (partial match)",
        )
        parser.add_argument(
            "--min-similarity",
            type=float,
            default=0.6,
            help="Minimum address similarity score (0.0-1.0, default 0.6)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing denominazione values",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        comune_filter = options.get("comune")
        min_similarity = options["min_similarity"]
        overwrite = options["overwrite"]

        fixtures_dir = Path(settings.BASE_DIR) / "fixtures"

        # MIM CSV files
        csv_files = [
            fixtures_dir / "SCUANAGRAFESTAT20252620250901.csv",  # Scuole statali
            fixtures_dir / "SCUANAGRAFEPAR20252620250901.csv",   # Scuole paritarie
            fixtures_dir / "SCUANAAUTSTAT20252620250901.csv",    # Scuole autonome statali
            fixtures_dir / "SCUANAAUTPAR20252620250901.csv",     # Scuole autonome paritarie
        ]

        # 1. Load all schools into a dictionary by codice catastale comune
        self.stdout.write("Loading schools from MIM CSV files...")
        schools_by_comune = defaultdict(list)
        total_schools = 0

        for csv_file in csv_files:
            if not csv_file.exists():
                self.stderr.write(f"  Warning: {csv_file.name} not found, skipping")
                continue

            self.stdout.write(f"  Loading {csv_file.name}...")
            df = pd.read_csv(csv_file, dtype=str, encoding="utf-8")

            # Find the relevant columns (names vary slightly between files)
            codice_col = "CODICECOMUNESCUOLA"
            denom_col = "DENOMINAZIONESCUOLA"
            addr_col = "INDIRIZZOSCUOLA"

            if codice_col not in df.columns:
                self.stderr.write(f"    Warning: {codice_col} not in {csv_file.name}")
                continue

            for _, row in df.iterrows():
                codice = str(row.get(codice_col, "")).strip()
                denom = str(row.get(denom_col, "")).strip()
                addr = str(row.get(addr_col, "")).strip()

                if not codice or not denom or denom == "nan":
                    continue
                if not addr or addr == "nan" or addr.lower() == "non disponibile":
                    continue

                schools_by_comune[codice].append({
                    "denominazione": denom,
                    "indirizzo": addr,
                    "indirizzo_norm": normalize_text(addr),
                })
                total_schools += 1

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {total_schools} schools across {len(schools_by_comune)} comuni"
        ))

        # 2. Build codice catastale -> Comune mapping
        self.stdout.write("Building comune mapping...")
        comuni_map = {}
        for comune in Comune.objects.all():
            comuni_map[comune.codice_catastale] = comune

        # 3. Load sections to match
        self.stdout.write("Loading electoral sections...")
        sections_qs = SezioneElettorale.objects.select_related("comune")

        if comune_filter:
            sections_qs = sections_qs.filter(comune__nome__icontains=comune_filter)

        if not overwrite:
            # Only process sections without denominazione or with empty denominazione
            sections_qs = sections_qs.filter(
                models.Q(denominazione__isnull=True) | models.Q(denominazione="")
            )

        # Filter to sections that have an address
        sections_qs = sections_qs.exclude(indirizzo__isnull=True).exclude(indirizzo="")

        sections = list(sections_qs)
        self.stdout.write(f"Found {len(sections)} sections to process")

        if not sections:
            self.stdout.write("No sections to process")
            return

        # 4. Match sections to schools
        self.stdout.write("Matching sections to schools...")
        matches = []
        not_found = []
        no_schools_in_comune = []

        for i, section in enumerate(sections):
            if (i + 1) % 1000 == 0:
                self.stdout.write(f"  Processed {i + 1}/{len(sections)} sections...")

            codice_cat = section.comune.codice_catastale
            schools = schools_by_comune.get(codice_cat, [])

            if not schools:
                no_schools_in_comune.append(section)
                continue

            section_addr_norm = normalize_text(section.indirizzo)
            section_street, section_civic = extract_street_and_civic(section.indirizzo)

            best_match = None
            best_score = 0.0

            for school in schools:
                school_street, school_civic = extract_street_and_civic(school["indirizzo"])

                # Strategy 1: Exact normalized address match
                if section_addr_norm == school["indirizzo_norm"]:
                    best_match = school
                    best_score = 1.0
                    break

                # Strategy 2: Street match + civic match
                if section_street and school_street:
                    street_match = section_street == school_street
                    civic_match = (
                        section_civic == school_civic or
                        section_civic in school_civic or
                        school_civic in section_civic
                    )

                    if street_match and civic_match:
                        score = 0.95
                        if score > best_score:
                            best_score = score
                            best_match = school
                        continue

                    if street_match:
                        score = 0.8
                        if score > best_score:
                            best_score = score
                            best_match = school
                        continue

                # Strategy 3: Token similarity
                similarity = address_similarity(section.indirizzo, school["indirizzo"])
                if similarity > best_score:
                    best_score = similarity
                    best_match = school

            if best_match and best_score >= min_similarity:
                matches.append({
                    "section": section,
                    "school": best_match,
                    "score": best_score,
                })
            else:
                not_found.append({
                    "section": section,
                    "best_match": best_match,
                    "best_score": best_score,
                })

        # 5. Report results
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"RESULTS:")
        self.stdout.write(f"  Total sections processed: {len(sections)}")
        self.stdout.write(self.style.SUCCESS(f"  Matched: {len(matches)}"))
        self.stdout.write(self.style.WARNING(f"  Not found: {len(not_found)}"))
        self.stdout.write(f"  No schools in comune: {len(no_schools_in_comune)}")
        self.stdout.write("=" * 60 + "\n")

        # Show sample matches
        if matches:
            self.stdout.write("Sample matches (first 10):")
            for m in matches[:10]:
                self.stdout.write(
                    f"  [{m['section'].comune.nome}] Sez. {m['section'].numero}: "
                    f"\"{m['section'].indirizzo}\" -> \"{m['school']['denominazione']}\" "
                    f"(score: {m['score']:.2f})"
                )
            self.stdout.write("")

        # Show sample not-found
        if not_found:
            self.stdout.write("Sample not found (first 10):")
            for nf in not_found[:10]:
                best = nf.get("best_match")
                if best:
                    self.stdout.write(
                        f"  [{nf['section'].comune.nome}] Sez. {nf['section'].numero}: "
                        f"\"{nf['section'].indirizzo}\" ~ \"{best['denominazione']}\" "
                        f"(score: {nf['best_score']:.2f})"
                    )
                else:
                    self.stdout.write(
                        f"  [{nf['section'].comune.nome}] Sez. {nf['section'].numero}: "
                        f"\"{nf['section'].indirizzo}\" - no candidate"
                    )
            self.stdout.write("")

        # 6. Update database
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes made"))
            return

        if not matches:
            self.stdout.write("No matches to save")
            return

        self.stdout.write(f"Updating {len(matches)} sections...")

        with transaction.atomic():
            updated = 0
            for m in matches:
                section = m["section"]
                section.denominazione = m["school"]["denominazione"]
                section.save(update_fields=["denominazione"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} sections"))
