"""
PDF generator for scrutinio data collection forms.

Generates printable A4 forms pre-filled with section info,
with clear boxes for manual number entry (optimized for later OCR/photo capture).
"""
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# Layout constants
PAGE_W, PAGE_H = A4  # 595.28 x 841.89 points
MARGIN_LEFT = 15 * mm
MARGIN_RIGHT = 15 * mm
MARGIN_TOP = 15 * mm
MARGIN_BOTTOM = 12 * mm
CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT

# Colors
COLOR_PRIMARY = colors.HexColor('#1F4E5F')
COLOR_M5S_YELLOW = colors.HexColor('#FFC800')
COLOR_LIGHT_BG = colors.HexColor('#F0F4F8')
COLOR_GRID = colors.HexColor('#CCCCCC')
COLOR_BOX_BG = colors.HexColor('#FFFFFF')
COLOR_LABEL = colors.HexColor('#333333')


def _find_logo():
    """Find the M5S logo file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    possible_paths = [
        os.path.join(project_root, "resources", "assets", "logo-m5s.png"),
        os.path.join(current_dir, "..", "resources", "assets", "logo-m5s.png"),
        "/app/resources/assets/logo-m5s.png",  # Docker
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _draw_header(c, consultazione_nome, sezione_info, page_num, total_pages, logo_path):
    """Draw page header with logo, title, consultazione and section info."""
    y = PAGE_H - MARGIN_TOP

    # === LOGO + TITLE BAR ===
    bar_height = 40
    c.setFillColor(COLOR_PRIMARY)
    c.rect(MARGIN_LEFT, y - bar_height, CONTENT_W, bar_height, fill=1, stroke=0)

    # Logo (left side)
    logo_w = 0
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            logo_h = bar_height - 8
            logo_w = logo_h  # square
            c.drawImage(logo, MARGIN_LEFT + 6, y - bar_height + 4, logo_w, logo_h,
                        preserveAspectRatio=True, mask='auto')
            logo_w += 12  # padding after logo
        except Exception:
            logo_w = 0

    # Title: AINAUDI.IT
    title_x = MARGIN_LEFT + logo_w + 4
    c.setFillColor(COLOR_M5S_YELLOW)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(title_x, y - 17, "AINAUDI.IT")

    # Subtitle
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawString(title_x, y - 30, f"Raccolta dati ai seggi per il \"{consultazione_nome}\"")

    # Page number (right)
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN_RIGHT - 6, y - 30, f"Pag. {page_num}/{total_pages}")

    y -= bar_height + 10

    # === SEZIONE NUMBER (big, prominent) ===
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGIN_LEFT, y, f"SEZIONE {sezione_info['numero']}")
    y -= 20

    # Section details row
    c.setFillColor(COLOR_LIGHT_BG)
    c.rect(MARGIN_LEFT, y - 16, CONTENT_W, 16, fill=1, stroke=0)
    c.setStrokeColor(COLOR_GRID)
    c.rect(MARGIN_LEFT, y - 16, CONTENT_W, 16, fill=0, stroke=1)
    c.setFillColor(COLOR_LABEL)
    c.setFont("Helvetica-Bold", 8)

    comune_text = sezione_info.get('comune', '')
    if sezione_info.get('municipio'):
        comune_text += f" ({sezione_info['municipio']})"
    c.drawString(MARGIN_LEFT + 4, y - 12, comune_text)

    indirizzo = sezione_info.get('indirizzo', '')
    denominazione = sezione_info.get('denominazione', '')
    loc_text = indirizzo
    if denominazione:
        loc_text += f" - {denominazione}"
    if loc_text:
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN_LEFT + 200, y - 12, loc_text[:55])

    y -= 28
    return y


def _draw_digit_boxes(c, x, y, n_boxes=5, box_size=9 * mm, spacing=1.5 * mm):
    """Draw a row of empty digit boxes for number entry."""
    for i in range(n_boxes):
        bx = x + i * (box_size + spacing)
        c.setStrokeColor(COLOR_GRID)
        c.setLineWidth(0.8)
        c.setFillColor(COLOR_BOX_BG)
        c.rect(bx, y, box_size, box_size, fill=1, stroke=1)
    return x + n_boxes * (box_size + spacing)


def _draw_field_row(c, y, label, n_boxes=5, label_width=160):
    """Draw a labeled row with digit boxes. Returns new y position."""
    box_size = 9 * mm
    spacing = 1.5 * mm
    row_h = box_size + 4

    # Label vertically centered with boxes
    c.setFillColor(COLOR_LABEL)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN_LEFT + 4, y + (box_size / 2) - 3, label)

    # Boxes aligned to right of label
    boxes_x = MARGIN_LEFT + label_width
    _draw_digit_boxes(c, boxes_x, y, n_boxes=n_boxes, box_size=box_size, spacing=spacing)

    return y - row_h - 4


def _draw_section_title(c, y, title):
    """Draw a section divider with title. Returns y below the line with enough gap for field rows."""
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN_LEFT, y, title)
    y -= 5
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1.2)
    c.line(MARGIN_LEFT, y, PAGE_W - MARGIN_RIGHT, y)
    # 22pt gap: field labels extend ~10pt above their y, so need ample clearance
    return y - 22


def _draw_turnout_section(c, y):
    """Draw the turnout (affluenza) fields — common to all ballots."""
    y = _draw_section_title(c, y, "DATI AFFLUENZA (comuni a tutte le schede)")

    y = _draw_field_row(c, y, "Elettori iscritti MASCHI")
    y = _draw_field_row(c, y, "Elettori iscritti FEMMINE")
    y -= 4
    y = _draw_field_row(c, y, "Votanti MASCHI")
    y = _draw_field_row(c, y, "Votanti FEMMINE")

    return y - 8


def _draw_scheda_section(c, y, scheda_nome, scheda_colore, schema_voti):
    """Draw per-ballot section with fields based on schema."""
    color_label = f" ({scheda_colore})" if scheda_colore else ""
    y = _draw_section_title(c, y, f"SCHEDA: {scheda_nome}{color_label}")

    # Common ballot fields
    y = _draw_field_row(c, y, "Schede ricevute")
    y = _draw_field_row(c, y, "Schede autenticate")
    y = _draw_field_row(c, y, "Schede bianche")
    y = _draw_field_row(c, y, "Schede nulle")
    y = _draw_field_row(c, y, "Schede contestate")

    y -= 4

    # Vote fields based on schema type
    tipo = schema_voti.get('tipo', '') if schema_voti else ''

    if tipo == 'si_no':
        y = _draw_field_row(c, y, "Voti SI")
        y = _draw_field_row(c, y, "Voti NO")
    elif tipo in ('liste_candidati', 'liste_preferenze'):
        # For elections with lists: provide blank rows for list names + votes
        c.setFillColor(COLOR_LABEL)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(MARGIN_LEFT + 4, y + 2, "Voti per lista (nome lista -> voti):")
        y -= 14
        for _ in range(8):  # 8 blank rows for lists
            c.setStrokeColor(COLOR_GRID)
            c.setLineWidth(0.4)
            c.line(MARGIN_LEFT + 4, y, MARGIN_LEFT + 140, y)
            _draw_digit_boxes(c, MARGIN_LEFT + 150, y - 2, n_boxes=5)
            y -= (9 * mm + 6)
    else:
        # Generic: just provide blank space for notes
        y = _draw_field_row(c, y, "Voti validi totali")

    return y - 6


def _draw_notes_section(c, y):
    """Draw a notes/observations area at the bottom."""
    c.setFillColor(COLOR_LABEL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN_LEFT, y, "NOTE / OSSERVAZIONI:")
    y -= 6
    c.setStrokeColor(COLOR_GRID)
    c.setLineWidth(0.4)
    for _ in range(3):
        c.line(MARGIN_LEFT, y, PAGE_W - MARGIN_RIGHT, y)
        y -= 14
    return y


def _draw_footer(c):
    """Draw footer with signature line and timestamp placeholder."""
    y = MARGIN_BOTTOM + 8
    c.setStrokeColor(COLOR_GRID)
    c.setLineWidth(0.5)

    # Signature line
    c.setFont("Helvetica", 7)
    c.setFillColor(COLOR_LABEL)
    sig_x = MARGIN_LEFT
    c.line(sig_x, y, sig_x + 150, y)
    c.drawString(sig_x, y - 8, "Firma RDL")

    # Date/time line
    dt_x = PAGE_W - MARGIN_RIGHT - 150
    c.line(dt_x, y, dt_x + 150, y)
    c.drawString(dt_x, y - 8, "Data e ora compilazione")

    # Yellow accent line at very bottom
    c.setStrokeColor(COLOR_M5S_YELLOW)
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, MARGIN_BOTTOM - 4, PAGE_W - MARGIN_RIGHT, MARGIN_BOTTOM - 4)


def generate_scrutinio_form(consultazione, sezioni_with_schede):
    """
    Generate a printable scrutinio data collection PDF.

    Args:
        consultazione: ConsultazioneElettorale instance
        sezioni_with_schede: list of dicts:
            [{
                'numero': '42',
                'comune': 'Roma',
                'municipio': 'Municipio I',
                'indirizzo': 'Via degli Animali 45',
                'denominazione': 'Scuola Elementare Topolino',
                'schede': [
                    {'nome': 'Referendum n.1', 'colore': 'verde', 'schema_voti': {'tipo': 'si_no'}},
                    ...
                ]
            }]

    Returns:
        io.BytesIO with PDF content
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    logo_path = _find_logo()

    total_pages = len(sezioni_with_schede)

    for page_idx, sezione in enumerate(sezioni_with_schede):
        y = _draw_header(
            c,
            consultazione_nome=consultazione.nome,
            sezione_info=sezione,
            page_num=page_idx + 1,
            total_pages=total_pages,
            logo_path=logo_path,
        )

        # Turnout section
        y = _draw_turnout_section(c, y)

        # Per-scheda sections
        for scheda in sezione.get('schede', []):
            needed_height = 200
            if y - needed_height < MARGIN_BOTTOM + 40:
                _draw_footer(c)
                c.showPage()
                total_pages += 1
                y = _draw_header(
                    c,
                    consultazione_nome=consultazione.nome,
                    sezione_info=sezione,
                    page_num=total_pages,
                    total_pages=total_pages,
                    logo_path=logo_path,
                )

            y = _draw_scheda_section(
                c, y,
                scheda_nome=scheda['nome'],
                scheda_colore=scheda.get('colore', ''),
                schema_voti=scheda.get('schema_voti', {}),
            )

        # Notes at bottom
        if y > MARGIN_BOTTOM + 60:
            y = _draw_notes_section(c, y)

        # Footer
        _draw_footer(c)

        # New page for next section
        if page_idx < len(sezioni_with_schede) - 1:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
