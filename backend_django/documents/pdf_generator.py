"""
PDF Generator per documenti con template e dati dinamici.

Supporta:
- Espressioni JSONPath complesse ($.delegato.nome + ' ' + $.delegato.cognome)
- Loop su array ($.designazioni[*].effettivo_cognome)
- Multi-pagina intelligente (prima, intermedie, ultima)
"""
import io
import re
from datetime import date, datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from jsonpath_ng import parse as jsonpath_parse


class PDFGenerator:
    """Genera PDF da template + dati usando field_mappings."""

    def __init__(self, template_file, data):
        """
        Args:
            template_file: FileField del template PDF
            data: Dict con dati da inserire (es. {'delegato': {...}, 'designazioni': [...]})
        """
        self.template_file = template_file
        self.data = data
        self.reader = PdfReader(template_file)
        self.page_size = A4  # Default

    def generate_from_template(self, template_obj):
        """
        Genera PDF usando un oggetto Template (con field_mappings).

        Args:
            template_obj: Oggetto Template Django con field_mappings JSONField

        Returns:
            BytesIO contenente il PDF generato
        """
        field_mappings = template_obj.field_mappings or []

        # Separa mappings per tipo
        simple_fields = []  # Campi semplici (non loop)
        loop_fields = []    # Campi dentro loop

        for mapping in field_mappings:
            jsonpath = mapping.get('jsonpath', '')
            if '[*]' in jsonpath:
                loop_fields.append(mapping)
            else:
                simple_fields.append(mapping)

        # Se non ci sono loop, genera singola pagina
        if not loop_fields:
            return self._generate_single_page(simple_fields)

        # Se ci sono loop, gestisci multi-pagina
        return self._generate_multipage(simple_fields, loop_fields)

    def _generate_single_page(self, field_mappings):
        """Genera PDF con singola pagina (no loop)."""
        writer = PdfWriter()

        # Carica prima pagina del template
        template_page = self.reader.pages[0]

        # Crea overlay con testo
        overlay = self._create_overlay(field_mappings, page_type='first')

        # Merge: overlay sopra template (non il contrario!)
        overlay_page = overlay.pages[0]
        overlay_page.merge_page(template_page)
        writer.add_page(overlay_page)

        # Scrivi output
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output

    def _generate_multipage(self, simple_fields, loop_fields):
        """
        Genera PDF multi-pagina con loop intelligente.

        Logica:
        1. Prima pagina (page=0): campi semplici + primi N elementi loop
        2. Pagine intermedie (page=2): elementi successivi del loop (se necessario)
        3. Ultima pagina (page=1): ultimi elementi loop + campi finali
        """
        writer = PdfWriter()

        # Determina quanti elementi loop abbiamo
        loop_items = self._get_loop_items(loop_fields)
        total_items = len(loop_items)

        # Calcola quanti item entrano per pagina
        items_per_page = self._calculate_items_per_page(loop_fields)

        # Determina struttura pagine
        if total_items <= items_per_page:
            # Tutti gli item stanno in prima pagina
            pages_needed = [('first', 0, total_items)]
        elif total_items <= items_per_page * 2:
            # Item distribuiti tra prima e ultima
            first_count = items_per_page
            last_count = total_items - first_count
            pages_needed = [
                ('first', 0, first_count),
                ('last', first_count, total_items)
            ]
        else:
            # Serve prima, intermedie, ultima
            first_count = items_per_page
            remaining = total_items - first_count
            last_count = remaining % items_per_page or items_per_page
            intermediate_count = remaining - last_count

            pages_needed = [('first', 0, first_count)]

            # Aggiungi pagine intermedie
            offset = first_count
            while offset < total_items - last_count:
                pages_needed.append(('intermediate', offset, offset + items_per_page))
                offset += items_per_page

            # Aggiungi ultima
            pages_needed.append(('last', total_items - last_count, total_items))

        # Genera ogni pagina
        for page_type, start_idx, end_idx in pages_needed:
            template_page = self._get_template_page(page_type)
            overlay = self._create_multipage_overlay(
                simple_fields,
                loop_fields,
                loop_items[start_idx:end_idx],
                page_type
            )
            # Merge: overlay sopra template (non il contrario!)
            overlay_page = overlay.pages[0]
            overlay_page.merge_page(template_page)
            writer.add_page(overlay_page)

        # Scrivi output
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output

    def _get_template_page(self, page_type):
        """
        Ottiene la pagina template corretta.

        Args:
            page_type: 'first', 'intermediate', 'last'

        Returns:
            PdfPage
        """
        page_map = {
            'first': 0,
            'intermediate': 2 if len(self.reader.pages) > 2 else 0,
            'last': 1 if len(self.reader.pages) > 1 else 0
        }
        page_idx = page_map.get(page_type, 0)
        if page_idx >= len(self.reader.pages):
            page_idx = 0
        return self.reader.pages[page_idx]

    def _create_overlay(self, field_mappings, page_type='first'):
        """
        Crea overlay PDF con testo renderizzato.

        Args:
            field_mappings: Lista di mapping da renderizzare
            page_type: Tipo pagina ('first', 'intermediate', 'last')

        Returns:
            PdfReader con overlay
        """
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=self.page_size)

        # Altezza pagina per conversione coordinate
        page_height = self.page_size[1]  # A4 = 841.89 punti

        page_num_map = {'first': 0, 'intermediate': 2, 'last': 1}
        target_page = page_num_map.get(page_type, 0)

        for mapping in field_mappings:
            page = mapping.get('page', 0)
            if page != target_page:
                continue

            # Valuta espressione
            text = self._evaluate_expression(mapping['jsonpath'], self.data)

            # Coordinate: converti da editor (top-left) a PDF (bottom-left)
            x = mapping.get('x', 0)
            editor_y = mapping.get('y', 0)
            pdf_y = page_height - editor_y  # Inversione asse Y
            font_size = mapping.get('font_size', 10)

            # Disegna testo
            can.setFont("Helvetica", font_size)
            can.drawString(x, pdf_y, str(text))

        can.showPage()  # Importante: mostra la pagina prima di salvare
        can.save()
        packet.seek(0)
        return PdfReader(packet)

    def _create_multipage_overlay(self, simple_fields, loop_fields, loop_items, page_type):
        """Crea overlay con campi semplici + loop items."""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=self.page_size)

        # Altezza pagina per conversione coordinate
        page_height = self.page_size[1]  # A4 = 841.89 punti

        page_num_map = {'first': 0, 'intermediate': 2, 'last': 1}
        target_page = page_num_map.get(page_type, 0)

        # Renderizza campi semplici (solo su prima/ultima)
        if page_type in ['first', 'last']:
            for mapping in simple_fields:
                page = mapping.get('page', 0)
                if page != target_page:
                    continue

                text = self._evaluate_expression(mapping['jsonpath'], self.data)
                x = mapping.get('x', 0)
                editor_y = mapping.get('y', 0)
                pdf_y = page_height - editor_y  # Conversione coordinate
                font_size = mapping.get('font_size', 10)

                can.setFont("Helvetica", font_size)
                can.drawString(x, pdf_y, str(text))

        # Renderizza loop items
        for idx, item in enumerate(loop_items):
            for mapping in loop_fields:
                page = mapping.get('page', 0)
                if page != target_page:
                    continue

                # Estrai il path dopo [*]. (es: $.designazioni[*].cognome -> $.cognome)
                jsonpath = mapping['jsonpath']
                if '[*].' in jsonpath:
                    # Prendi solo la parte dopo [*].
                    jsonpath = '$.' + jsonpath.split('[*].', 1)[1]
                else:
                    # Fallback: rimuovi solo [*]
                    jsonpath = jsonpath.replace('[*]', '')

                text = self._evaluate_expression(jsonpath, item)

                x = mapping.get('x', 0)
                editor_y = mapping.get('y', 0)
                y_offset = mapping.get('y_offset', 20)  # Spazio tra righe loop
                font_size = mapping.get('font_size', 10)

                # Conversione coordinate + offset loop
                # Nel PDF Y cresce verso l'alto, nell'editor verso il basso
                pdf_y = page_height - editor_y
                actual_y = pdf_y - (idx * y_offset)  # Sottrai perché scendiamo

                can.setFont("Helvetica", font_size)
                can.drawString(x, actual_y, str(text))

        can.showPage()  # Importante: mostra la pagina prima di salvare
        can.save()
        packet.seek(0)
        return PdfReader(packet)

    def _get_loop_items(self, loop_fields):
        """
        Estrae gli item del loop dai dati.

        Args:
            loop_fields: Lista field mappings con loop

        Returns:
            Lista di dict con item del loop
        """
        if not loop_fields:
            return []

        # Prendi il primo loop field per determinare il path
        first_loop = loop_fields[0]['jsonpath']

        # Estrai il path dell'array (es: $.designazioni[*].campo → $.designazioni)
        match = re.match(r'(\$\.[^\[]+)\[\*\]', first_loop)
        if not match:
            return []

        array_path = match.group(1)

        # Usa jsonpath per estrarre array
        try:
            expr = jsonpath_parse(array_path)
            matches = expr.find(self.data)
            if matches:
                return matches[0].value
        except:
            pass

        return []

    def _calculate_items_per_page(self, loop_fields):
        """
        Calcola quanti item del loop entrano in una pagina.

        Basato su y_offset e altezza disponibile.
        """
        if not loop_fields:
            return 10  # Default

        # Prendi y_offset dal primo field
        y_offset = loop_fields[0].get('y_offset', 20)
        editor_y = loop_fields[0].get('y', 700)

        # Converti coordinate editor → PDF
        page_height = self.page_size[1]
        pdf_y = page_height - editor_y

        # Calcola spazio disponibile (margine basso di 50 punti)
        available_height = pdf_y - 50

        return int(available_height / y_offset)

    def _evaluate_expression(self, expression, data):
        """
        Valuta espressione JSONPath con supporto per concatenazioni.

        Supporta (SICURO - no eval):
        - $.delegato.nome
        - $.delegato.nome + ' ' + $.delegato.cognome
        - $.designazioni[0].effettivo_cognome

        Args:
            expression: Stringa espressione
            data: Dict dati

        Returns:
            Valore valutato (str)
        """
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
                    # Converti date
                    if isinstance(value, (date, datetime)):
                        jsonpath_values[path] = value.strftime('%d/%m/%Y')
                    elif value is None:
                        jsonpath_values[path] = ''
                    elif isinstance(value, str) and len(value) == 10 and value[4] == '-' and value[7] == '-':
                        # Prova a parsare come data ISO (YYYY-MM-DD)
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
            # Sostituisci i JSONPath con i loro valori
            result = expression
            for path, value in jsonpath_values.items():
                result = result.replace(path, f'"{value}"')

            # Parse manuale della concatenazione (supporta solo + e stringhe literal)
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
                    # Skip apici singoli fuori dalle stringhe
                    continue
                elif in_string:
                    current += char

            return ''.join(parts)

        # Fallback: ritorna primo valore
        return list(jsonpath_values.values())[0] if jsonpath_values else ''


def generate_pdf(template_obj, data):
    """
    Helper per generare PDF.

    Args:
        template_obj: Oggetto Template Django
        data: Dict con dati

    Returns:
        BytesIO con PDF generato
    """
    generator = PDFGenerator(template_obj.template_file, data)
    return generator.generate_from_template(template_obj)
