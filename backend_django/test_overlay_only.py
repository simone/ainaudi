#!/usr/bin/env python
"""
Test overlay senza merge per verificare le coordinate.
"""
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfWriter, PdfReader

# Crea overlay con coordinate convertite
def create_test_overlay():
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_height = A4[1]

    # Disegna griglia di riferimento
    can.setStrokeColorRGB(0.9, 0.9, 0.9)
    for y in range(0, int(page_height), 50):
        can.line(0, y, A4[0], y)
        can.setFont("Helvetica", 8)
        can.setFillColorRGB(0.5, 0.5, 0.5)
        can.drawString(5, y, f"Y={y}")

    # Test posizioni con conversione coordinate
    test_data = [
        (100, 50, "editor_y=50 → pdf_y=791.89 (ALTO)"),
        (100, 100, "editor_y=100 → pdf_y=741.89"),
        (100, 200, "editor_y=200 → pdf_y=641.89"),
        (100, 400, "editor_y=400 → pdf_y=441.89 (CENTRO)"),
        (100, 600, "editor_y=600 → pdf_y=241.89"),
        (100, 750, "editor_y=750 → pdf_y=91.89 (BASSO)"),
    ]

    can.setFont("Helvetica", 12)
    can.setFillColorRGB(1, 0, 0)  # Rosso

    for editor_x, editor_y, text in test_data:
        # Conversione coordinate
        pdf_y = page_height - editor_y

        # Disegna marker
        can.circle(editor_x - 5, pdf_y, 3, fill=1)

        # Scrivi testo
        can.drawString(editor_x, pdf_y, text)

    can.showPage()
    can.save()
    packet.seek(0)
    return packet

# Genera PDF
print("Generazione overlay con coordinate convertite...")
overlay_buffer = create_test_overlay()

# Salva direttamente
with open('/tmp/test_overlay_only.pdf', 'wb') as f:
    f.write(overlay_buffer.read())

print("✓ PDF salvato in: /tmp/test_overlay_only.pdf")
print("\nApri il file e verifica:")
print("  - Il testo con editor_y=50 deve essere vicino al TOP")
print("  - Il testo con editor_y=750 deve essere vicino al BOTTOM")
print("  - Se è corretto, allora la conversione funziona!")
