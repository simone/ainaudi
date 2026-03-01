#!/usr/bin/env python3
"""
Estrae le sezioni elettorali dal PDF ufficiale di Roma Capitale
e genera il CSV nel formato: SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO

Gestisce correttamente le SEZIONI OSPEDALIERE (senza intestazione Municipio)
mappando il quartiere/rione/zona al municipio corretto.
"""
import re
import csv
import pdfplumber

PDF_PATH = "Seggi elettorali 2026.pdf"
CSV_OUTPUT = "backend_django/fixtures/ROMA - Sezioni.csv"

# Sezioni ospedaliere in zone ambigue (quartiere a cavallo di più municipi).
# Mappatura manuale basata sull'indirizzo effettivo dell'ospedale.
HOSPITAL_MUNICIPIO = {
    2572: 4,   # Osp. Sandro Pertini, Via dei Monti Tiburtini 385 (Pietralata→Mun.4)
    2573: 5,   # Via di Acqua Bullicante 4 (Prenestino→Mun.5)
    2578: 6,   # Policlinico Tor Vergata, Viale Oxford 81 (Torre Gaia→Mun.6)
    2580: 12,  # Osp. San Camillo, Circ. Gianicolense 87 (Gianicolense→Mun.12)
    2581: 12,  # Osp. San Camillo
    2582: 12,  # Osp. San Camillo
    2586: 13,  # San Carlo di Nancy, Via Aurelia 275 (Aurelio→Mun.13)
    2587: 14,  # Policlinico Gemelli, Largo A. Gemelli 8 (Trionfale→Mun.14)
    2588: 14,  # Policlinico Gemelli
    2589: 14,  # Policlinico Gemelli
    2590: 14,  # Gemelli, Via G. Moscati 31 (Trionfale→Mun.14)
    2592: 12,  # IDI, Via della Pisana 235 (Gianicolense→Mun.12)
    2593: 11,  # Via Portuense 798 (Gianicolense→Mun.11)
    2599: 14,  # Via G. Martinotti 20 (Trionfale→Mun.14)
}

# Regex per estrarre sezione con zona/quartiere/rione completo
RE_SECTION = re.compile(
    r'sezione\s+n\.:\s*(\d+)\s*-+\s*'       # numero sezione
    r'(.+?)\s*-\s*Cap\s+(\d{5})\s*'          # indirizzo e CAP
    r'(.+)',                                   # zona/quartiere/rione (resto della riga)
)
RE_MUNICIPIO = re.compile(r'Municipio Roma\s+(\d+)', re.IGNORECASE)
RE_OSPEDALIERE = re.compile(r'SEZIONI OSPEDALIERE', re.IGNORECASE)


def extract_sections(pdf_path):
    """
    Estrae tutte le sezioni dal PDF.
    Ritorna (sections_dict, zona_to_municipio_map).
    """
    sections = {}
    zona_municipio = {}  # zona_name -> municipio (costruita dalle sezioni regolari)
    current_municipio = None
    is_ospedaliere = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                # Rileva intestazione "SEZIONI OSPEDALIERE"
                if RE_OSPEDALIERE.search(line):
                    is_ospedaliere = True
                    current_municipio = None
                    continue

                # Rileva cambio municipio
                m = RE_MUNICIPIO.search(line)
                if m:
                    current_municipio = int(m.group(1))
                    is_ospedaliere = False
                    continue

                # Rileva sezione
                m = RE_SECTION.match(line.strip())
                if m:
                    num = int(m.group(1))
                    indirizzo = re.sub(r'\s+', ' ', m.group(2).strip()).upper()
                    zona_raw = m.group(4).strip()
                    # Normalizza zona: prendi solo la prima (prima di " e parte")
                    zona = re.split(r'\s+e\s+parte\s+', zona_raw, flags=re.IGNORECASE)[0].strip()

                    if not is_ospedaliere and current_municipio:
                        # Sezione regolare: salva e costruisci mappa zona→municipio
                        sections[num] = {
                            'municipio': current_municipio,
                            'indirizzo': indirizzo,
                            'zona': zona,
                        }
                        if zona and zona not in zona_municipio:
                            zona_municipio[zona] = current_municipio
                    else:
                        # Sezione ospedaliera: salva con municipio=None, risolveremo dopo
                        sections[num] = {
                            'municipio': None,
                            'indirizzo': indirizzo,
                            'zona': zona,
                        }

    return sections, zona_municipio


def resolve_hospital_sections(sections, zona_municipio):
    """Risolve il municipio per le sezioni ospedaliere.

    Priorità: 1) mappa hardcoded HOSPITAL_MUNICIPIO per zone ambigue
              2) mappa zona→municipio per zone non ambigue
    """
    unresolved = []
    for num, s in sorted(sections.items()):
        if s['municipio'] is not None:
            continue

        # 1) Mappa hardcoded per ospedali in zone ambigue
        if num in HOSPITAL_MUNICIPIO:
            s['municipio'] = HOSPITAL_MUNICIPIO[num]
            continue

        # 2) Mappa zona→municipio (solo per zone non ambigue)
        zona = s['zona']
        if zona in zona_municipio:
            s['municipio'] = zona_municipio[zona]
        else:
            unresolved.append((num, zona, s['indirizzo']))

    return unresolved


def write_csv(sections, csv_path):
    """Scrive le sezioni in formato CSV ordinato per numero sezione."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['SEZIONE', 'COMUNE', 'MUNICIPIO', 'INDIRIZZO', ''])
        for num in sorted(sections.keys()):
            s = sections[num]
            writer.writerow([num, 'ROMA', s['municipio'], s['indirizzo'], ''])

    return len(sections)


def compare_with_existing(sections, csv_path):
    """Confronta le sezioni estratte con il CSV esistente."""
    old = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = int(row['SEZIONE'])
                old[num] = {
                    'municipio': int(row['MUNICIPIO']),
                    'indirizzo': row['INDIRIZZO'].strip(),
                }
    except FileNotFoundError:
        print("CSV esistente non trovato, skip confronto.")
        return

    new_nums = set(sections.keys())
    old_nums = set(old.keys())
    common = sorted(new_nums & old_nums)

    print(f"\n{'='*60}")
    print(f"CONFRONTO PDF vs CSV ESISTENTE")
    print(f"{'='*60}")
    print(f"Sezioni nel PDF:           {len(new_nums)}")
    print(f"Sezioni nel CSV esistente: {len(old_nums)}")
    print(f"In comune:                 {len(common)}")

    only_pdf = sorted(new_nums - old_nums)
    only_csv = sorted(old_nums - new_nums)

    if only_pdf:
        print(f"\nSolo nel PDF ({len(only_pdf)}):")
        for n in only_pdf:
            s = sections[n]
            print(f"  Sez. {n}: Mun.{s['municipio']} - {s['indirizzo']}")

    if only_csv:
        print(f"\nSolo nel CSV ({len(only_csv)}):")
        for n in only_csv:
            print(f"  Sez. {n}: Mun.{old[n]['municipio']} - {old[n]['indirizzo']}")

    mun_diff = []
    addr_diff = []
    for n in common:
        new_mun = sections[n]['municipio']
        old_mun = old[n]['municipio']
        new_addr = sections[n]['indirizzo']
        old_addr = old[n]['indirizzo'].upper().strip()
        if new_mun != old_mun:
            mun_diff.append((n, old_mun, new_mun))
        if new_addr != old_addr:
            addr_diff.append((n, old_addr, new_addr))

    if mun_diff:
        print(f"\nMunicipio diverso ({len(mun_diff)}):")
        for n, o, new in mun_diff:
            print(f"  Sez. {n}: CSV=Mun.{o} → PDF=Mun.{new}")

    if addr_diff:
        print(f"\nIndirizzo diverso ({len(addr_diff)}):")
        for n, o, new in addr_diff:
            print(f"  Sez. {n}: CSV={o} → PDF={new}")

    if not only_pdf and not only_csv and not mun_diff and not addr_diff:
        print("\nNessuna differenza!")


if __name__ == '__main__':
    print("Estrazione sezioni dal PDF...")
    sections, zona_municipio = extract_sections(PDF_PATH)

    # Conteggio sezioni ospedaliere (municipio=None)
    ospedaliere = [n for n, s in sections.items() if s['municipio'] is None]
    print(f"Sezioni estratte: {len(sections)} ({len(ospedaliere)} ospedaliere da risolvere)")

    # Risolvi sezioni ospedaliere
    unresolved = resolve_hospital_sections(sections, zona_municipio)
    if unresolved:
        print(f"\nATTENZIONE: {len(unresolved)} sezioni ospedaliere non risolte:")
        for num, zona, addr in unresolved:
            print(f"  Sez. {num}: zona='{zona}' - {addr}")
    else:
        print(f"Tutte le {len(ospedaliere)} sezioni ospedaliere risolte correttamente")

    # Riepilogo per municipio
    by_mun = {}
    for s in sections.values():
        by_mun.setdefault(s['municipio'], []).append(1)
    print("\nSezioni per Municipio:")
    for mun in sorted(by_mun.keys()):
        print(f"  Municipio {mun:2d}: {len(by_mun[mun]):4d} sezioni")

    # Confronta con CSV esistente
    compare_with_existing(sections, CSV_OUTPUT)

    # Scrivi il nuovo CSV
    count = write_csv(sections, CSV_OUTPUT)
    print(f"\nCSV scritto: {CSV_OUTPUT} ({count} sezioni)")
