#!/usr/bin/env python3
"""
Compare Roma electoral sections between PDF and CSV sources.
"""

import csv
import re
import sys
from collections import defaultdict
import PyPDF2

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
    return addr

def extract_section_from_pdf_line(line, current_municipio):
    """Extract section data from a PDF line."""
    # Pattern: Section number at start, then address, then CAP
    # Example: "1 Via di Settebagni, 231 00138"
    match = re.match(r'^(\d{1,4})\s+(.+?)\s+(\d{5})$', line.strip())
    if match:
        section_num = int(match.group(1))
        address = match.group(2).strip()
        cap = match.group(3)
        return {
            'section': section_num,
            'municipio': current_municipio,
            'address': address,
            'cap': cap
        }
    return None

def parse_pdf(pdf_path):
    """Parse the PDF and extract all sections."""
    sections = {}

    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        current_municipio = None

        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()

            lines = text.split('\n')
            for line in lines:
                line = line.strip()

                # Detect Municipio headers
                municipio_match = re.search(r'MUNICIPIO\s+([IVXL]+|[0-9]+)', line, re.IGNORECASE)
                if municipio_match:
                    municipio_str = municipio_match.group(1)
                    # Convert Roman numerals to numbers
                    roman_to_int = {
                        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
                        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
                        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15
                    }
                    current_municipio = roman_to_int.get(municipio_str, municipio_str)
                    if isinstance(current_municipio, str) and current_municipio.isdigit():
                        current_municipio = int(current_municipio)
                    continue

                # Try to extract section data
                if current_municipio and re.match(r'^\d{1,4}\s+', line):
                    section_data = extract_section_from_pdf_line(line, current_municipio)
                    if section_data:
                        sections[section_data['section']] = section_data

    return sections

def parse_csv(csv_path):
    """Parse the CSV and extract all sections."""
    sections = {}

    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            section_num = int(row['SEZIONE'])
            sections[section_num] = {
                'section': section_num,
                'municipio': int(row['MUNICIPIO']) if row['MUNICIPIO'].isdigit() else row['MUNICIPIO'],
                'address': row['INDIRIZZO'].strip(),
                'comune': row['COMUNE']
            }

    return sections

def compare_sections(pdf_sections, csv_sections):
    """Compare sections from both sources."""
    report = []

    # Get all section numbers
    all_sections = sorted(set(pdf_sections.keys()) | set(csv_sections.keys()))

    # Sections only in PDF
    only_pdf = sorted(set(pdf_sections.keys()) - set(csv_sections.keys()))
    # Sections only in CSV
    only_csv = sorted(set(csv_sections.keys()) - set(pdf_sections.keys()))

    # Sections with different municipio
    different_municipio = []
    # Sections with different address
    different_address = []

    # Compare common sections
    common_sections = sorted(set(pdf_sections.keys()) & set(csv_sections.keys()))
    for section_num in common_sections:
        pdf_data = pdf_sections[section_num]
        csv_data = csv_sections[section_num]

        # Compare municipio
        if pdf_data['municipio'] != csv_data['municipio']:
            different_municipio.append({
                'section': section_num,
                'pdf_municipio': pdf_data['municipio'],
                'csv_municipio': csv_data['municipio']
            })

        # Compare address (normalized)
        pdf_addr_norm = normalize_address(pdf_data['address'])
        csv_addr_norm = normalize_address(csv_data['address'])

        if pdf_addr_norm != csv_addr_norm:
            different_address.append({
                'section': section_num,
                'pdf_address': pdf_data['address'],
                'csv_address': csv_data['address']
            })

    return {
        'total_pdf': len(pdf_sections),
        'total_csv': len(csv_sections),
        'only_pdf': only_pdf,
        'only_csv': only_csv,
        'different_municipio': different_municipio,
        'different_address': different_address,
        'common_sections': len(common_sections)
    }

def print_report(comparison):
    """Print the comparison report."""
    print("=" * 80)
    print("ROMA ELECTORAL SECTIONS COMPARISON REPORT")
    print("=" * 80)
    print()

    print(f"Total sections in PDF:  {comparison['total_pdf']}")
    print(f"Total sections in CSV:  {comparison['total_csv']}")
    print(f"Common sections:        {comparison['common_sections']}")
    print()

    print("-" * 80)
    print(f"SECTIONS ONLY IN PDF ({len(comparison['only_pdf'])} sections)")
    print("-" * 80)
    if comparison['only_pdf']:
        for section in comparison['only_pdf']:
            print(f"  Section {section}")
    else:
        print("  None")
    print()

    print("-" * 80)
    print(f"SECTIONS ONLY IN CSV ({len(comparison['only_csv'])} sections)")
    print("-" * 80)
    if comparison['only_csv']:
        # Print first 50 and summarize if more
        display_limit = 50
        for i, section in enumerate(comparison['only_csv']):
            if i < display_limit:
                print(f"  Section {section}")
            elif i == display_limit:
                print(f"  ... and {len(comparison['only_csv']) - display_limit} more sections")
                break
    else:
        print("  None")
    print()

    print("-" * 80)
    print(f"SECTIONS WITH DIFFERENT MUNICIPIO ({len(comparison['different_municipio'])} sections)")
    print("-" * 80)
    if comparison['different_municipio']:
        for item in comparison['different_municipio']:
            print(f"  Section {item['section']:4d}: PDF=Municipio {item['pdf_municipio']}, CSV=Municipio {item['csv_municipio']}")
    else:
        print("  None")
    print()

    print("-" * 80)
    print(f"SECTIONS WITH DIFFERENT ADDRESS ({len(comparison['different_address'])} sections)")
    print("-" * 80)
    if comparison['different_address']:
        # Print first 100 and summarize if more
        display_limit = 100
        for i, item in enumerate(comparison['different_address']):
            if i < display_limit:
                print(f"  Section {item['section']:4d}:")
                print(f"    PDF: {item['pdf_address']}")
                print(f"    CSV: {item['csv_address']}")
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
    print(f"✓ Matching sections: {comparison['common_sections']}")
    print(f"✗ Missing in CSV: {len(comparison['only_pdf'])}")
    print(f"✗ Extra in CSV: {len(comparison['only_csv'])}")
    print(f"✗ Different Municipio: {len(comparison['different_municipio'])}")
    print(f"✗ Different Address: {len(comparison['different_address'])}")
    print()

if __name__ == '__main__':
    pdf_path = '/Users/aldaran/workspaces/m5s/rdleu2024/Seggi elettorali 2026.pdf'
    csv_path = '/Users/aldaran/workspaces/m5s/rdleu2024/backend_django/fixtures/ROMA - Sezioni.csv'

    print("Parsing PDF...")
    pdf_sections = parse_pdf(pdf_path)

    print("Parsing CSV...")
    csv_sections = parse_csv(csv_path)

    print("Comparing sections...")
    comparison = compare_sections(pdf_sections, csv_sections)

    print()
    print_report(comparison)
