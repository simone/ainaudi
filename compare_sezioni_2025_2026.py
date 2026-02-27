#!/usr/bin/env python3
"""
Compare Roma electoral sections 2025 vs 2026 CSV sources.
Generates detailed report by municipality.
"""

import csv
import re
from collections import defaultdict


def normalize_address(address):
    """Normalize address for comparison."""
    if not address:
        return ""
    # Convert to uppercase
    addr = address.upper().strip()
    # Remove multiple spaces
    addr = re.sub(r'\s+', ' ', addr)
    # Remove punctuation at the end
    addr = addr.rstrip('.,;')
    # Normalize common abbreviations
    addr = addr.replace('S.', 'S')
    addr = addr.replace('SS.', 'SS')
    addr = addr.replace("'", "'")
    # Normalize separators: comma + number → "N."
    addr = re.sub(r',\s*(\d+)', r' N. \1', addr)
    return addr


def parse_csv_2025_2026(csv_path):
    """Parse the CSV 2025/2026 format and extract all sections."""
    sections = {}

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                section_num = int(row['numero'])
                sections[section_num] = {
                    'section': section_num,
                    'municipio': int(row['municipio']),
                    'address': row['via'].strip(),
                }
            except (KeyError, ValueError):
                # Skip invalid rows
                pass

    return sections


def compare_sections(sections_2025, sections_2026):
    """Compare sections from both sources."""

    # Get all section numbers
    all_sections = sorted(set(sections_2025.keys()) | set(sections_2026.keys()))

    # Sections only in 2025
    only_2025 = sorted(set(sections_2025.keys()) - set(sections_2026.keys()))
    # Sections only in 2026
    only_2026 = sorted(set(sections_2026.keys()) - set(sections_2025.keys()))

    # Sections with different municipio
    different_municipio = []
    # Sections with different address
    different_address = []

    # Compare common sections
    common_sections = sorted(set(sections_2025.keys()) & set(sections_2026.keys()))
    for section_num in common_sections:
        data_2025 = sections_2025[section_num]
        data_2026 = sections_2026[section_num]

        # Compare municipio
        if data_2025['municipio'] != data_2026['municipio']:
            different_municipio.append({
                'section': section_num,
                'municipio_2025': data_2025['municipio'],
                'municipio_2026': data_2026['municipio'],
                'address_2025': data_2025['address'],
                'address_2026': data_2026['address'],
            })

        # Compare address (normalized)
        addr_2025_norm = normalize_address(data_2025['address'])
        addr_2026_norm = normalize_address(data_2026['address'])

        if addr_2025_norm != addr_2026_norm:
            different_address.append({
                'section': section_num,
                'address_2025': data_2025['address'],
                'address_2026': data_2026['address'],
                'municipio_2025': data_2025['municipio'],
                'municipio_2026': data_2026['municipio'],
            })

    return {
        'total_2025': len(sections_2025),
        'total_2026': len(sections_2026),
        'only_2025': only_2025,
        'only_2026': only_2026,
        'different_municipio': different_municipio,
        'different_address': different_address,
        'common_sections': len(common_sections)
    }


def print_report(comparison, sections_2025, sections_2026):
    """Print the comparison report in detailed format."""
    print("=" * 80)
    print("ROMA ELECTORAL SECTIONS COMPARISON: 2025 vs 2026")
    print("=" * 80)
    print()

    print(f"Total sections in 2025:  {comparison['total_2025']}")
    print(f"Total sections in 2026:  {comparison['total_2026']}")
    print(f"Common sections:         {comparison['common_sections']}")
    print()

    # Sections only in 2025 (removed)
    print("-" * 80)
    print(f"SECTIONS REMOVED in 2026 ({len(comparison['only_2025'])} sections)")
    print("-" * 80)
    if comparison['only_2025']:
        for section in comparison['only_2025']:
            s = sections_2025[section]
            print(f"  Section {section}: {s['address']} (Municipio {s['municipio']})")
    else:
        print("  None")
    print()

    # Sections only in 2026 (new)
    print("-" * 80)
    print(f"SECTIONS NEW in 2026 ({len(comparison['only_2026'])} sections)")
    print("-" * 80)
    if comparison['only_2026']:
        for section in comparison['only_2026']:
            s = sections_2026[section]
            print(f"  Section {section}: {s['address']} (Municipio {s['municipio']})")
    else:
        print("  None")
    print()

    # Sections with different municipio
    print("-" * 80)
    print(f"SECTIONS WITH DIFFERENT MUNICIPIO ({len(comparison['different_municipio'])} sections)")
    print("-" * 80)
    if comparison['different_municipio']:
        for item in comparison['different_municipio']:
            print(f"  Section {item['section']:4d}: 2025=Municipio {item['municipio_2025']}, 2026=Municipio {item['municipio_2026']}")
            print(f"    2025: {item['address_2025']}")
            print(f"    2026: {item['address_2026']}")
    else:
        print("  None")
    print()

    # Sections with different address
    print("-" * 80)
    print(f"SECTIONS WITH DIFFERENT ADDRESS ({len(comparison['different_address'])} sections)")
    print("-" * 80)
    if comparison['different_address']:
        # Print first 100 and summarize if more
        display_limit = 100
        for i, item in enumerate(comparison['different_address']):
            if i < display_limit:
                print(f"  Section {item['section']:4d}:")
                print(f"    2025: {item['address_2025']}")
                print(f"    2026: {item['address_2026']}")
                if item['municipio_2025'] != item['municipio_2026']:
                    print(f"    Municipio: {item['municipio_2025']} → {item['municipio_2026']}")
                print()
            elif i == display_limit:
                print(f"  ... and {len(comparison['different_address']) - display_limit} more address differences")
                break
    else:
        print("  None")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Matching sections:     {comparison['common_sections']}")
    print(f"✗ Removed in 2026:       {len(comparison['only_2025'])}")
    print(f"✓ New in 2026:           {len(comparison['only_2026'])}")
    print(f"✗ Different Municipio:   {len(comparison['different_municipio'])}")
    print(f"✗ Different Address:     {len(comparison['different_address'])}")
    print()


def print_summary_by_municipio(comparison, sections_2025, sections_2026):
    """Print summary organized by municipio."""
    print("\n" + "=" * 80)
    print("DETAILED CHANGES BY MUNICIPIO")
    print("=" * 80)
    print()

    # Group differences by municipio (use 2026 as reference)
    changes_by_mun = defaultdict(list)

    for item in comparison['different_address']:
        mun_2026 = item['municipio_2026']
        changes_by_mun[mun_2026].append(('ADDRESS', item))

    for item in comparison['different_municipio']:
        mun_2026 = item['municipio_2026']
        changes_by_mun[mun_2026].append(('MUNICIPIO', item))

    # Print by municipio
    for mun in sorted(changes_by_mun.keys()):
        changes = changes_by_mun[mun]
        print(f"Municipio {mun}:")

        # Group address changes by transition
        addr_transitions = defaultdict(list)
        mun_transitions = defaultdict(list)

        for change_type, item in changes:
            if change_type == 'ADDRESS':
                key = (item['address_2025'], item['address_2026'])
                addr_transitions[key].append(item['section'])
            else:  # MUNICIPIO
                key = (item['municipio_2025'], item['municipio_2026'])
                mun_transitions[key].append(item)

        # Print address transitions
        for (old_addr, new_addr), sections in sorted(addr_transitions.items()):
            sections_str = ', '.join(str(s) for s in sorted(sections))
            if len(sections) == 1:
                print(f"  - Section {sections_str} changed address from {old_addr} to {new_addr}")
            else:
                print(f"  - Sections {sections_str} changed address from {old_addr} to {new_addr}")

        # Print municipio transitions
        for (old_mun, new_mun), items in sorted(mun_transitions.items()):
            for item in items:
                print(f"  - Section {item['section']} moved from Municipio {old_mun} to {new_mun}")
                print(f"    2025: {item['address_2025']}")
                print(f"    2026: {item['address_2026']}")

        print()


if __name__ == '__main__':
    print("Parsing 2025 CSV...")
    sections_2025 = parse_csv_2025_2026('roma/sezioni_2025.csv')

    print("Parsing 2026 CSV...")
    sections_2026 = parse_csv_2025_2026('roma/sezioni_2026.csv')

    print("Comparing sections...")
    comparison = compare_sections(sections_2025, sections_2026)

    print()
    print_report(comparison, sections_2025, sections_2026)
    print_summary_by_municipio(comparison, sections_2025, sections_2026)
