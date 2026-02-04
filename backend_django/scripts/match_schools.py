#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Match a list of addresses (Rome) to official Italian school buildings (MIM Open Data),
then enrich with school names from the "Anagrafica scuole statali" dataset.

Inputs:
  - all_missing_addrs.txt  (one address per line, e.g. "VIA XYZ, 12/A")

Outputs:
  - matched_schools.csv

Notes:
  - Address matching is normalized and can be extended to fuzzy matching if needed.
  - The script tries to auto-discover the latest downloadable CSV links from dataset pages.
"""

import re
import sys
import unicodedata
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup

ADDR_FILE = Path("all_missing_addrs.txt")
OUT_FILE = Path("matched_schools.csv")

# Official dataset pages (MIM Open Data)
EDIFICI_DATASET_PAGE = "https://dati.istruzione.it/opendata/opendata/catalog/EDIANAGRAFESTA2021"
SCUOLE_DATASET_INDEX = "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/?area=Scuole"

# Prefer these school years (descending priority)
# 202526 = a.s. 2025/26, 202425 = a.s. 2024/25
PREFERRED_SCHOOL_YEARS = ["202526", "202425", "202324"]


def normalize_text(s: str) -> str:
    """Normalize text for robust matching: uppercase, strip accents, collapse spaces, remove punctuation."""
    s = s.strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Keep letters/numbers/spaces only
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_address(line: str):
    """
    Split an address like 'VIA ANDREA DORIA, 18' into:
      - street_raw: 'VIA ANDREA DORIA'
      - civico_raw: '18' (can include letters or /A)
    """
    line = line.strip()
    if not line:
        return None, None, None

    # Common pattern: "STREET, CIVIC"
    if "," in line:
        street, civico = [p.strip() for p in line.split(",", 1)]
    else:
        # Fallback: last token might be civic
        parts = line.split()
        street, civico = " ".join(parts[:-1]), parts[-1]

    street_n = normalize_text(street)
    civico_n = normalize_text(civico)
    full_n = normalize_text(f"{street} {civico}")
    return street_n, civico_n, full_n


def discover_csv_link_from_page(url: str, year_token: str = None) -> str:
    """
    Try to discover a CSV download link by scraping anchor tags.
    If year_token is given, prefer links containing that token.
    """
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    # Make absolute if needed
    abs_links = []
    for href in links:
        if href.startswith("http"):
            abs_links.append(href)
        else:
            abs_links.append(requests.compat.urljoin(url, href))

    # Filter likely downloadable CSVs
    csv_links = [l for l in abs_links if l.lower().endswith(".csv")]
    if year_token:
        preferred = [l for l in csv_links if year_token in l]
        if preferred:
            return preferred[0]
    if csv_links:
        return csv_links[0]

    # Sometimes the distribution pages need a second hop: look for "Distribuzione" pages and follow
    dist_pages = [l for l in abs_links if "Distribuzione" in l or "ANNOSCOLASTICO" in l.upper() or "catalog/" in l]
    for dp in dist_pages[:20]:
        try:
            r2 = requests.get(dp, timeout=60)
            if r2.status_code != 200:
                continue
            soup2 = BeautifulSoup(r2.text, "html.parser")
            links2 = [a.get("href") for a in soup2.find_all("a") if a.get("href")]
            abs2 = []
            for href2 in links2:
                if href2.startswith("http"):
                    abs2.append(href2)
                else:
                    abs2.append(requests.compat.urljoin(dp, href2))
            csv2 = [l for l in abs2 if l.lower().endswith(".csv")]
            if year_token:
                preferred2 = [l for l in csv2 if year_token in l]
                if preferred2:
                    return preferred2[0]
            if csv2:
                return csv2[0]
        except Exception:
            continue

    raise RuntimeError(f"Could not auto-discover a CSV link from {url}")


def download_file(url: str, dest: Path):
    """Download a file with streaming."""
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main():
    if not ADDR_FILE.exists():
        print(f"ERROR: missing input file {ADDR_FILE.resolve()}", file=sys.stderr)
        sys.exit(1)

    # 1) Download "edifici scolastici attivi" CSV (choose best year)
    edifici_csv_url = None
    for y in PREFERRED_SCHOOL_YEARS:
        try:
            # For this dataset, the distribution pages are exposed from EDIFICI_DATASET_PAGE
            edifici_csv_url = discover_csv_link_from_page(EDIFICI_DATASET_PAGE, year_token=y)
            break
        except Exception:
            continue
    if not edifici_csv_url:
        raise RuntimeError("Could not find a suitable 'edifici' CSV link")

    edifici_path = Path("edifici_scolastici.csv")
    print(f"Downloading edifici CSV: {edifici_csv_url}")
    download_file(edifici_csv_url, edifici_path)

    # 2) Download "anagrafica scuole statali" CSV (latest available)
    # The search result you saw shows direct per-year CSV URLs; we'll discover by scraping a known direct file list page.
    # Practical approach: hit the "Scuole" catalog index and pick a CSV that matches SCUANAGRAFESTAT and preferred year.
    r = requests.get(SCUOLE_DATASET_INDEX, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    abs_links = []
    for href in links:
        if href.startswith("http"):
            abs_links.append(href)
        else:
            abs_links.append(requests.compat.urljoin(SCUOLE_DATASET_INDEX, href))

    scuole_candidates = [l for l in abs_links if "SCUANAGRAFESTAT" in l and l.lower().endswith(".csv")]
    scuole_csv_url = None
    for y in PREFERRED_SCHOOL_YEARS:
        preferred = [l for l in scuole_candidates if y in l]
        if preferred:
            scuole_csv_url = preferred[0]
            break
    if not scuole_csv_url and scuole_candidates:
        scuole_csv_url = scuole_candidates[0]

    if not scuole_csv_url:
        raise RuntimeError("Could not find 'SCUANAGRAFESTAT' CSV link")

    scuole_path = Path("anagrafica_scuole.csv")
    print(f"Downloading scuole CSV: {scuole_csv_url}")
    download_file(scuole_csv_url, scuole_path)

    # 3) Load datasets
    edifici = pd.read_csv(edifici_path, dtype=str, sep=",", encoding="utf-8", engine="python")
    scuole = pd.read_csv(scuole_path, dtype=str, sep=",", encoding="utf-8", engine="python")

    # 4) Normalize and pre-filter to Roma (if present)
    # The dataset uses DescrizioneComune; we'll keep both Roma and variants if any.
    if "DescrizioneComune" in edifici.columns:
        edifici["DescrizioneComune_N"] = edifici["DescrizioneComune"].fillna("").map(normalize_text)
        edifici = edifici[edifici["DescrizioneComune_N"].isin(["ROMA"])].copy()

    # Build normalized key: "TIPOLOGIA + DENOMINAZIONE + CIVICO"
    edifici["TipologiaIndirizzo"] = edifici.get("TipologiaIndirizzo", "").fillna("")
    edifici["DenominazioneIndirizzo"] = edifici.get("DenominazioneIndirizzo", "").fillna("")
    edifici["NumeroCivico"] = edifici.get("NumeroCivico", "").fillna("")

    edifici["ADDR_N"] = (
        edifici["TipologiaIndirizzo"].map(normalize_text)
        + " "
        + edifici["DenominazioneIndirizzo"].map(normalize_text)
        + " "
        + edifici["NumeroCivico"].map(normalize_text)
    ).str.strip()

    # Map CodiceScuola -> Denominazione (field names may differ by year)
    # Try common columns
    possible_name_cols = ["DENOMINAZIONESCUOLA", "DENOMINAZIONE", "DESCRIZIONESCUOLA", "DESCRIZIONE"]
    name_col = next((c for c in possible_name_cols if c in scuole.columns), None)
    if not name_col:
        # fallback: take the first textual column that looks like a denomination
        name_col = next((c for c in scuole.columns if "DENOM" in c.upper()), None)

    possible_code_cols = ["CODICESCUOLA", "CodiceScuola"]
    code_col = next((c for c in possible_code_cols if c in scuole.columns), None)
    if not code_col:
        code_col = next((c for c in scuole.columns if "CODICE" in c.upper() and "SCUOLA" in c.upper()), None)

    scuole_map = {}
    if code_col and name_col:
        tmp = scuole[[code_col, name_col]].dropna()
        tmp[code_col] = tmp[code_col].astype(str).str.strip()
        scuole_map = dict(zip(tmp[code_col], tmp[name_col].astype(str)))

    # 5) Read input addresses and match
    rows = []
    with open(ADDR_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("indirizzi"):
                continue

            street_n, civico_n, full_n = split_address(line)
            if not full_n:
                continue

            # exact match on normalized address
            hits = edifici[edifici["ADDR_N"] == full_n]

            if hits.empty:
                # fallback: match on street only + civic token inclusion
                # (helps when civico formatting differs: "87/B" vs "87 B")
                hits = edifici[
                    edifici["ADDR_N"].str.contains(street_n, na=False)
                    & edifici["ADDR_N"].str.contains(civico_n, na=False)
                ]

            if hits.empty:
                rows.append(
                    {
                        "input_address": line,
                        "status": "NOT_FOUND",
                        "codice_scuola": "",
                        "denominazione_scuola": "",
                        "official_address": "",
                        "comune": "ROMA",
                        "provincia": "RM",
                        "cap": "",
                    }
                )
                continue

            # One input address can map to multiple schools/plessi in the same building
            for _, h in hits.iterrows():
                cod = str(h.get("CodiceScuola", "")).strip()
                denom = scuole_map.get(cod, "")
                official_addr = " ".join(
                    [
                        str(h.get("TipologiaIndirizzo", "")).strip(),
                        str(h.get("DenominazioneIndirizzo", "")).strip(),
                        str(h.get("NumeroCivico", "")).strip(),
                    ]
                ).strip()

                rows.append(
                    {
                        "input_address": line,
                        "status": "MATCHED",
                        "codice_scuola": cod,
                        "denominazione_scuola": denom,
                        "official_address": official_addr,
                        "comune": str(h.get("DescrizioneComune", "ROMA")).strip(),
                        "provincia": str(h.get("SiglaProvincia", "RM")).strip(),
                        "cap": str(h.get("CAP", "")).strip(),
                    }
                )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8")
    print(f"Done. Output written to: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
