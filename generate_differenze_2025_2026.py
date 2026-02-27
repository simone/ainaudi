#!/usr/bin/env python3
"""
Genera i file di differenze tra sezioni 2025 e 2026:
- differenze_2025_2026.csv (con colonne: sezione, via_2025, mun_2025, via_2026, mun_2026, tipo_diff)
- differenze_2025_2026.txt (report leggibile per municipio)
"""
import csv
import re
from collections import defaultdict

CSV_2025 = "roma/sezioni_2025.csv"
CSV_2026 = "roma/sezioni_2026.csv"
OUT_CSV = "roma/differenze_2025_2026.csv"
OUT_TXT = "roma/differenze_2025_2026.txt"


def normalize_address(addr):
    """Normalizza indirizzo per comparazione."""
    # Converti a maiuscole
    addr = addr.upper().strip()
    # Rimuovi spazi multipli
    addr = re.sub(r'\s+', ' ', addr)
    # Normalizza separatori: "VIA XX, 231" -> "VIA XX N. 231", "VIA XX N. 231" -> "VIA XX N. 231"
    addr = re.sub(r',\s*(\d+)', r' N. \1', addr)
    # Rimuovi "N." se non seguito da numero
    addr = re.sub(r'\s+N\.\s*$', '', addr)
    return addr


# Leggi i CSV
sezioni_2025 = {}
sezioni_2026 = {}

with open(CSV_2025, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        num = int(row['numero'])
        via_orig = row['via'].strip()
        sezioni_2025[num] = {
            'via': via_orig,
            'via_norm': normalize_address(via_orig),
            'municipio': int(row['municipio']),
        }

with open(CSV_2026, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        num = int(row['numero'])
        via_orig = row['via'].strip()
        sezioni_2026[num] = {
            'via': via_orig,
            'via_norm': normalize_address(via_orig),
            'municipio': int(row['municipio']),
        }

# Trova differenze (usando indirizzi normalizzati)
differenze = []
nuove = []
rimosse = []

for num in sorted(sezioni_2025.keys()):
    if num not in sezioni_2026:
        rimosse.append(num)
        continue

    s2025 = sezioni_2025[num]
    s2026 = sezioni_2026[num]

    # Compara usando gli indirizzi normalizzati
    via_changed = s2025['via_norm'] != s2026['via_norm']
    mun_changed = s2025['municipio'] != s2026['municipio']

    if via_changed or mun_changed:
        if via_changed and mun_changed:
            tipo = 'VIA+MUN'
        elif via_changed:
            tipo = 'VIA'
        else:
            tipo = 'MUN'

        differenze.append({
            'sezione': num,
            'via_2025': s2025['via'],  # Usa l'indirizzo originale nel CSV
            'mun_2025': s2025['municipio'],
            'via_2026': s2026['via'],  # Usa l'indirizzo originale nel CSV
            'mun_2026': s2026['municipio'],
            'tipo': tipo,
        })

for num in sorted(sezioni_2026.keys()):
    if num not in sezioni_2025:
        nuove.append(num)

# Scrivi CSV
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['sezione', 'via_2025', 'mun_2025', 'via_2026', 'mun_2026', 'tipo_diff'])
    for d in differenze:
        writer.writerow([
            d['sezione'],
            d['via_2025'],
            d['mun_2025'],
            d['via_2026'],
            d['mun_2026'],
            d['tipo'],
        ])

print(f"✓ CSV scritto: {OUT_CSV} ({len(differenze)} differenze)")

# Organizza differenze per municipio
differenze_per_mun = defaultdict(list)
for d in differenze:
    # Usa il municipio 2026 come riferimento
    mun = d['mun_2026']
    differenze_per_mun[mun].append(d)

# Scrivi TXT
with open(OUT_TXT, 'w', encoding='utf-8') as f:
    if nuove:
        f.write(f"SEZIONI NUOVE nel 2026 ({len(nuove)}):\n")
        for num in nuove:
            s = sezioni_2026[num]
            f.write(f"  Sezione {num}: {s['via']} (Municipio {s['municipio']})\n")
        f.write("\n")

    if rimosse:
        f.write(f"SEZIONI RIMOSSE nel 2026 ({len(rimosse)}):\n")
        for num in rimosse:
            s = sezioni_2025[num]
            f.write(f"  Sezione {num}: {s['via']} (Municipio {s['municipio']})\n")
        f.write("\n")

    if differenze:
        f.write(f"SEZIONI CON DIFFERENZE ({len(differenze)}):\n\n")

        for mun in sorted(differenze_per_mun.keys()):
            diffs = differenze_per_mun[mun]
            f.write(f"Nel municipio {mun}:\n")

            # Raggruppa per tipo di differenza
            by_type = defaultdict(list)
            for d in diffs:
                by_type[d['tipo']].append(d)

            # Stampa VIA
            if 'VIA' in by_type:
                via_changes = by_type['VIA']
                if len(via_changes) == 1:
                    d = via_changes[0]
                    f.write(f"  - la sezione {d['sezione']} ha cambiato via da {d['via_2025']} a {d['via_2026']}\n")
                else:
                    # Raggruppa per coppia via_2025 -> via_2026
                    by_transition = defaultdict(list)
                    for d in via_changes:
                        key = (d['via_2025'], d['via_2026'])
                        by_transition[key].append(d['sezione'])

                    for (old_via, new_via), nums in sorted(by_transition.items()):
                        nums_str = ', '.join(str(n) for n in nums)
                        f.write(f"  - le sezioni {nums_str} hanno cambiato via da {old_via} a {new_via}\n")

            # Stampa MUN
            if 'MUN' in by_type:
                mun_changes = by_type['MUN']
                if len(mun_changes) == 1:
                    d = mun_changes[0]
                    f.write(f"  - la sezione {d['sezione']} ha cambiato municipio da {d['mun_2025']} a {d['mun_2026']}\n")
                else:
                    # Raggruppa per municipio di provenienza
                    by_source = defaultdict(list)
                    for d in mun_changes:
                        by_source[d['mun_2025']].append(d['sezione'])

                    for old_mun in sorted(by_source.keys()):
                        nums = by_source[old_mun]
                        nums_str = ', '.join(str(n) for n in nums)
                        f.write(f"  - le sezioni {nums_str} hanno cambiato municipio da {old_mun} a {mun}\n")

            # Stampa VIA+MUN
            if 'VIA+MUN' in by_type:
                via_mun_changes = by_type['VIA+MUN']
                for d in via_mun_changes:
                    f.write(f"  - la sezione {d['sezione']} ha cambiato via e municipio, stava in {d['via_2025']} nel municipio {d['mun_2025']} e ora si trova in {d['via_2026']} nel municipio {d['mun_2026']}\n")

            f.write("\n")

print(f"✓ TXT scritto: {OUT_TXT} ({len(differenze)} differenze, {len(nuove)} nuove, {len(rimosse)} rimosse)")

# Resoconto
print(f"\n{'='*80}")
print(f"RIASSUNTO DIFFERENZE 2025 → 2026")
print(f"{'='*80}")
print(f"Sezioni comuni:              {len(sezioni_2025) - len(rimosse)}")
print(f"Sezioni nuove:               {len(nuove)}")
print(f"Sezioni rimosse:             {len(rimosse)}")
print(f"Sezioni con differenze:      {len(differenze)}")
print(f"  - Solo via:                {len([d for d in differenze if d['tipo'] == 'VIA'])}")
print(f"  - Solo municipio:          {len([d for d in differenze if d['tipo'] == 'MUN'])}")
print(f"  - Via + municipio:         {len([d for d in differenze if d['tipo'] == 'VIA+MUN'])}")
print()
