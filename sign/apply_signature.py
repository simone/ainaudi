#!/usr/bin/env python3
"""
Applica la firma PNG su tutte le pagine del PDF.
Uso:
  python3 apply_signature.py                    # test su pagina 1 → test_firma.pdf
  python3 apply_signature.py --all              # applica a tutte le pagine → output firmato
  python3 apply_signature.py --x 350 --y 430   # posizione custom
"""
import argparse
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import os

def create_signature_overlay(img_path, page_width, page_height, x, y, sig_width, sig_height, text=None, text_x=None, text_y=None, font_size=12):
    """Crea un PDF overlay trasparente con la firma posizionata."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Disegna l'immagine della firma
    c.drawImage(
        ImageReader(img_path), x, y, sig_width, sig_height,
        mask='auto',  # preserva trasparenza PNG
        preserveAspectRatio=True
    )

    # Aggiungi testo se specificato
    if text:
        c.setFont('Helvetica-Bold', font_size)
        # Se non specificato, posiziona il testo sotto la firma
        tx = text_x if text_x is not None else x
        ty = text_y if text_y is not None else (y - 15)
        c.drawString(tx, ty, text)

    c.save()
    packet.seek(0)
    return PdfReader(packet).pages[0]

def main():
    parser = argparse.ArgumentParser(description='Applica firma PNG al PDF')
    parser.add_argument('--all', action='store_true', help='Applica a tutte le pagine')
    parser.add_argument('--x', type=float, default=203, help='Posizione X della firma (pt da sinistra)')
    parser.add_argument('--y', type=float, default=259, help='Posizione Y della firma (pt dal basso)')
    parser.add_argument('--w', type=float, default=139, help='Larghezza firma (pt)')
    parser.add_argument('--h', type=float, default=139, help='Altezza firma (pt)')
    parser.add_argument('--pdf', default='Linda_Meleo_Nomine_Individuali_18_Marzo_Referendum_2026_v2.pdf')
    parser.add_argument('--img', default='spamp_18.png')
    parser.add_argument('--text', type=str, default='LINDA MELEO', help='Testo da aggiungere (es. "LINDA MELEO")')
    parser.add_argument('--text-x', type=float, default=393, help='Posizione X del testo')
    parser.add_argument('--text-y', type=float, default=360, help='Posizione Y del testo')
    parser.add_argument('--font-size', type=float, default=10, help='Dimensione font (default: 10)')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, args.pdf)
    img_path = os.path.join(script_dir, args.img)

    print(f"PDF: {pdf_path}")
    print(f"Firma: {img_path}")
    print(f"Posizione: x={args.x}, y={args.y}, w={args.w}, h={args.h}")
    if args.text:
        tx = args.text_x if args.text_x is not None else args.x
        ty = args.text_y if args.text_y is not None else (args.y - 15)
        print(f"Testo: '{args.text}' @ x={tx}, y={ty}, font={args.font_size}pt")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total = len(reader.pages)

    page_width = float(reader.pages[0].mediabox.width)
    page_height = float(reader.pages[0].mediabox.height)
    print(f"Pagine: {total}, dimensioni: {page_width:.0f} x {page_height:.0f} pt")

    if args.all:
        pages_to_sign = range(total)
        output_name = args.pdf.replace('.pdf', '_firmato.pdf')
        print(f"Applico firma a tutte le {total} pagine...")
    else:
        pages_to_sign = [0]  # solo prima pagina per test
        output_name = 'test_firma.pdf'
        print("TEST: firma solo sulla prima pagina")

    for i in range(total):
        page = reader.pages[i]
        if i in pages_to_sign:
            overlay = create_signature_overlay(
                img_path, page_width, page_height,
                args.x, args.y, args.w, args.h,
                text=args.text,
                text_x=args.text_x,
                text_y=args.text_y,
                font_size=args.font_size
            )
            page.merge_page(overlay)
        writer.add_page(page)

        if (i + 1) % 100 == 0 or i == total - 1:
            print(f"  {i+1}/{total}")

    output_path = os.path.join(script_dir, output_name)
    with open(output_path, 'wb') as f:
        writer.write(f)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nSalvato: {output_path} ({size_mb:.1f} MB)")

if __name__ == '__main__':
    main()
