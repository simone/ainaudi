"""
PDF Generator per documenti con template e dati dinamici.

Supporta:
- Campi semplici (type='text') con coordinate assolute in area.x/area.y
- Loop su array (type='loop') con loop_fields a coordinate relative
- Multi-pagina intelligente con loop_pages per continuazione su pagine successive
"""
import io
import re
import logging
from datetime import date, datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from jsonpath_ng import parse as jsonpath_parse

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Genera PDF da template + dati usando field_mappings."""

    def __init__(self, template_file, data):
        self.template_file = template_file
        self.data = data
        self.reader = PdfReader(template_file)
        self.page_size = A4  # Default (595.28 x 841.89)

        # Leggi dimensione reale dalla prima pagina del template
        first_page = self.reader.pages[0]
        mb = first_page.mediabox
        self.template_width = float(mb.width)
        self.template_height = float(mb.height)
        logger.info(
            f"[PDFGenerator] Template: {len(self.reader.pages)} pagine, "
            f"size={self.template_width:.1f}x{self.template_height:.1f}"
        )

    def generate_from_template(self, template_obj):
        """Genera PDF usando un oggetto Template (con field_mappings)."""
        field_mappings = template_obj.field_mappings or []

        logger.info(
            f"[PDFGenerator] Template id={template_obj.id}, "
            f"nome={getattr(template_obj, 'name', '?')}, "
            f"{len(field_mappings)} field_mappings"
        )

        # Separa per tipo
        text_fields = []
        loop_field = None

        for mapping in field_mappings:
            mtype = mapping.get('type', 'text')
            if mtype == 'loop':
                loop_field = mapping
            else:
                text_fields.append(mapping)

        logger.info(f"[PDFGenerator] text_fields={len(text_fields)}, has_loop={loop_field is not None}")

        if not loop_field:
            return self._generate_simple(text_fields)

        return self._generate_with_loop(text_fields, loop_field)

    def _generate_simple(self, text_fields):
        """Genera PDF senza loop (singola pagina)."""
        writer = PdfWriter()
        template_page = self.reader.pages[0]

        overlay = self._render_text_fields(text_fields, target_page=0)
        template_page.merge_page(overlay)
        writer.add_page(template_page)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output

    def _generate_with_loop(self, text_fields, loop_mapping):
        """Genera PDF con loop multi-pagina."""
        writer = PdfWriter()

        # Estrai dati array dal loop
        array_path = loop_mapping.get('jsonpath', '')
        loop_items = self._resolve_array(array_path)
        loop_fields = loop_mapping.get('loop_fields', [])

        logger.info(
            f"[PDFGenerator] Loop: jsonpath={array_path}, "
            f"{len(loop_items)} items, {len(loop_fields)} columns"
        )

        if not loop_items or not loop_fields:
            # Nessun dato loop, genera solo campi semplici
            return self._generate_simple(text_fields)

        # Pagina principale del loop
        main_area = loop_mapping.get('area', {})
        main_page_num = loop_mapping.get('page', 0)
        main_rows = loop_mapping.get('rows', 6)
        row_height = main_area.get('height', 20)

        # Costruisci lista di "pagine loop" (principale + continuazioni)
        loop_pages = [
            {
                'page': main_page_num,
                'area': main_area,
                'rows': main_rows,
            }
        ]
        for lp in loop_mapping.get('loop_pages', []):
            loop_pages.append({
                'page': lp.get('page', 0),
                'area': lp.get('area', main_area),
                'rows': lp.get('rows', main_rows),
            })

        # Distribuisci items tra le pagine
        item_offset = 0
        pages_generated = set()

        for lp_idx, lp in enumerate(loop_pages):
            if item_offset >= len(loop_items):
                break

            page_num = lp['page']
            area = lp['area']
            rows = lp['rows']
            items_for_page = loop_items[item_offset:item_offset + rows]

            logger.info(
                f"[PDFGenerator] Pagina {page_num} ({lp_idx}): "
                f"area={area}, rows={rows}, items={len(items_for_page)} "
                f"(offset {item_offset})"
            )

            # Crea overlay per questa pagina
            overlay = self._render_page(
                text_fields=text_fields if page_num not in pages_generated else [],
                loop_fields=loop_fields,
                loop_items=items_for_page,
                loop_area=area,
                target_page=page_num,
            )

            # Merge su template page
            template_page_idx = min(page_num, len(self.reader.pages) - 1)
            template_page = self.reader.pages[template_page_idx]
            template_page.merge_page(overlay)
            writer.add_page(template_page)

            pages_generated.add(page_num)
            item_offset += rows

        # Se ci sono ancora items, ripeti l'ultima pagina loop
        if item_offset < len(loop_items):
            last_lp = loop_pages[-1]
            while item_offset < len(loop_items):
                rows = last_lp['rows']
                area = last_lp['area']
                page_num = last_lp['page']
                items_for_page = loop_items[item_offset:item_offset + rows]

                logger.info(
                    f"[PDFGenerator] Pagina extra (overflow): "
                    f"items={len(items_for_page)} (offset {item_offset})"
                )

                overlay = self._render_page(
                    text_fields=[],
                    loop_fields=loop_fields,
                    loop_items=items_for_page,
                    loop_area=area,
                    target_page=page_num,
                )

                template_page_idx = min(page_num, len(self.reader.pages) - 1)
                template_page = self.reader.pages[template_page_idx]
                template_page.merge_page(overlay)
                writer.add_page(template_page)

                item_offset += rows

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output

    def _render_page(self, text_fields, loop_fields, loop_items, loop_area, target_page):
        """Renderizza una pagina con campi testo + loop items. Ritorna PdfReader overlay."""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(self.template_width, self.template_height))
        page_height = self.template_height

        # 1. Renderizza campi testo semplici
        for mapping in text_fields:
            if mapping.get('page', 0) != target_page:
                continue

            area = mapping.get('area', {})
            text = self._evaluate_expression(mapping.get('jsonpath', ''), self.data)
            x = area.get('x', 0)
            editor_y = area.get('y', 0)
            field_height = area.get('height', 12)
            font_size = max(6, field_height * 0.85)

            # Converti da editor (top-left, Y cresce in basso) a PDF (bottom-left, Y cresce in alto)
            pdf_y = page_height - editor_y - field_height

            logger.info(
                f"[PDFGenerator] TEXT '{text}' at x={x}, pdf_y={pdf_y:.1f} "
                f"(editor_y={editor_y}, h={field_height}, font={font_size:.1f})"
            )

            can.setFont("Helvetica", font_size)
            can.drawString(x, pdf_y, str(text))

        # 2. Renderizza loop items
        loop_x = loop_area.get('x', 0)
        loop_y = loop_area.get('y', 0)
        row_height = loop_area.get('height', 20)

        for idx, item in enumerate(loop_items):
            for lf in loop_fields:
                text = self._evaluate_expression(lf.get('jsonpath', ''), item)
                rel_x = lf.get('x', 0)
                rel_y = lf.get('y', 0)
                field_height = lf.get('height', 12)
                font_size = max(6, field_height * 0.85)

                # Posizione assoluta: loop_origin + campo relativo + riga * altezza_riga
                abs_x = loop_x + rel_x
                editor_abs_y = loop_y + rel_y + (idx * row_height)

                # Converti a coordinate PDF
                pdf_y = page_height - editor_abs_y - field_height

                logger.info(
                    f"[PDFGenerator] LOOP[{idx}] '{text}' at x={abs_x}, pdf_y={pdf_y:.1f} "
                    f"(loop={loop_x},{loop_y} rel={rel_x},{rel_y} row_h={row_height} "
                    f"font={font_size:.1f})"
                )

                can.setFont("Helvetica", font_size)
                can.drawString(abs_x, pdf_y, str(text))

        can.showPage()
        can.save()
        packet.seek(0)
        return PdfReader(packet).pages[0]

    def _render_text_fields(self, text_fields, target_page):
        """Renderizza solo campi testo (no loop). Ritorna PdfReader page overlay."""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(self.template_width, self.template_height))
        page_height = self.template_height

        for mapping in text_fields:
            if mapping.get('page', 0) != target_page:
                continue

            area = mapping.get('area', {})
            text = self._evaluate_expression(mapping.get('jsonpath', ''), self.data)
            x = area.get('x', 0)
            editor_y = area.get('y', 0)
            field_height = area.get('height', 12)
            font_size = max(6, field_height * 0.85)

            pdf_y = page_height - editor_y - field_height

            logger.info(
                f"[PDFGenerator] TEXT '{text}' at x={x}, pdf_y={pdf_y:.1f} "
                f"(editor_y={editor_y}, h={field_height}, font={font_size:.1f})"
            )

            can.setFont("Helvetica", font_size)
            can.drawString(x, pdf_y, str(text))

        can.showPage()
        can.save()
        packet.seek(0)
        return PdfReader(packet).pages[0]

    def _resolve_array(self, jsonpath_str):
        """Risolvi un JSONPath che punta a un array e ritorna la lista di items."""
        if not jsonpath_str:
            return []
        try:
            expr = jsonpath_parse(jsonpath_str)
            matches = expr.find(self.data)
            if matches and isinstance(matches[0].value, list):
                return matches[0].value
        except Exception as e:
            logger.warning(f"[PDFGenerator] Errore resolve array '{jsonpath_str}': {e}")
        return []

    def _evaluate_expression(self, expression, data):
        """
        Valuta espressione JSONPath con supporto per concatenazioni.

        Supporta (SICURO - no eval):
        - $.delegato.nome
        - $.delegato.nome + ' ' + $.delegato.cognome
        """
        if not expression:
            return ''

        # Pattern per trovare tutti i $.path
        pattern = r'\$\.([a-zA-Z_][a-zA-Z0-9_.\[\]]*)'

        # Trova tutti i JSONPath e i loro valori
        jsonpath_values = {}
        for match in re.finditer(pattern, expression):
            path = match.group(0)
            try:
                expr = jsonpath_parse(path)
                matches = expr.find(data)
                if matches:
                    value = matches[0].value
                    if isinstance(value, (date, datetime)):
                        jsonpath_values[path] = value.strftime('%d/%m/%Y')
                    elif value is None:
                        jsonpath_values[path] = ''
                    elif isinstance(value, str) and len(value) == 10 and value[4] == '-' and value[7] == '-':
                        try:
                            parsed_date = datetime.strptime(value, '%Y-%m-%d')
                            jsonpath_values[path] = parsed_date.strftime('%d/%m/%Y')
                        except ValueError:
                            jsonpath_values[path] = str(value)
                    else:
                        jsonpath_values[path] = str(value)
                else:
                    jsonpath_values[path] = ''
            except:
                jsonpath_values[path] = ''

        # Se contiene solo un JSONPath senza operazioni, ritorna direttamente
        if len(jsonpath_values) == 1 and '+' not in expression:
            return list(jsonpath_values.values())[0]

        # Se contiene concatenazioni (+), valutale manualmente (SICURO)
        if '+' in expression:
            result = expression
            for path, value in jsonpath_values.items():
                result = result.replace(path, f'"{value}"')

            parts = []
            current = ''
            in_string = False
            for char in result:
                if char == '"':
                    if in_string:
                        parts.append(current)
                        current = ''
                    in_string = not in_string
                elif char == '+' and not in_string:
                    continue
                elif char == "'" and not in_string:
                    continue
                elif in_string:
                    current += char

            return ''.join(parts)

        # Fallback
        return list(jsonpath_values.values())[0] if jsonpath_values else ''


def generate_pdf(template_obj, data):
    """Helper per generare PDF."""
    generator = PDFGenerator(template_obj.template_file, data)
    return generator.generate_from_template(template_obj)
