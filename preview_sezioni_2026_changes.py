#!/usr/bin/env python3
"""
Preview of changes for ROMA sezioni_2026 update.
Shows what would be updated in Roma without requiring database connection.
This only updates sections in Roma (Comune: ROMA), not other cities.
"""

import csv
import re


def normalize_address(addr):
    """Normalize for comparison."""
    if not addr:
        return ""
    addr = addr.upper().strip()
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r',\s*(\d+)', r' N. \1', addr)
    return addr


# Read 2025 CSV (still in roma directory)
sezioni_2025 = {}
with open('roma/sezioni_2025.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        num = int(row['numero'])
        sezioni_2025[num] = {
            'via': row['via'].strip(),
            'municipio': int(row['municipio']),
        }

# Read 2026 CSV
sezioni_2026 = {}
with open('backend_django/fixtures/sezioni_2026.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        num = int(row['numero'])
        sezioni_2026[num] = {
            'via': row['via'].strip(),
            'municipio': int(row['municipio']),
        }

# Find sections to delete
to_delete = sorted(set(sezioni_2025.keys()) - set(sezioni_2026.keys()))

# Find sections to update
to_update = []
for num in sorted(set(sezioni_2025.keys()) & set(sezioni_2026.keys())):
    s2025 = sezioni_2025[num]
    s2026 = sezioni_2026[num]

    # Normalize for comparison (ignore format differences like comma vs "N.")
    via_2025_norm = normalize_address(s2025['via'])
    via_2026_norm = normalize_address(s2026['via'])

    # Check for real changes (compare normalized addresses)
    via_changed = via_2025_norm != via_2026_norm
    mun_changed = s2025['municipio'] != s2026['municipio']

    if via_changed or mun_changed:
        to_update.append({
            'numero': num,
            'via_2025': s2025['via'],
            'via_2026': s2026['via'],
            'mun_2025': s2025['municipio'],
            'mun_2026': s2026['municipio'],
            'via_changed': via_changed,
            'mun_changed': mun_changed,
        })

# Print summary
print("=" * 80)
print("PREVIEW: AGGIORNAMENTO SEZIONI 2026")
print("=" * 80)
print()

print(f"Sezioni da aggiornare: {len(to_update)}")
print(f"Sezioni da eliminare:  {len(to_delete)}")
print()

if to_delete:
    print("-" * 80)
    print(f"SEZIONI DA ELIMINARE ({len(to_delete)}):")
    print("-" * 80)
    for num in to_delete:
        s = sezioni_2025[num]
        print(f"  Sezione {num}: {s['via']} (Municipio {s['municipio']})")
    print()

if to_update:
    print("-" * 80)
    print(f"SEZIONI DA AGGIORNARE ({len(to_update)}):")
    print("-" * 80)

    # Group by type
    only_via = [u for u in to_update if u['via_changed'] and not u['mun_changed']]
    only_mun = [u for u in to_update if not u['via_changed'] and u['mun_changed']]
    both = [u for u in to_update if u['via_changed'] and u['mun_changed']]

    if only_via:
        print(f"\nSolo INDIRIZZO ({len(only_via)}):")
        for u in only_via:
            print(f"  Sezione {u['numero']}:")
            print(f"    Via: {u['via_2025']}")
            print(f"         ↓")
            print(f"         {u['via_2026']}")

    if only_mun:
        print(f"\nSolo MUNICIPIO ({len(only_mun)}):")
        for u in only_mun:
            print(f"  Sezione {u['numero']}: Municipio {u['mun_2025']} → {u['mun_2026']}")
            print(f"    Via: {u['via_2025']}")

    if both:
        print(f"\nINDIRIZZO + MUNICIPIO ({len(both)}):")
        for u in both:
            print(f"  Sezione {u['numero']}:")
            print(f"    Via: {u['via_2025']}")
            print(f"         ↓")
            print(f"         {u['via_2026']}")
            print(f"    Municipio: {u['mun_2025']} → {u['mun_2026']}")

print()
print("=" * 80)
print("ISTRUZIONI PER L'AGGIORNAMENTO:")
print("=" * 80)
print()
print("1. Assicurati che il database è disponibile")
print("2. Esegui il comando Django:")
print()
print("   # Anteprima (dry-run):")
print("   python manage.py update_sezioni_2026 --dry-run")
print()
print("   # Aggiorna senza eliminare:")
print("   python manage.py update_sezioni_2026")
print()
print("   # Aggiorna ed elimina sezioni 9001-9007:")
print("   python manage.py update_sezioni_2026 --delete-removed")
print()
print("=" * 80)
