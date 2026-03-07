"""
Badge generator for RDL credentials.
Generates business cards and lockscreen wallpapers with M5S branding.
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import io

# Dimensioni
CARD_WIDTH = 1004
CARD_HEIGHT = 638
LOCKSCREEN_WIDTH = 1080
LOCKSCREEN_HEIGHT = 2340

# Colori M5S
BLUE_DARK = (44, 78, 107)
RED = (220, 38, 57)
WHITE = (255, 255, 255)
YELLOW = (255, 205, 0)
BLACK = (0, 0, 0)


def format_name(name):
    """
    Formatta il nome in Title Case (prima lettera di ogni parola maiuscola).
    Gestisce anche nomi doppi, prefissi (De, Di, Von, etc.)

    Args:
        name: Nome grezzo (es. "MARIO ROSSI", "mario rossi", "MaRiO rOsSi")

    Returns:
        Nome formattato (es. "Mario Rossi")
    """
    if not name:
        return name

    # Split per spazi
    words = name.split()
    formatted_words = []

    for word in words:
        # Converti in lowercase e poi capitalizza
        formatted = word.lower().capitalize()
        formatted_words.append(formatted)

    return ' '.join(formatted_words)


def format_name_two_lines(name):
    """
    Formatta il nome su 2 righe: nome sulla prima, cognome sulla seconda.

    Args:
        name: Nome completo (es. "Mario Rossi", "Maria De Santis")

    Returns:
        Tupla (nome, cognome) - es. ("Mario", "Rossi") o ("Maria", "De Santis")
    """
    if not name:
        return ("", "")

    # Formatta in Title Case
    formatted = format_name(name)
    parts = formatted.split()

    if len(parts) == 1:
        # Solo cognome o solo nome
        return (parts[0], "")
    elif len(parts) == 2:
        # Nome Cognome (caso standard)
        return (parts[0], parts[1])
    else:
        # Nome composto o cognome composto (es. "Maria De Santis")
        # Assumiamo prima parola = nome, resto = cognome
        return (parts[0], ' '.join(parts[1:]))


def calculate_text_width(text, font):
    """Calcola la larghezza del testo."""
    from PIL import Image, ImageDraw
    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def get_responsive_font_size(text, base_size, max_width, bold=True, min_size=40):
    """
    Calcola il font size ottimale per far stare il testo nella larghezza massima.
    
    Args:
        text: Testo da misurare
        base_size: Font size iniziale desiderato
        max_width: Larghezza massima disponibile
        bold: Se usare font bold
        min_size: Font size minimo accettabile
        
    Returns:
        Font size ottimale
    """
    font_size = base_size
    
    while font_size >= min_size:
        font = get_font(font_size, bold=bold)
        text_width = calculate_text_width(text, font)
        
        if text_width <= max_width:
            return font_size
        
        # Riduci del 10%
        font_size = int(font_size * 0.9)
    
    return min_size


def split_name_smart(name, max_chars=15):
    """
    Divide il nome intelligentemente in più righe.
    
    Args:
        name: Nome completo
        max_chars: Numero massimo di caratteri per riga
        
    Returns:
        Lista di righe
    """
    # Se il nome è corto, restituisci una riga
    if len(name) <= max_chars:
        return [name]
    
    # Prova a dividere su spazio
    parts = name.split()
    if len(parts) == 2:
        # Nome e cognome - due righe
        return parts
    elif len(parts) > 2:
        # Nome composto - dividi intelligentemente
        mid = len(parts) // 2
        line1 = ' '.join(parts[:mid])
        line2 = ' '.join(parts[mid:])
        return [line1, line2]
    else:
        # Nessuno spazio - dividi a metà
        mid = len(name) // 2
        return [name[:mid], name[mid:]]


def draw_text_responsive(draw, text, x, y, max_width, base_font_size, fill, bold=True, 
                        align='left', line_spacing=1.2, max_lines=2):
    """
    Disegna testo con font size responsive e gestione multi-linea automatica.
    
    Args:
        draw: ImageDraw object
        text: Testo da disegnare
        x, y: Coordinate di partenza
        max_width: Larghezza massima
        base_font_size: Font size desiderato
        fill: Colore del testo
        bold: Se usare font bold
        align: Allineamento ('left', 'center')
        line_spacing: Spaziatura tra righe (moltiplicatore)
        max_lines: Numero massimo di righe
        
    Returns:
        Altezza totale occupata dal testo
    """
    # Prova con font size ottimale per una riga
    optimal_font_size = get_responsive_font_size(text, base_font_size, max_width, bold=bold)
    font = get_font(optimal_font_size, bold=bold)
    text_width = calculate_text_width(text, font)
    
    # Se sta in una riga, disegna
    if text_width <= max_width:
        if align == 'center':
            x = x + (max_width - text_width) // 2
        draw.text((x, y), text, fill=fill, font=font)
        return optimal_font_size
    
    # Altrimenti dividi su più righe
    lines = split_name_smart(text, max_chars=15)
    
    # Limita il numero di righe
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] += '...'
    
    # Ricalcola font size per la riga più lunga
    longest_line = max(lines, key=len)
    optimal_font_size = get_responsive_font_size(longest_line, base_font_size, max_width, bold=bold)
    font = get_font(optimal_font_size, bold=bold)
    
    # Disegna ogni riga
    current_y = y
    line_height = int(optimal_font_size * line_spacing)
    
    for line in lines:
        line_width = calculate_text_width(line, font)
        line_x = x
        if align == 'center':
            line_x = x + (max_width - line_width) // 2
        
        draw.text((line_x, current_y), line, fill=fill, font=font)
        current_y += line_height
    
    return current_y - y


def get_font(size, bold=False):
    """Ottiene un font di sistema."""
    # Percorso ai font del progetto
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(current_dir, "fonts")

    # Lista percorsi possibili per i font
    font_paths = [
        # Font del progetto (inclusi nel repo)
        (os.path.join(fonts_dir, "Arial-Bold.ttf"), os.path.join(fonts_dir, "Arial.ttf")),
        # Font di sistema macOS
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"),
        # Font di sistema Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]

    for bold_path, regular_path in font_paths:
        try:
            font_path = bold_path if bold else regular_path
            return ImageFont.truetype(font_path, size)
        except:
            continue

    # Fallback (dovrebbe mai succedere)
    print(f"⚠️ Nessun font trovato! Usando default (size ignorato)")
    return ImageFont.load_default()


def load_logo():
    """Carica il logo M5S."""
    # Percorso assoluto dal file corrente al logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # Cerca il logo in diverse posizioni possibili
    possible_paths = [
        os.path.join(current_dir, "assets", "logo-m5s.png"),  # resources/assets/
        os.path.join(project_root, "src", "assets", "logo-m5s.png"),
        os.path.join(project_root, "public", "assets", "logo-m5s.png"),
        os.path.join(project_root, "build", "assets", "logo-m5s.png"),
        "/app/resources/assets/logo-m5s.png",  # Docker
        "/app/src/assets/logo-m5s.png",  # Docker (frontend)
    ]

    for logo_path in possible_paths:
        if os.path.exists(logo_path):
            print(f"✓ Logo M5S trovato: {logo_path}")
            return Image.open(logo_path)

    print(f"✗ Logo M5S NON trovato. Percorsi cercati: {possible_paths}")
    return None


# =============================================================================
# BUSINESS CARDS - 10 Modern Variants
# =============================================================================

def generate_card_variant_1(name="Nome Cognome"):
    """Hero Layout - Logo gigante al centro."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BLUE_DARK)
    draw = ImageDraw.Draw(img)

    # Logo gigante al centro (ridotto per evitare sovrapposizione)
    logo = load_logo()
    if logo:
        logo_size = 320
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = CARD_WIDTH - logo_size - 40
        logo_y = (CARD_HEIGHT - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome grande a sinistra (RESPONSIVE)
    max_width_name = CARD_WIDTH - 460  # Spazio per logo
    draw_text_responsive(
        draw, name, 
        x=60, 
        y=CARD_HEIGHT // 2 - 80, 
        max_width=max_width_name,
        base_font_size=120,
        fill=WHITE,
        bold=True,
        align='left',
        max_lines=2
    )

    # Sottotitolo
    font_title = get_font(50, bold=False)
    draw.text((60, CARD_HEIGHT // 2 + 60), "Rappresentante di Lista", fill=YELLOW, font=font_title)

    return img


def generate_card_variant_2(name="Nome Cognome"):
    """Clean Layout - Design pulito e moderno."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Barra gialla in alto
    bar_height = 180
    draw.rectangle([0, 0, CARD_WIDTH, bar_height], fill=YELLOW)

    # Logo nella barra gialla
    logo = load_logo()
    if logo:
        logo_size = 140
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = CARD_WIDTH - logo_size - 30
        logo_y = (bar_height - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # "Movimento 5 Stelle" in piccolo nella barra
    font_small = get_font(28, bold=True)
    draw.text((60, bar_height//2 - 14), "MOVIMENTO 5 STELLE", fill=BLUE_DARK, font=font_small)

    # Nome grande (RESPONSIVE)
    draw_text_responsive(draw, name, x=60, y=bar_height + 100, max_width=CARD_WIDTH-120, base_font_size=130, fill=BLUE_DARK, bold=True, max_lines=2)

    # Sottotitolo
    font_title = get_font(52, bold=False)
    draw.text((60, CARD_HEIGHT - 120), "Rappresentante di Lista", fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_3(name="Nome Cognome"):
    """Center Stage - Logo in alto, nome centrato gigante."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Header blu
    header_h = 220
    draw.rectangle([0, 0, CARD_WIDTH, header_h], fill=BLUE_DARK)

    # Logo nel header
    logo = load_logo()
    if logo:
        logo_size = 180
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = (header_h - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome gigante centrato (RESPONSIVE)
    draw_text_responsive(draw, name, x=100, y=header_h + 80, max_width=CARD_WIDTH-200, base_font_size=140, fill=BLUE_DARK, bold=True, align='center', max_lines=2)

    # Barra gialla sotto
    bar_y = header_h + 250
    draw.rectangle([100, bar_y, CARD_WIDTH - 100, bar_y + 12], fill=YELLOW)

    # Sottotitolo
    font_title = get_font(46, bold=False)
    text = "Rappresentante di Lista"
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (CARD_WIDTH - text_width) // 2
    draw.text((text_x, bar_y + 40), text, fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_4(name="Nome Cognome"):
    """Bold Contrast - Blu su giallo, alto contrasto."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), YELLOW)
    draw = ImageDraw.Draw(img)

    # Margini generosi
    margin = 60

    # Logo centrato in alto
    logo = load_logo()
    logo_bottom_y = 0
    if logo:
        logo_size = 200
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = margin
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)
        logo_bottom_y = logo_y + logo_size

    # Spazio di mezzo carattere (0.5em ≈ 70px con font 140)
    spacing = 70

    # Nome gigante centrato - più in basso (RESPONSIVE)
    name_y = logo_bottom_y + spacing
    draw_text_responsive(draw, name, x=margin, y=name_y, max_width=CARD_WIDTH-margin*2, base_font_size=140, fill=BLUE_DARK, bold=True, align='center', max_lines=2)

    # Linea blu sotto il nome
    line_y = name_y + 180
    draw.rectangle([150, line_y, CARD_WIDTH - 150, line_y + 8], fill=BLUE_DARK)

    # Sottotitolo
    font_title = get_font(48, bold=True)
    text = "RAPPRESENTANTE DI LISTA"
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (CARD_WIDTH - text_width) // 2
    draw.text((text_x, line_y + 40), text, fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_5(name="Nome Cognome"):
    """Frame Design - Stile tessera ufficiale."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), YELLOW)
    draw = ImageDraw.Draw(img)

    # Doppia cornice
    margin1 = 20
    margin2 = 35
    draw.rectangle([margin1, margin1, CARD_WIDTH - margin1, CARD_HEIGHT - margin1], fill=BLUE_DARK)
    draw.rectangle([margin2, margin2, CARD_WIDTH - margin2, CARD_HEIGHT - margin2], fill=WHITE)

    # Logo in alto
    logo = load_logo()
    if logo:
        logo_size = 220
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = margin2 + 30
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome al centro (RESPONSIVE)
    draw_text_responsive(draw, name, x=margin2+50, y=CARD_HEIGHT//2+10, max_width=CARD_WIDTH-margin2*2-100, base_font_size=130, fill=BLUE_DARK, bold=True, align='center', max_lines=2)

    # Sottotitolo
    font_title = get_font(44, bold=True)
    text = "RAPPRESENTANTE DI LISTA"
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (CARD_WIDTH - text_width) // 2
    draw.text((text_x, CARD_HEIGHT - margin2 - 80), text, fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_6(name="Nome Cognome"):
    """Side Logo - Logo laterale con nome prominente."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BLUE_DARK)
    draw = ImageDraw.Draw(img)

    # Pannello giallo a destra
    panel_w = 320
    draw.rectangle([CARD_WIDTH - panel_w, 0, CARD_WIDTH, CARD_HEIGHT], fill=YELLOW)

    # Logo nel pannello giallo
    logo = load_logo()
    if logo:
        logo_size = 260
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = CARD_WIDTH - panel_w + (panel_w - logo_size) // 2
        logo_y = (CARD_HEIGHT - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome grande a sinistra (RESPONSIVE)
    draw_text_responsive(draw, name, x=60, y=CARD_HEIGHT//2-80, max_width=CARD_WIDTH-panel_w-120, base_font_size=130, fill=WHITE, bold=True, max_lines=2)

    # Sottotitolo
    font_title = get_font(48, bold=False)
    draw.text((60, CARD_HEIGHT // 2 + 80), "Rappresentante di Lista", fill=YELLOW, font=font_title)

    return img


def generate_card_variant_7(name="Nome Cognome"):
    """Minimal White - Minimalista su bianco."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Barra gialla spessa a sinistra
    draw.rectangle([0, 0, 40, CARD_HEIGHT], fill=YELLOW)

    # Logo in alto
    logo = load_logo()
    logo_bottom_y = 0
    if logo:
        logo_size = 200
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = 80
        logo_y = 50
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)
        logo_bottom_y = logo_y + logo_size

    # Spazio di mezzo carattere (0.5em ≈ 70px)
    spacing = 70

    # Nome grande - più in basso (RESPONSIVE)
    name_y = logo_bottom_y + spacing
    draw_text_responsive(draw, name, x=80, y=name_y, max_width=CARD_WIDTH-160, base_font_size=140, fill=BLUE_DARK, bold=True, max_lines=2)

    # Linea gialla
    line_y = name_y + 180
    draw.rectangle([80, line_y, CARD_WIDTH - 80, line_y + 10], fill=YELLOW)

    # Sottotitolo
    font_title = get_font(52, bold=False)
    draw.text((80, line_y + 40), "Rappresentante di Lista", fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_8(name="Nome Cognome"):
    """Color Block - Blocchi di colore audaci."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BLUE_DARK)
    draw = ImageDraw.Draw(img)

    # Blocco giallo in alto
    top_h = 220
    draw.rectangle([0, 0, CARD_WIDTH, top_h], fill=YELLOW)

    # Blocco rosso in basso
    bottom_h = 140
    draw.rectangle([0, CARD_HEIGHT - bottom_h, CARD_WIDTH, CARD_HEIGHT], fill=RED)

    # Logo nel blocco giallo
    logo = load_logo()
    if logo:
        logo_size = 200
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = (top_h - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome nel blocco blu (RESPONSIVE)
    draw_text_responsive(draw, name, x=100, y=top_h+(CARD_HEIGHT-top_h-bottom_h-130)//2, max_width=CARD_WIDTH-200, base_font_size=130, fill=WHITE, bold=True, align='center', max_lines=2)

    # Sottotitolo nel blocco rosso
    font_title = get_font(52, bold=True)
    text = "Rappresentante di Lista"
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (CARD_WIDTH - text_width) // 2
    draw.text((text_x, CARD_HEIGHT - bottom_h + (bottom_h - 52) // 2), text, fill=WHITE, font=font_title)

    return img


def generate_card_variant_9(name="Nome Cognome"):
    """Blue Header - Header blu con logo."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Header blu (ottimo contrasto con logo)
    header_h = 200
    draw.rectangle([0, 0, CARD_WIDTH, header_h], fill=BLUE_DARK)

    # Logo nel header
    logo = load_logo()
    if logo:
        logo_size = 160
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = (header_h - logo_size) // 2
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome grande (RESPONSIVE)
    draw_text_responsive(draw, name, x=60, y=header_h + 100, max_width=CARD_WIDTH-120, base_font_size=140, fill=BLUE_DARK, bold=True, max_lines=2)

    # Barra gialla
    bar_y = header_h + 280
    draw.rectangle([60, bar_y, CARD_WIDTH - 60, bar_y + 10], fill=YELLOW)

    # Sottotitolo
    font_title = get_font(52, bold=False)
    draw.text((60, bar_y + 40), "Rappresentante di Lista", fill=BLUE_DARK, font=font_title)

    return img


def generate_card_variant_10(name="Nome Cognome"):
    """Centered Badge - Badge centrale pulito."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BLUE_DARK)
    draw = ImageDraw.Draw(img)

    # Logo grande centrato
    logo = load_logo()
    if logo:
        logo_size = 240
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (CARD_WIDTH - logo_size) // 2
        logo_y = 80
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome gigante centrato (RESPONSIVE)
    draw_text_responsive(draw, name, x=80, y=360, max_width=CARD_WIDTH-160, base_font_size=140, fill=WHITE, bold=True, align='center', max_lines=2)

    # Barra gialla
    bar_y = 500
    draw.rectangle([100, bar_y, CARD_WIDTH - 100, bar_y + 8], fill=YELLOW)

    # Sottotitolo
    font_title = get_font(48, bold=True)
    text = "RAPPRESENTANTE DI LISTA"
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (CARD_WIDTH - text_width) // 2
    draw.text((text_x, bar_y + 40), text, fill=YELLOW, font=font_title)

    return img


def generate_card_variant_11(name="Nome Cognome"):
    """
    Variant 11 rebuilt from the uploaded curve artwork.

    Geometry:
    - yellow uses its own top and bottom curves
    - white is the gap between yellow_bottom and orange_top
    - orange fills everything below orange_top

    The three curves below were sampled from the uploaded PDF artwork
    after rendering the page at high resolution.
    """

    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Colors tuned to match the badge
    ORANGE = (244, 166, 0)
    YELLOW = (248, 205, 0)
    GAP_WHITE = (250, 250, 250)

    # ------------------------------------------------------------------
    # Sampled curves from the uploaded PDF artwork.
    #
    # Each tuple is:
    # (t, yellow_top_y, yellow_bottom_y, orange_top_y)
    #
    # t is normalized in [0, 1] along the horizontal development
    # of the original artwork after trimming the straight end-cap.
    # Y values are normalized against the 2000 px render height.
    # ------------------------------------------------------------------
    anchors = [
        (0.000000, 0.4870, 0.4870, 0.4910),
        (0.062588, 0.4925, 0.4995, 0.5035),
        (0.125176, 0.4930, 0.5065, 0.5105),
        (0.187764, 0.4890, 0.5090, 0.5130),
        (0.250352, 0.4810, 0.5080, 0.5120),
        (0.312940, 0.4690, 0.5030, 0.5075),
        (0.374824, 0.4540, 0.4955, 0.5000),
        (0.437412, 0.4360, 0.4850, 0.4895),
        (0.500000, 0.4145, 0.4720, 0.4765),
        (0.562588, 0.3900, 0.4565, 0.4605),
        (0.625176, 0.3620, 0.4380, 0.4425),
        (0.687060, 0.3320, 0.4180, 0.4225),
        (0.749648, 0.2985, 0.3955, 0.4000),
        (0.812236, 0.2620, 0.3705, 0.3755),
        (0.874824, 0.2230, 0.3440, 0.3485),
        (0.937412, 0.1810, 0.3150, 0.3200),
        (1.000000, 0.1365, 0.2845, 0.2895),
    ]

    t_anchor = np.array([a[0] for a in anchors], dtype=float)
    y_yellow_top_anchor = np.array([a[1] for a in anchors], dtype=float)
    y_yellow_bottom_anchor = np.array([a[2] for a in anchors], dtype=float)
    y_orange_top_anchor = np.array([a[3] for a in anchors], dtype=float)

    # ------------------------------------------------------------------
    # Curve placement inside the final badge
    # ------------------------------------------------------------------
    x_start_norm = -0.08
    x_end_norm = 1.00
    y_left_norm = 0.72
    y_scale = 1.23

    yellow_top_bias = 0.000
    yellow_bottom_bias = 0.010
    orange_top_bias = 0.022

    def build_curve(y_values_norm, y_bias=0.0, samples=500):
        """
        Build a curve by interpolating sampled anchor points.
        """
        xs_norm = np.linspace(x_start_norm, x_end_norm, samples)
        t = np.clip((xs_norm - x_start_norm) / (x_end_norm - x_start_norm), 0.0, 1.0)

        y_interp = np.interp(t, t_anchor, y_values_norm)

        # Use the first yellow-top value as reference origin for vertical remap
        y0 = y_yellow_top_anchor[0]

        points = []
        for x_n, y_n in zip(xs_norm, y_interp):
            x = x_n * CARD_WIDTH
            y = (y_left_norm + (y_n - y0) * y_scale + y_bias) * CARD_HEIGHT
            points.append((x, y))

        return points

    yellow_top = build_curve(y_yellow_top_anchor, yellow_top_bias)
    yellow_bottom = build_curve(y_yellow_bottom_anchor, yellow_bottom_bias)
    orange_top = build_curve(y_orange_top_anchor, orange_top_bias)

    # Draw yellow band
    draw.polygon(yellow_top + yellow_bottom[::-1], fill=YELLOW)

    # Draw white separator
    draw.polygon(yellow_bottom + orange_top[::-1], fill=GAP_WHITE)

    # Draw orange field
    orange_poly = orange_top + [(CARD_WIDTH, CARD_HEIGHT), (0, CARD_HEIGHT)]
    draw.polygon(orange_poly, fill=ORANGE)

    # ------------------------------------------------------------------
    # Logo
    # ------------------------------------------------------------------
    logo = load_logo()
    if logo:
        logo_size = 280
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = CARD_WIDTH - logo_size - 40
        logo_y = 30
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == "RGBA" else None)

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------
    formatted_name = format_name(name).upper()
    font_nome = get_font(70, bold=False)

    nome_x = 60
    nome_y = CARD_HEIGHT - 370

    draw.text(
        (nome_x, nome_y),
        formatted_name,
        fill=(30, 30, 30),
        font=font_nome
    )

    # ------------------------------------------------------------------
    # Red label
    # ------------------------------------------------------------------
    font_rdl = get_font(46, bold=True)
    text_rdl = "Rappresentante di lista"

    bbox = draw.textbbox((0, 0), text_rdl, font=font_rdl)
    text_width = bbox[2] - bbox[0]

    padding = 30
    banda_width = text_width + padding * 2
    banda_height = 64

    banda_x = 55
    banda_y = CARD_HEIGHT - 240

    draw.rounded_rectangle(
        [banda_x, banda_y, banda_x + banda_width, banda_y + banda_height],
        radius=10,
        fill=RED
    )

    draw.text(
        (banda_x + padding, banda_y + 12),
        text_rdl,
        fill=WHITE,
        font=font_rdl
    )

    return img


# =============================================================================
# LOCKSCREEN WALLPAPERS - 6 Variants
# =============================================================================

def generate_lockscreen_variant_1(name="Nome Cognome"):
    """Centro con logo grande."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), BLUE_DARK)
    draw = ImageDraw.Draw(img)

    # Logo gigante in alto
    logo = load_logo()
    if logo:
        logo_size = 600
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 250
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome e cognome su 2 righe - più padding dal logo
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(180, bold=True)
    font_cognome = get_font(180, bold=True)

    # Più spazio sotto il logo
    y_start = 1000

    # Nome (prima riga)
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=WHITE, font=font_nome)

    # Cognome (seconda riga) - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 210), cognome, fill=WHITE, font=font_cognome)

    # Barra gialla - più padding
    bar_y = y_start + 500
    draw.rectangle([150, bar_y, LOCKSCREEN_WIDTH - 150, bar_y + 15], fill=YELLOW)

    # "RDL" - più padding
    font_rdl = get_font(120, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, bar_y + 80), text, fill=YELLOW, font=font_rdl)

    return img


def generate_lockscreen_variant_2(name="Nome Cognome"):
    """Top branding, info centrate."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Header blu con logo
    header_height = 520
    draw.rectangle([0, 0, LOCKSCREEN_WIDTH, header_height], fill=BLUE_DARK)

    logo = load_logo()
    if logo:
        logo_size = 440
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 50
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome e cognome su 2 righe - più padding dall'header
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(180, bold=True)
    font_cognome = get_font(180, bold=True)

    y_start = header_height + 240

    # Nome
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=BLUE_DARK, font=font_nome)

    # Cognome - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 210), cognome, fill=BLUE_DARK, font=font_cognome)

    # Badge giallo con RDL - più padding
    badge_y = y_start + 500
    badge_height = 180
    draw.rectangle([80, badge_y, LOCKSCREEN_WIDTH - 80, badge_y + badge_height], fill=YELLOW)

    font_rdl = get_font(100, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, badge_y + 50), text, fill=BLUE_DARK, font=font_rdl)

    return img


def generate_lockscreen_variant_3(name="Nome Cognome"):
    """Minimalista elegante."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Logo grande in alto
    logo = load_logo()
    if logo:
        logo_size = 520
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 200
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome e cognome su 2 righe - più padding dal logo
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(190, bold=True)
    font_cognome = get_font(190, bold=True)

    y_start = 860

    # Nome
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=BLUE_DARK, font=font_nome)

    # Cognome - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 220), cognome, fill=BLUE_DARK, font=font_cognome)

    # Linea gialla - più padding
    line_y = y_start + 520
    draw.rectangle([200, line_y, LOCKSCREEN_WIDTH - 200, line_y + 20], fill=YELLOW)

    # RDL - più padding
    font_rdl = get_font(90, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, line_y + 80), text, fill=BLUE_DARK, font=font_rdl)

    return img


def generate_lockscreen_variant_4(name="Nome Cognome"):
    """Bold color blocks - Giallo dominante."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), YELLOW)
    draw = ImageDraw.Draw(img)

    # Logo gigante in alto (su sfondo giallo - ottimo contrasto)
    logo = load_logo()
    if logo:
        logo_size = 580
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 180
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome e cognome su 2 righe - più padding dal logo
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(180, bold=True)
    font_cognome = get_font(180, bold=True)

    y_start = 900

    # Nome
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=BLUE_DARK, font=font_nome)

    # Cognome - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 210), cognome, fill=BLUE_DARK, font=font_cognome)

    # Blocco blu in basso con RDL - più alto per più padding
    bottom_height = 340
    draw.rectangle([0, LOCKSCREEN_HEIGHT - bottom_height, LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT], fill=BLUE_DARK)

    font_rdl = get_font(120, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, LOCKSCREEN_HEIGHT - bottom_height + 120), text, fill=YELLOW, font=font_rdl)

    return img


def generate_lockscreen_variant_5(name="Nome Cognome"):
    """Yellow Bold - Giallo dominante ad alto contrasto."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), YELLOW)
    draw = ImageDraw.Draw(img)

    # Logo grande in alto (su giallo)
    logo = load_logo()
    if logo:
        logo_size = 540
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 200
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Pannello blu per nome/cognome - più padding dal logo
    panel_y = 880
    panel_h = 640
    draw.rectangle([0, panel_y, LOCKSCREEN_WIDTH, panel_y + panel_h], fill=BLUE_DARK)

    # Nome e cognome su 2 righe (nel pannello blu) - più padding interno
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(170, bold=True)
    font_cognome = get_font(170, bold=True)

    y_start = panel_y + 100

    # Nome
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=WHITE, font=font_nome)

    # Cognome - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 200), cognome, fill=WHITE, font=font_cognome)

    # RDL nel pannello blu - più padding
    font_rdl = get_font(110, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, y_start + 460), text, fill=YELLOW, font=font_rdl)

    return img


def generate_lockscreen_variant_6(name="Nome Cognome"):
    """Red Accent - Accento rosso con logo su bianco."""
    img = Image.new('RGB', (LOCKSCREEN_WIDTH, LOCKSCREEN_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Logo grande in alto (su bianco - massimo contrasto)
    logo = load_logo()
    if logo:
        logo_size = 580
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_x = (LOCKSCREEN_WIDTH - logo_size) // 2
        logo_y = 160
        img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)

    # Nome e cognome su 2 righe - più padding dal logo
    nome, cognome = format_name_two_lines(name)

    font_nome = get_font(180, bold=True)
    font_cognome = get_font(180, bold=True)

    y_start = 880

    # Nome
    bbox_nome = draw.textbbox((0, 0), nome, font=font_nome)
    nome_width = bbox_nome[2] - bbox_nome[0]
    nome_x = (LOCKSCREEN_WIDTH - nome_width) // 2
    draw.text((nome_x, y_start), nome, fill=BLUE_DARK, font=font_nome)

    # Cognome - più padding
    bbox_cognome = draw.textbbox((0, 0), cognome, font=font_cognome)
    cognome_width = bbox_cognome[2] - bbox_cognome[0]
    cognome_x = (LOCKSCREEN_WIDTH - cognome_width) // 2
    draw.text((cognome_x, y_start + 210), cognome, fill=BLUE_DARK, font=font_cognome)

    # Barra rossa - più padding
    bar_y = y_start + 500
    draw.rectangle([150, bar_y, LOCKSCREEN_WIDTH - 150, bar_y + 20], fill=RED)

    # RDL - più padding
    font_rdl = get_font(110, bold=True)
    text = "RDL"
    bbox = draw.textbbox((0, 0), text, font=font_rdl)
    text_width = bbox[2] - bbox[0]
    text_x = (LOCKSCREEN_WIDTH - text_width) // 2
    draw.text((text_x, bar_y + 80), text, fill=RED, font=font_rdl)

    return img


# =============================================================================
# REGISTRY & API
# =============================================================================

BADGE_REGISTRY = {
    # Business cards (1004x638)
    'card_1': {
        'name': 'Hero Layout',
        'description': 'Logo gigante al centro con nome a sinistra',
        'type': 'card',
        'generator': generate_card_variant_1,
    },
    'card_2': {
        'name': 'Split Layout',
        'description': 'Design split verticale blu/giallo',
        'type': 'card',
        'generator': generate_card_variant_2,
    },
    'card_3': {
        'name': 'Center Stage',
        'description': 'Logo in alto, nome centrato gigante',
        'type': 'card',
        'generator': generate_card_variant_3,
    },
    'card_4': {
        'name': 'Bold Typography',
        'description': 'Focus sul nome con cornice gialla',
        'type': 'card',
        'generator': generate_card_variant_4,
    },
    'card_5': {
        'name': 'Frame Design',
        'description': 'Stile tessera ufficiale con doppia cornice',
        'type': 'card',
        'generator': generate_card_variant_5,
    },
    'card_6': {
        'name': 'Asymmetric Bold',
        'description': 'Design asimmetrico moderno con triangolo',
        'type': 'card',
        'generator': generate_card_variant_6,
    },
    'card_7': {
        'name': 'Minimalist Pro',
        'description': 'Stile minimalista professionale',
        'type': 'card',
        'generator': generate_card_variant_7,
    },
    'card_8': {
        'name': 'Color Block',
        'description': 'Blocchi di colore audaci',
        'type': 'card',
        'generator': generate_card_variant_8,
    },
    'card_9': {
        'name': 'Gradient Style',
        'description': 'Gradiente moderno con logo watermark',
        'type': 'card',
        'generator': generate_card_variant_9,
    },
    'card_10': {
        'name': 'Badge Style',
        'description': 'Stile badge identificativo',
        'type': 'card',
        'generator': generate_card_variant_10,
    },
    'card_11': {
        'name': 'Vertical Triangle',
        'description': 'Design triangolo giallo con banda rossa verticale',
        'type': 'card',
        'generator': generate_card_variant_11,
    },

    # Lockscreen wallpapers (1080x2340)
    'lockscreen_1': {
        'name': 'Centro con logo grande',
        'description': 'Logo gigante centrato con nome sotto',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_1,
    },
    'lockscreen_2': {
        'name': 'Top branding',
        'description': 'Header blu con logo e badge giallo',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_2,
    },
    'lockscreen_3': {
        'name': 'Minimalista elegante',
        'description': 'Design pulito e professionale',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_3,
    },
    'lockscreen_4': {
        'name': 'Bold color blocks',
        'description': 'Blocchi di colore giallo/blu/rosso',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_4,
    },
    'lockscreen_5': {
        'name': 'Badge ufficiale',
        'description': 'Stile tessera con cornici',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_5,
    },
    'lockscreen_6': {
        'name': 'Gradiente moderno',
        'description': 'Sfondo gradiente con logo watermark',
        'type': 'lockscreen',
        'generator': generate_lockscreen_variant_6,
    },
}


def generate_badge(variant_id, name="Nome Cognome"):
    """
    Genera un badge RDL.

    Args:
        variant_id: ID variante (card_1, lockscreen_1, etc.)
        name: Nome completo dell'utente

    Returns:
        PIL Image object
    """
    if variant_id not in BADGE_REGISTRY:
        raise ValueError(f"Variante non trovata: {variant_id}")

    # Formatta il nome in Title Case
    formatted_name = format_name(name)

    generator = BADGE_REGISTRY[variant_id]['generator']
    return generator(formatted_name)


def generate_badge_to_bytes(variant_id, name="Nome Cognome", format='PNG'):
    """
    Genera un badge e restituisce i bytes.

    Args:
        variant_id: ID variante
        name: Nome completo
        format: Formato immagine (PNG, JPEG)

    Returns:
        BytesIO object contenente l'immagine
    """
    img = generate_badge(variant_id, name)

    # Converti in bytes
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=95, dpi=(300, 300))
    buffer.seek(0)

    return buffer


def get_available_variants():
    """Restituisce la lista delle varianti disponibili."""
    return {
        variant_id: {
            'id': variant_id,
            'name': info['name'],
            'description': info['description'],
            'type': info['type'],
        }
        for variant_id, info in BADGE_REGISTRY.items()
    }
