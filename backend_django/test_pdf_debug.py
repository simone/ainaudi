#!/usr/bin/env python
"""
Script per generare un PDF di test e verificarne il contenuto.
"""
import os
import sys
import django
import io
from datetime import date

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from documents.pdf_generator import PDFGenerator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader

def create_blank_template():
    """Crea un template PDF vuoto per test."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Disegna un bordo blu per vedere l'area
    pdf.setStrokeColorRGB(0, 0, 1)
    pdf.rect(50, 50, 500, 700)

    # Scrivi "TEMPLATE" al centro
    pdf.setFont("Helvetica", 24)
    pdf.setFillColorRGB(0.9, 0.9, 0.9)
    pdf.drawString(250, 400, "TEMPLATE")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

# Dati di test
data = {
    'delegato': {
        'cognome': 'Rossi',
        'nome': 'Mario',
        'carica': 'Deputato',
        'data_nascita': date(1980, 5, 15)
    }
}

# Field mappings con coordinate dall'editor (top-left origin)
# editor_y=100 significa 100px dall'alto
field_mappings = [
    {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 100, 'page': 0, 'font_size': 14},
    {'jsonpath': '$.delegato.nome', 'x': 250, 'y': 100, 'page': 0, 'font_size': 14},
    {'jsonpath': '$.delegato.carica', 'x': 100, 'y': 150, 'page': 0, 'font_size': 12},
    {'jsonpath': '$.delegato.data_nascita', 'x': 100, 'y': 200, 'page': 0, 'font_size': 10},
]

# Crea template
print("1. Creazione template PDF vuoto...")
template_buffer = create_blank_template()

# Crea mock template object
class MockTemplate:
    pass

mock_template = MockTemplate()
mock_template.field_mappings = field_mappings

# Genera PDF
print("2. Generazione PDF con PDFGenerator...")
generator = PDFGenerator(template_buffer, data)
output = generator.generate_from_template(mock_template)

# Salva PDF
output_path = '/tmp/test_pdf_output.pdf'
with open(output_path, 'wb') as f:
    f.write(output.read())
print(f"3. PDF salvato in: {output_path}")

# Leggi e verifica
print("\n4. Verifica contenuto PDF:")
output.seek(0)
reader = PdfReader(output)
print(f"   - Numero pagine: {len(reader.pages)}")

page = reader.pages[0]
text = page.extract_text()

print(f"   - Testo estratto: {repr(text[:500])}")
print(f"\n5. Verifica presenza dati:")
print(f"   - 'Rossi' trovato: {'Rossi' in text}")
print(f"   - 'Mario' trovato: {'Mario' in text}")
print(f"   - 'Deputato' trovato: {'Deputato' in text}")
print(f"   - '15/05/1980' trovato: {'15/05/1980' in text}")

print(f"\n✓ Test completato! Apri {output_path} per verificare visualmente.")
print(f"\nSe il testo NON è visibile nel PDF, il problema è con merge_page().")
print(f"Se il testo è in posizione SBAGLIATA, il problema è con la conversione coordinate.")
