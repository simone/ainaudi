"""
Match electoral sections to nearest RDLs by geographic proximity.

Works per-comune: for each comune in the provincia, matches its geocoded
sections to RDLs whose comune operativo is that same comune.

Usage:
    python manage.py match_sezioni_rdl --provincia RM --top 5
    python manage.py match_sezioni_rdl --provincia RM --top 3 --output rdl_match.csv
    python manage.py match_sezioni_rdl --comune-id 123 --top 5
"""
import csv
import sys
from collections import defaultdict

from django.core.management.base import BaseCommand

from campaign.models import RdlRegistration
from territory.geocoding import haversine_km
from territory.models import SezioneElettorale


class Command(BaseCommand):
    help = (
        "Match electoral sections to nearest geocoded RDLs per-comune. "
        "RDLs are matched only to sections of their comune operativo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--provincia",
            default="RM",
            help="Sigla provincia (default: RM)",
        )
        parser.add_argument(
            "--comune-id",
            dest="comune_id",
            help="Codice ISTAT del comune (es. 058091)",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=5,
            help="Numero di RDL più vicini per sezione (default: 5)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="File CSV di output (default: stdout)",
        )
        parser.add_argument(
            "--max-km",
            type=float,
            default=0,
            help="Distanza massima in km (default: 0 = nessun limite)",
        )

    def handle(self, *args, **options):
        provincia = options["provincia"]
        comune_id = options.get("comune_id")
        top_n = options["top"]
        output_path = options["output"]
        max_km = options["max_km"]

        log = self.stderr

        # ── Load sections ──────────────────────────────────────────────
        sez_filter = {
            "latitudine__isnull": False,
            "longitudine__isnull": False,
        }
        if comune_id:
            sez_filter["comune__codice_istat"] = comune_id
        else:
            sez_filter["comune__provincia__sigla"] = provincia

        sezioni = list(
            SezioneElettorale.objects.filter(**sez_filter)
            .select_related("comune", "comune__provincia")
        )

        log.write(f"Trovate {len(sezioni)} sezioni geocodificate\n")
        if not sezioni:
            log.write(self.style.ERROR(
                "Nessuna sezione geocodificata. Esegui prima geocode_sezioni.\n"
            ))
            return

        # ── Load RDLs ─────────────────────────────────────────────────
        rdl_filter = {
            "status": RdlRegistration.Status.APPROVED,
            "latitudine__isnull": False,
            "longitudine__isnull": False,
        }
        if comune_id:
            rdl_filter["comune__codice_istat"] = comune_id
        else:
            rdl_filter["comune__provincia__sigla"] = provincia

        rdl_list = list(
            RdlRegistration.objects.filter(**rdl_filter)
            .select_related("comune")
        )

        log.write(f"Trovati {len(rdl_list)} RDL geocodificati\n")
        if not rdl_list:
            log.write(self.style.ERROR(
                "Nessun RDL geocodificato. Esegui prima geocode_rdl.\n"
            ))
            return

        # ── Group by comune ────────────────────────────────────────────
        sez_by_comune = defaultdict(list)
        for s in sezioni:
            sez_by_comune[s.comune_id].append(s)

        rdl_by_comune = defaultdict(list)
        for r in rdl_list:
            rdl_by_comune[r.comune_id].append(r)

        # Comuni with both sections and RDLs
        comuni_ids = set(sez_by_comune.keys()) & set(rdl_by_comune.keys())

        log.write(
            f"Comuni con sezioni + RDL geocodificati: {len(comuni_ids)}\n"
        )
        if not comuni_ids:
            log.write(self.style.WARNING(
                "Nessun comune ha sia sezioni che RDL geocodificati.\n"
            ))
            return

        max_label = f"max {max_km} km" if max_km > 0 else "senza limite"
        log.write(f"Matching top {top_n} per sezione ({max_label})...\n")

        # ── Output CSV ─────────────────────────────────────────────────
        if output_path:
            outfile = open(output_path, "w", newline="", encoding="utf-8")
        else:
            outfile = sys.stdout

        try:
            writer = csv.writer(outfile)
            writer.writerow([
                "sezione_id",
                "sezione_numero",
                "sezione_comune",
                "sezione_indirizzo",
                "rdl_id",
                "rdl_cognome",
                "rdl_nome",
                "rdl_email",
                "distanza_km",
            ])

            total_rows = 0
            total_sez_matched = 0

            for cid in sorted(comuni_ids):
                c_sezioni = sez_by_comune[cid]
                c_rdl = rdl_by_comune[cid]
                comune_nome = c_sezioni[0].comune.nome

                c_rdl_coords = [
                    (float(r.latitudine), float(r.longitudine))
                    for r in c_rdl
                ]

                for sez in c_sezioni:
                    sez_lat = float(sez.latitudine)
                    sez_lon = float(sez.longitudine)

                    distances = []
                    for j, rdl in enumerate(c_rdl):
                        dist = haversine_km(
                            sez_lat, sez_lon,
                            c_rdl_coords[j][0], c_rdl_coords[j][1],
                        )
                        if max_km <= 0 or dist <= max_km:
                            distances.append((dist, rdl))

                    distances.sort(key=lambda x: x[0])
                    top_matches = distances[:top_n]

                    if top_matches:
                        total_sez_matched += 1

                    for dist, rdl in top_matches:
                        writer.writerow([
                            sez.id,
                            sez.numero,
                            comune_nome,
                            sez.indirizzo or "",
                            rdl.id,
                            rdl.cognome,
                            rdl.nome,
                            rdl.email,
                            f"{dist:.2f}",
                        ])
                        total_rows += 1

                log.write(
                    f"  {comune_nome}: {len(c_sezioni)} sezioni x "
                    f"{len(c_rdl)} RDL\n"
                )

        finally:
            if output_path and outfile is not sys.stdout:
                outfile.close()

        if output_path:
            log.write(self.style.SUCCESS(
                f"\nScritte {total_rows} righe in {output_path} "
                f"({total_sez_matched} sezioni con match)\n"
            ))
        else:
            log.write(self.style.SUCCESS(
                f"\nTotale: {total_rows} righe, "
                f"{total_sez_matched} sezioni con match\n"
            ))
