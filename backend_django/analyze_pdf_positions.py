#!/usr/bin/env python
"""
Analizza le posizioni degli oggetti nel PDF generato.
"""
import sys
from PyPDF2 import PdfReader

pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test_pdf_output.pdf'

print(f"Analisi PDF: {pdf_path}\n")

reader = PdfReader(pdf_path)
page = reader.pages[0]

# MediaBox (dimensioni pagina)
mediabox = page.mediabox
print(f"MediaBox: {mediabox}")
print(f"  Width: {mediabox.width}")
print(f"  Height: {mediabox.height}")
print(f"  (A4 = 595.27 x 841.89 punti)\n")

# Estrai contenuto
if '/Contents' in page:
    print("Contenuto pagina:")
    try:
        content = page.get_contents()
        if content:
            content_data = content.get_data().decode('latin-1', errors='ignore')

            # Cerca operazioni di testo (Tj, TJ, ')
            print("\nOperazioni di disegno testo (Tj):")
            lines = content_data.split('\n')
            for i, line in enumerate(lines):
                if 'Tj' in line or 'TJ' in line or ') Tj' in line:
                    # Mostra contesto (3 righe prima)
                    start = max(0, i-3)
                    print(f"\n  Riga {i}:")
                    for j in range(start, min(i+2, len(lines))):
                        print(f"    {lines[j]}")

            # Cerca trasformazioni (Tm, Td)
            print("\n\nTrasformazioni di posizione (Tm, Td):")
            for i, line in enumerate(lines):
                if ' Tm' in line or ' Td' in line:
                    print(f"  {line.strip()}")

    except Exception as e:
        print(f"Errore estrazione contenuto: {e}")

# Estrai testo
print("\n\nTesto estratto:")
text = page.extract_text()
print(repr(text))

print("\n\n=== INTERPRETAZIONE ===")
print("Se vedi coordinate Y molto alte (>700), il testo è vicino al TOP della pagina.")
print("Se vedi coordinate Y basse (<200), il testo è vicino al BOTTOM della pagina.")
print("\nCon la conversione corretta:")
print("  editor_y=100 (100px dall'alto) → pdf_y = 841.89 - 100 = 741.89 (vicino al top)")
print("  editor_y=750 (750px dall'alto) → pdf_y = 841.89 - 750 = 91.89 (vicino al bottom)")
