#!/usr/bin/env python3
"""
Script standalone per testare la generazione PDF.
"""
import io
import sys
import os

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(__file__))

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter

def create_blank_template():
    """Crea un template PDF vuoto con un rettangolo."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Disegna un bordo per vedere l'area del template
    pdf.setStrokeColorRGB(0, 0, 1)  # Blu
    pdf.rect(50, 50, 500, 700)

    # Aggiungi testo di riferimento
    pdf.setFont("Helvetica", 10)
    pdf.drawString(60, 760, "Template PDF - Angolo alto-sinistra")
    pdf.drawString(60, 60, "Template PDF - Angolo basso-sinistra")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

def create_overlay_old_way(x, y, text):
    """Crea overlay con coordinate SBAGLIATE (come prima)."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    can.setFont("Helvetica", 12)
    can.setFillColorRGB(1, 0, 0)  # Rosso
    can.drawString(x, y, text)

    can.showPage()
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def create_overlay_new_way(editor_x, editor_y, text):
    """Crea overlay con coordinate CORRETTE (convertite)."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    # Conversione coordinate
    page_height = A4[1]  # 841.89
    pdf_y = page_height - editor_y

    can.setFont("Helvetica", 12)
    can.setFillColorRGB(0, 1, 0)  # Verde
    can.drawString(editor_x, pdf_y, f"{text} (editor_y={editor_y}, pdf_y={pdf_y:.1f})")

    can.showPage()
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def test_merge_order():
    """Testa l'ordine di merge."""
    print("=== Test 1: Ordine Merge ===")

    template_buffer = create_blank_template()

    # Test SBAGLIATO: template.merge_page(overlay)
    print("\n1. Template.merge_page(overlay) - SBAGLIATO")
    template_reader = PdfReader(template_buffer)
    overlay = create_overlay_new_way(100, 100, "Test SBAGLIATO")

    writer = PdfWriter()
    template_page = template_reader.pages[0]
    template_page.merge_page(overlay.pages[0])
    writer.add_page(template_page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    with open('/tmp/test_merge_wrong.pdf', 'wb') as f:
        f.write(output.read())
    print("   → Salvato in /tmp/test_merge_wrong.pdf")

    # Test CORRETTO: overlay.merge_page(template)
    print("\n2. Overlay.merge_page(template) - CORRETTO")
    template_buffer.seek(0)
    template_reader = PdfReader(template_buffer)
    overlay = create_overlay_new_way(100, 100, "Test CORRETTO")

    writer = PdfWriter()
    overlay_page = overlay.pages[0]
    overlay_page.merge_page(template_reader.pages[0])
    writer.add_page(overlay_page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    with open('/tmp/test_merge_correct.pdf', 'wb') as f:
        f.write(output.read())
    print("   → Salvato in /tmp/test_merge_correct.pdf")

def test_coordinates():
    """Testa conversione coordinate."""
    print("\n=== Test 2: Conversione Coordinate ===")

    template_buffer = create_blank_template()
    template_reader = PdfReader(template_buffer)

    writer = PdfWriter()

    # Crea overlay con testi a varie altezze
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_height = A4[1]

    test_positions = [
        (100, 50, "editor_y=50 (vicino alto)"),
        (100, 200, "editor_y=200"),
        (100, 400, "editor_y=400 (centro)"),
        (100, 600, "editor_y=600"),
        (100, 750, "editor_y=750 (vicino basso)"),
    ]

    can.setFont("Helvetica", 10)
    can.setFillColorRGB(0, 0, 0)

    for editor_x, editor_y, text in test_positions:
        pdf_y = page_height - editor_y
        can.drawString(editor_x, pdf_y, f"{text} → pdf_y={pdf_y:.1f}")

    can.showPage()
    can.save()
    packet.seek(0)

    overlay_reader = PdfReader(packet)
    overlay_page = overlay_reader.pages[0]
    overlay_page.merge_page(template_reader.pages[0])
    writer.add_page(overlay_page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    with open('/tmp/test_coordinates.pdf', 'wb') as f:
        f.write(output.read())
    print("   → Salvato in /tmp/test_coordinates.pdf")

def test_extract_text():
    """Estrai testo dai PDF generati per verificare."""
    print("\n=== Test 3: Estrazione Testo ===")

    files = [
        '/tmp/test_merge_wrong.pdf',
        '/tmp/test_merge_correct.pdf',
        '/tmp/test_coordinates.pdf'
    ]

    for filepath in files:
        if os.path.exists(filepath):
            reader = PdfReader(filepath)
            text = reader.pages[0].extract_text()
            print(f"\n{os.path.basename(filepath)}:")
            print(f"   Contenuto: {text[:200]}...")
        else:
            print(f"\n{filepath}: NON TROVATO")

if __name__ == '__main__':
    print("Test Generazione PDF con PyPDF2 + ReportLab\n")
    print(f"A4 size: {A4[0]:.2f} x {A4[1]:.2f} punti\n")

    test_merge_order()
    test_coordinates()
    test_extract_text()

    print("\n✓ Test completati! Apri i PDF in /tmp/ per verificare visualmente.")
