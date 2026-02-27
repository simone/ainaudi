#!/usr/bin/env python3
"""
Estrae le sezioni elettorali dal PDF Referendum Confermativo 2026
e genera il CSV nel formato: numero,via,municipio
"""
import re
import csv
import pdfplumber

PDF_PATH = "roma/SezioniReferendumConfermativo2026.pdf"
CSV_OUTPUT = "roma/sezioni_2026.csv"

def extract_sections(pdf_path):
    """
    Estrae tutte le sezioni dal PDF.
    Formato tabellare: Sezione | Municipio | Indirizzo
    """
    sections = {}

    # Pattern per estrarre: numero municipio indirizzo da una riga
    # Es: "1 3 VIA DI SETTEBAGNI N. 231"
    RE_LINE = re.compile(r'^(\d+)\s+(\d+)\s+(.+)$')

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()

                # Skip header lines
                if 'Sezione' in line or 'Municipio' in line or 'Indirizzo' in line:
                    continue
                if 'Sezioni Elettorali' in line or 'Direzione' in line or 'Ufficio' in line:
                    continue
                if not line:
                    continue

                # Try to match the line
                m = RE_LINE.match(line)
                if m:
                    try:
                        num = int(m.group(1))
                        municipio = int(m.group(2))
                        indirizzo = m.group(3).strip()

                        sections[num] = {
                            'numero': num,
                            'via': indirizzo,
                            'municipio': municipio,
                        }
                    except (ValueError, IndexError):
                        # Skip lines that don't match the pattern
                        pass

    return sections


def write_csv(sections, csv_path):
    """Scrive le sezioni in formato CSV ordinato per numero sezione."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['numero', 'via', 'municipio'])
        for num in sorted(sections.keys()):
            s = sections[num]
            writer.writerow([s['numero'], s['via'], s['municipio']])

    return len(sections)


def normalize_address(addr):
    """Normalizza indirizzo per comparazione: rimuove virgole, standardizza separatori."""
    # Converti a maiuscole
    addr = addr.upper().strip()
    # Rimuovi spazi multipli
    addr = re.sub(r'\s+', ' ', addr)
    # Normalizza separatori: "VIA XX, 231" -> "VIA XX N. 231", "VIA XX N. 231" -> "VIA XX N. 231"
    # Sostituisci virgola numero con "N."
    addr = re.sub(r',\s*(\d+)', r' N. \1', addr)
    # Rimuovi "N." se non seguito da numero
    addr = re.sub(r'\s+N\.\s*$', '', addr)
    return addr


def compare_with_existing(sections, existing_csv):
    """Confronta le sezioni estratte con il CSV 2025."""
    try:
        with open(existing_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            old_orig = {}  # Valori originali
            old_norm = {}  # Valori normalizzati
            for row in reader:
                num = int(row['numero'])
                via_orig = row['via'].strip()
                old_orig[num] = {
                    'via': via_orig,
                    'municipio': int(row['municipio']),
                }
                old_norm[num] = {
                    'via': normalize_address(via_orig),
                    'municipio': int(row['municipio']),
                }
    except FileNotFoundError:
        print(f"File {existing_csv} non trovato, skip confronto.")
        return

    # Normalizza anche i nuovi indirizzi
    sections_norm = {}
    for num, s in sections.items():
        sections_norm[num] = {
            'via': normalize_address(s['via']),
            'municipio': s['municipio'],
        }

    new_nums = set(sections.keys())
    old_nums = set(old_orig.keys())
    common = sorted(new_nums & old_nums)

    print(f"\n{'='*80}")
    print(f"CONFRONTO PDF 2026 vs CSV 2025")
    print(f"{'='*80}")
    print(f"Sezioni nel PDF 2026:      {len(new_nums)}")
    print(f"Sezioni nel CSV 2025:      {len(old_nums)}")
    print(f"In comune:                 {len(common)}")

    only_pdf = sorted(new_nums - old_nums)
    only_csv = sorted(old_nums - new_nums)

    if only_pdf:
        print(f"\nNUOVE SEZIONI nel PDF 2026 ({len(only_pdf)}):")
        for n in only_pdf[:20]:
            s = sections[n]
            print(f"  Sez. {n:4d}: Mun.{s['municipio']:2d} - {s['via']}")
        if len(only_pdf) > 20:
            print(f"  ... e {len(only_pdf) - 20} altre sezioni")

    if only_csv:
        print(f"\nSEZIONI RIMOSSE dal CSV 2026 ({len(only_csv)}):")
        for n in only_csv[:20]:
            print(f"  Sez. {n:4d}: Mun.{old_orig[n]['municipio']:2d} - {old_orig[n]['via']}")
        if len(only_csv) > 20:
            print(f"  ... e {len(only_csv) - 20} altre sezioni")

    mun_diff = []
    addr_diff = []
    for n in common:
        new_mun = sections[n]['municipio']
        old_mun = old_orig[n]['municipio']
        new_addr_norm = sections_norm[n]['via']
        old_addr_norm = old_norm[n]['via']
        if new_mun != old_mun:
            mun_diff.append((n, old_mun, new_mun))
        if new_addr_norm != old_addr_norm:
            addr_diff.append((n, old_orig[n]['via'], sections[n]['via']))

    if mun_diff:
        print(f"\nMUNICIPIO DIVERSO ({len(mun_diff)}):")
        for n, o, new in mun_diff[:20]:
            print(f"  Sez. {n:4d}: 2025=Mun.{o:2d} → 2026=Mun.{new:2d}")
        if len(mun_diff) > 20:
            print(f"  ... e {len(mun_diff) - 20} altre sezioni con municipio diverso")

    if addr_diff:
        print(f"\nINDIRIZZO DIVERSO ({len(addr_diff)}):")
        for n, o, new in addr_diff[:20]:
            print(f"  Sez. {n:4d}:")
            print(f"    2025: {o}")
            print(f"    2026: {new}")
        if len(addr_diff) > 20:
            print(f"  ... e {len(addr_diff) - 20} altri indirizzi diversi")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Sezioni in comune:       {len(common)}")
    print(f"+ Nuove nel 2026:          {len(only_pdf)}")
    print(f"- Rimosse nel 2026:        {len(only_csv)}")
    print(f"✗ Municipio diverso:       {len(mun_diff)}")
    print(f"✗ Indirizzo diverso:       {len(addr_diff)}")
    print()

    if not only_pdf and not only_csv and not mun_diff and not addr_diff:
        print("✓ NESSUNA DIFFERENZA! File identici.")


if __name__ == '__main__':
    print(f"Estrazione sezioni dal PDF 2026: {PDF_PATH}")
    sections = extract_sections(PDF_PATH)

    if not sections:
        print("ERRORE: Nessuna sezione trovata nel PDF!")
        exit(1)

    print(f"✓ Sezioni estratte: {len(sections)}")

    # Riepilogo per municipio
    by_mun = {}
    for s in sections.values():
        by_mun.setdefault(s['municipio'], []).append(1)
    print("\nSezioni per Municipio:")
    for mun in sorted(by_mun.keys()):
        print(f"  Municipio {mun:2d}: {len(by_mun[mun]):4d} sezioni")

    # Scrivi il nuovo CSV
    count = write_csv(sections, CSV_OUTPUT)
    print(f"\n✓ CSV scritto: {CSV_OUTPUT} ({count} sezioni)")

    # Confronta con CSV 2025
    compare_with_existing(sections, "roma/sezioni_2025.csv")
