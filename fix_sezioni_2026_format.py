#!/usr/bin/env python3
"""
Converte il formato indirizzi da 'VIA XX N. 123' a 'VIA XX, 123'
per compatibilità con il formato del DB.
"""
import csv
import re

INPUT_CSV = "backend_django/fixtures/sezioni_2026.csv"
OUTPUT_CSV = "backend_django/fixtures/sezioni_2026.csv"

def fix_address(addr):
    """Converte 'VIA XX N. 123' -> 'VIA XX, 123'"""
    if not addr:
        return addr
    # Converti "VIA XX N. 123" -> "VIA XX, 123"
    addr = re.sub(r'\s+N\.\s+(\d+)', r', \1', addr)
    return addr

# Leggi e converti
rows = []
with open(INPUT_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['via'] = fix_address(row['via'])
        rows.append(row)

# Scrivi
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['numero', 'via', 'municipio'])
    writer.writeheader()
    writer.writerows(rows)

print(f"✓ Convertiti {len(rows)} indirizzi")
print(f"✓ Formato: 'VIA XX N. 123' → 'VIA XX, 123'")
print(f"✓ File scritto: {OUTPUT_CSV}")
