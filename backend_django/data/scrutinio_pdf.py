"""
PDF generator for scrutinio data collection forms.

Generates printable A4 forms pre-filled with section info,
with underline fields for manual number entry (optimized for photo capture).
Font sizes and spacing adapt to fill the available page space.
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
COLOR_LABEL = colors.HexColor('#333333')
COLOR_UNDERLINE = colors.HexColor('#999999')

# Footer height (signature + date + yellow line)
FOOTER_HEIGHT = 30


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


def _count_field_rows(schede):
    """Count how many field rows we need for all sections on the page."""
    # Affluenza: 2 rows (Elettori M/F, Votanti M/F)
    rows = 2

    for scheda in schede:
        # Section title counts as a separator, not a row
        # Group 1: ricevute/autenticate = 1 row
        rows += 1
        # Group 2: votes
        tipo = (scheda.get('schema_voti') or {}).get('tipo', '')
        if tipo == 'si_no':
            rows += 1  # SI/NO paired
        elif tipo in ('liste_candidati', 'liste_preferenze'):
            rows += 9  # header + 8 list rows
        else:
            rows += 1  # voti validi
        # Group 3: bianche/nulle + contestate = 2 rows
        rows += 2

    # Notes: title + 4 lines = ~3 rows equivalent
    rows += 3

    return rows


def _draw_header(c, consultazione_nome, sezione_info, page_num, total_pages, logo_path):
    """Draw page header: logo bar on top, then section number below."""
    y = PAGE_H - MARGIN_TOP

    # === LOGO + TITLE BAR ===
    bar_height = 28
    c.setFillColor(COLOR_PRIMARY)
    c.rect(MARGIN_LEFT, y - bar_height, CONTENT_W, bar_height, fill=1, stroke=0)

    logo_w = 0
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            logo_h = bar_height - 6
            logo_w = logo_h
            c.drawImage(logo, MARGIN_LEFT + 4, y - bar_height + 3, logo_w, logo_h,
                        preserveAspectRatio=True, mask='auto')
            logo_w += 10
        except Exception:
            logo_w = 0

    title_x = MARGIN_LEFT + logo_w + 4
    c.setFillColor(COLOR_M5S_YELLOW)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(title_x, y - 12, "AINAUDI.IT")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7)
    c.drawString(title_x, y - 22, f"Raccolta dati: \"{consultazione_nome}\"")

    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN_RIGHT - 6, y - 12, f"Pag. {page_num}/{total_pages}")

    y -= bar_height + 14

    # === SEZIONE NUMBER ===
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(MARGIN_LEFT, y - 22, f"SEZIONE {sezione_info['numero']}")
    y -= 38

    # Section details row
    c.setFillColor(COLOR_LIGHT_BG)
    c.rect(MARGIN_LEFT, y - 18, CONTENT_W, 18, fill=1, stroke=0)
    c.setStrokeColor(COLOR_GRID)
    c.rect(MARGIN_LEFT, y - 18, CONTENT_W, 18, fill=0, stroke=1)
    c.setFillColor(COLOR_LABEL)
    c.setFont("Helvetica-Bold", 9)

    comune_text = sezione_info.get('comune', '')
    if sezione_info.get('municipio'):
        comune_text += f" ({sezione_info['municipio']})"
    c.drawString(MARGIN_LEFT + 6, y - 13, comune_text)

    indirizzo = sezione_info.get('indirizzo', '')
    denominazione = sezione_info.get('denominazione', '')
    loc_text = indirizzo
    if denominazione:
        loc_text += f" - {denominazione}"
    if loc_text:
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN_LEFT + 210, y - 13, loc_text[:55])

    y -= 30
    return y


def _draw_underline_field(c, x, y, label, font_size, field_width):
    """Draw a label followed by an underline for writing."""
    c.setFillColor(COLOR_LABEL)
    c.setFont("Helvetica", font_size)
    c.drawString(x, y, label)
    label_end = x + c.stringWidth(label, "Helvetica", font_size) + 8

    c.setStrokeColor(COLOR_UNDERLINE)
    c.setLineWidth(0.8)
    c.line(label_end, y - 3, label_end + field_width, y - 3)


def _draw_paired_row(c, y, label_left, label_right, font_size, field_width):
    """Draw two label+underline fields side by side."""
    col_width = CONTENT_W / 2
    _draw_underline_field(c, MARGIN_LEFT + 6, y, label_left, font_size, field_width)
    _draw_underline_field(c, MARGIN_LEFT + col_width + 6, y, label_right, font_size, field_width)


def _draw_single_row(c, y, label, font_size, field_width):
    """Draw a single label+underline field."""
    _draw_underline_field(c, MARGIN_LEFT + 6, y, label, font_size, field_width)


def _draw_section_title(c, y, title, font_size):
    """Draw a section divider with title."""
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(MARGIN_LEFT, y, title)
    y -= 5
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1.2)
    c.line(MARGIN_LEFT, y, PAGE_W - MARGIN_RIGHT, y)
    return y


def _draw_footer(c):
    """Draw footer with signature line and timestamp placeholder."""
    y = MARGIN_BOTTOM + 8
    c.setStrokeColor(COLOR_GRID)
    c.setLineWidth(0.5)

    c.setFont("Helvetica", 7)
    c.setFillColor(COLOR_LABEL)
    sig_x = MARGIN_LEFT
    c.line(sig_x, y, sig_x + 150, y)
    c.drawString(sig_x, y - 8, "Firma RDL")

    dt_x = PAGE_W - MARGIN_RIGHT - 150
    c.line(dt_x, y, dt_x + 150, y)
    c.drawString(dt_x, y - 8, "Data e ora compilazione")

    c.setStrokeColor(COLOR_M5S_YELLOW)
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, MARGIN_BOTTOM - 4, PAGE_W - MARGIN_RIGHT, MARGIN_BOTTOM - 4)


def generate_scrutinio_form(consultazione, sezioni_with_schede):
    """
    Generate a printable scrutinio data collection PDF.

    Layout adapts to fill the page: fewer fields = larger font and more spacing.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Modulo Scrutinio - {consultazione.nome}")
    c.setAuthor("AInaudi.it")
    logo_path = _find_logo()

    total_pages = len(sezioni_with_schede)

    for page_idx, sezione in enumerate(sezioni_with_schede):
        y_after_header = _draw_header(
            c,
            consultazione_nome=consultazione.nome,
            sezione_info=sezione,
            page_num=page_idx + 1,
            total_pages=total_pages,
            logo_path=logo_path,
        )

        # Calculate available space and adaptive sizing
        available_height = y_after_header - MARGIN_BOTTOM - FOOTER_HEIGHT
        schede = sezione.get('schede', [])
        num_rows = _count_field_rows(schede)
        num_sections = 1 + len(schede) + 1  # affluenza + schede + notes

        # Space per row (adaptive)
        row_height = min(available_height / max(num_rows + num_sections * 2, 1), 50)
        row_height = max(row_height, 22)  # minimum

        # Adaptive font size based on row height
        if row_height >= 40:
            font_size = 14
            title_font_size = 13
            field_width = 120
        elif row_height >= 32:
            font_size = 12
            title_font_size = 12
            field_width = 110
        else:
            font_size = 10
            title_font_size = 11
            field_width = 90

        section_gap = row_height * 0.6

        y = y_after_header

        # === AFFLUENZA ===
        y = _draw_section_title(c, y, "DATI AFFLUENZA (comuni a tutte le schede)", title_font_size)
        y -= section_gap

        _draw_paired_row(c, y, "Elettori M", "Elettori F", font_size, field_width)
        y -= row_height

        _draw_paired_row(c, y, "Votanti M", "Votanti F", font_size, field_width)
        y -= row_height + section_gap

        # Minimum y before we need a new page
        min_y = MARGIN_BOTTOM + FOOTER_HEIGHT + 10

        # Space needed for one scheda section (5 rows + title + gaps)
        scheda_height = row_height * 5 + section_gap * 2 + 20

        # === PER-SCHEDA SECTIONS ===
        for scheda in schede:
            # Check if we need a new page
            if y - scheda_height < min_y:
                _draw_footer(c)
                c.showPage()
                total_pages += 1
                y = _draw_header(
                    c, consultazione_nome=consultazione.nome,
                    sezione_info=sezione, page_num=total_pages,
                    total_pages=total_pages, logo_path=logo_path,
                )

            color_label = f" ({scheda.get('colore', '')})" if scheda.get('colore') else ""
            y = _draw_section_title(c, y, f"SCHEDA: {scheda['nome']}{color_label}", title_font_size)
            y -= section_gap

            # Group 1: Schede ricevute / autenticate
            _draw_paired_row(c, y, "Schede ricevute", "Schede autenticate", font_size, field_width)
            y -= row_height

            # Group 2: Votes
            tipo = (scheda.get('schema_voti') or {}).get('tipo', '')

            if tipo == 'si_no':
                _draw_paired_row(c, y, "Voti SI", "Voti NO", font_size, field_width)
                y -= row_height
            elif tipo in ('liste_candidati', 'liste_preferenze'):
                c.setFillColor(COLOR_LABEL)
                list_font = max(font_size - 2, 8)
                c.setFont("Helvetica-Oblique", list_font)
                c.drawString(MARGIN_LEFT + 6, y, "Voti per lista (nome lista e voti):")
                y -= row_height * 0.7
                list_row_h = min(row_height * 0.8, 22)
                for _ in range(8):
                    c.setStrokeColor(COLOR_UNDERLINE)
                    c.setLineWidth(0.4)
                    c.line(MARGIN_LEFT + 6, y - 2, MARGIN_LEFT + 220, y - 2)
                    c.line(MARGIN_LEFT + 240, y - 2, MARGIN_LEFT + 340, y - 2)
                    y -= list_row_h
            else:
                _draw_single_row(c, y, "Voti validi totali", font_size, field_width)
                y -= row_height

            # Group 3: Bianche, nulle, contestate
            _draw_paired_row(c, y, "Schede bianche", "Schede nulle", font_size, field_width)
            y -= row_height

            _draw_single_row(c, y, "Schede contestate", font_size, field_width)
            y -= row_height + section_gap

        # === NOTES ===
        # Need at least ~80pt for notes section
        notes_min_space = 80
        if y - notes_min_space < min_y:
            _draw_footer(c)
            c.showPage()
            total_pages += 1
            y = _draw_header(
                c, consultazione_nome=consultazione.nome,
                sezione_info=sezione, page_num=total_pages,
                total_pages=total_pages, logo_path=logo_path,
            )

        c.setFillColor(COLOR_LABEL)
        c.setFont("Helvetica-Bold", max(font_size - 2, 9))
        c.drawString(MARGIN_LEFT, y, "NOTE E CONTESTAZIONI:")
        y -= 12
        c.setStrokeColor(COLOR_GRID)
        c.setLineWidth(0.4)
        # Fill remaining space with note lines
        notes_line_spacing = min(row_height * 0.8, 20)
        notes_line_spacing = max(notes_line_spacing, 14)
        while y > min_y + 10:
            c.line(MARGIN_LEFT, y, PAGE_W - MARGIN_RIGHT, y)
            y -= notes_line_spacing

        # Footer
        _draw_footer(c)

        # New page for next section
        if page_idx < len(sezioni_with_schede) - 1:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
