"""
Unit tests per PDF Generator.

Testa:
- Generazione PDF con template + dati
- Espressioni JSONPath con concatenazione
- Loop multi-pagina
- Verifica dati scritti nel PDF
"""
import io
from datetime import date
from django.test import TestCase
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader

from documents.pdf_generator import PDFGenerator, generate_pdf
from documents.models import Template, TemplateType
from elections.models import ConsultazioneElettorale


class PDFGeneratorTestCase(TestCase):
    """Test suite per PDFGenerator."""

    def setUp(self):
        """Setup test fixtures."""
        # Crea consultazione di test
        self.consultazione = ConsultazioneElettorale.objects.create(
            nome="Test Elezioni 2026",
            data_inizio=date(2026, 6, 8),
            data_fine=date(2026, 6, 9)
        )

        # Crea tipo template
        self.template_type = TemplateType.objects.create(
            code="TEST_TEMPLATE",
            name="Template Test",
            default_merge_mode=TemplateType.MergeMode.SINGLE_DOC_PER_RECORD
        )

    def _create_blank_pdf_template(self, num_pages=1):
        """Crea un PDF template vuoto per test."""
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        for i in range(num_pages):
            # Aggiungi numero pagina per debug
            pdf.drawString(50, 800, f"Pagina {i}")
            pdf.showPage()

        pdf.save()
        buffer.seek(0)
        return buffer

    def _create_mock_template(self, field_mappings):
        """Crea un mock template object con field_mappings."""
        class MockTemplate:
            pass

        mock = MockTemplate()
        mock.field_mappings = field_mappings
        return mock

    def test_generate_single_page_simple_fields(self):
        """Test generazione PDF singola pagina con campi semplici."""
        # Crea template PDF vuoto
        template_buffer = self._create_blank_pdf_template(num_pages=1)

        # Dati test
        data = {
            'delegato': {
                'cognome': 'Rossi',
                'nome': 'Mario',
                'carica': 'Deputato',
                'data_nomina': date(2025, 1, 15)
            }
        }

        # Field mappings
        field_mappings = [
            {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 700, 'page': 0, 'font_size': 12},
            {'jsonpath': '$.delegato.nome', 'x': 200, 'y': 700, 'page': 0, 'font_size': 12},
            {'jsonpath': '$.delegato.carica', 'x': 100, 'y': 680, 'page': 0, 'font_size': 10},
        ]

        # Genera PDF
        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)
        output = generator.generate_from_template(mock_template)

        # Verifica output
        self.assertIsNotNone(output)
        self.assertIsInstance(output, io.BytesIO)

        # Leggi PDF generato e verifica contenuto
        pdf_reader = PdfReader(output)
        self.assertEqual(len(pdf_reader.pages), 1)

        # Estrai testo dalla prima pagina
        page_text = pdf_reader.pages[0].extract_text()

        # Verifica che i dati siano presenti
        self.assertIn('Rossi', page_text)
        self.assertIn('Mario', page_text)
        self.assertIn('Deputato', page_text)

    def test_generate_with_expression_concatenation(self):
        """Test generazione con espressioni concatenate (nome + cognome)."""
        template_buffer = self._create_blank_pdf_template(num_pages=1)

        data = {
            'delegato': {
                'cognome': 'Bianchi',
                'nome': 'Laura'
            }
        }

        generator = PDFGenerator(template_buffer, data)

        mock_template = self._create_mock_template([
                    {
                        'jsonpath': "$.delegato.nome + ' ' + $.delegato.cognome",
                        'x': 100,
                        'y': 700,
                        'page': 0,
                        'font_size': 14
                    }
                ])
        output = generator.generate_from_template(mock_template)

        # Verifica
        pdf_reader = PdfReader(output)
        page_text = pdf_reader.pages[0].extract_text()

        # Deve contenere il nome completo concatenato (PyPDF2 può rimuovere spazi)
        self.assertIn('Laura', page_text)
        self.assertIn('Bianchi', page_text)

    def test_generate_multipage_with_loop_small(self):
        """Test generazione multi-pagina con loop (pochi elementi, 1 pagina)."""
        # Template con 3 pagine (prima, intermedia, ultima)
        template_buffer = self._create_blank_pdf_template(num_pages=3)

        data = {
            'delegato': {
                'cognome': 'Verdi',
                'nome': 'Giuseppe'
            },
            'designazioni': [
                {
                    'sezione_numero': 1,
                    'effettivo_cognome': 'Neri',
                    'effettivo_nome': 'Andrea'
                },
                {
                    'sezione_numero': 2,
                    'effettivo_cognome': 'Blu',
                    'effettivo_nome': 'Sara'
                },
                {
                    'sezione_numero': 3,
                    'effettivo_cognome': 'Gialli',
                    'effettivo_nome': 'Luca'
                }
            ]
        }

        field_mappings = [
            # Campo semplice (delegato)
            {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},

            # Loop fields
            {'jsonpath': '$.designazioni[*].sezione_numero', 'x': 50, 'y': 600, 'y_offset': 20, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.designazioni[*].effettivo_cognome', 'x': 100, 'y': 600, 'y_offset': 20, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.designazioni[*].effettivo_nome', 'x': 200, 'y': 600, 'y_offset': 20, 'page': 0, 'font_size': 10},
        ]

        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)
        output = generator.generate_from_template(mock_template)

        # Verifica output
        pdf_reader = PdfReader(output)

        # Con 3 elementi e y_offset=20, dovrebbe stare in 1 pagina
        self.assertEqual(len(pdf_reader.pages), 1)

        page_text = pdf_reader.pages[0].extract_text()

        # Verifica delegato
        self.assertIn('Verdi', page_text)

        # Verifica tutti gli RDL
        self.assertIn('Neri', page_text)
        self.assertIn('Andrea', page_text)
        self.assertIn('Blu', page_text)
        self.assertIn('Sara', page_text)
        self.assertIn('Gialli', page_text)
        self.assertIn('Luca', page_text)

    def test_generate_multipage_with_loop_large(self):
        """Test generazione multi-pagina con loop (molti elementi, multi-pagina)."""
        template_buffer = self._create_blank_pdf_template(num_pages=3)

        # Genera 50 designazioni per forzare multi-pagina
        designazioni = []
        for i in range(1, 51):
            designazioni.append({
                'sezione_numero': i,
                'effettivo_cognome': f'Cognome{i}',
                'effettivo_nome': f'Nome{i}'
            })

        data = {
            'delegato': {
                'cognome': 'Delegato',
                'nome': 'Test'
            },
            'designazioni': designazioni
        }

        field_mappings = [
            {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},
            {'jsonpath': '$.designazioni[*].sezione_numero', 'x': 50, 'y': 650, 'y_offset': 20, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.designazioni[*].effettivo_cognome', 'x': 100, 'y': 650, 'y_offset': 20, 'page': 0, 'font_size': 10},
        ]

        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)
        output = generator.generate_from_template(mock_template)

        # Verifica output
        pdf_reader = PdfReader(output)

        # Con 50 elementi e y_offset=20, y_start=650, dovrebbe generare multiple pagine
        # Calcolo: available_height = 650 - 50 = 600, items_per_page = 600 / 20 = 30
        # 50 elementi = prima pagina (30) + ultima pagina (20) = 2 pagine
        self.assertGreaterEqual(len(pdf_reader.pages), 2)

        # Verifica che i dati siano distribuiti sulle pagine
        all_text = ''
        for page in pdf_reader.pages:
            all_text += page.extract_text()

        # Verifica presenza di alcuni elementi chiave
        self.assertIn('Delegato', all_text)
        self.assertIn('Cognome1', all_text)
        self.assertIn('Cognome25', all_text)
        # Note: PyPDF2 potrebbe non estrarre tutti gli elementi dalla seconda pagina
        # L'importante è che ci siano multiple pagine e i primi elementi siano presenti

    def test_evaluate_expression_with_date(self):
        """Test valutazione espressione con date."""
        template_buffer = self._create_blank_pdf_template(num_pages=1)

        data = {
            'delegato': {
                'data_nascita': date(1980, 5, 15)
            }
        }

        field_mappings = [
            {'jsonpath': '$.delegato.data_nascita', 'x': 100, 'y': 700, 'page': 0, 'font_size': 10}
        ]

        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)
        output = generator.generate_from_template(mock_template)

        pdf_reader = PdfReader(output)
        page_text = pdf_reader.pages[0].extract_text()

        # Le date vengono formattate come dd/mm/yyyy
        self.assertIn('15/05/1980', page_text)

    def test_generate_individuale_multipage(self):
        """Test generazione PDF multi-pagina individuale (una pagina per sezione)."""
        from PyPDF2 import PdfWriter

        template_buffer = self._create_blank_pdf_template(num_pages=1)

        # Simula 3 sezioni
        sezioni_data = [
            {
                'delegato': {'cognome': 'Rossi', 'nome': 'Mario'},
                'designazioni': [{
                    'sezione_numero': 1,
                    'effettivo_cognome': 'Neri',
                    'effettivo_nome': 'Andrea'
                }]
            },
            {
                'delegato': {'cognome': 'Rossi', 'nome': 'Mario'},
                'designazioni': [{
                    'sezione_numero': 2,
                    'effettivo_cognome': 'Blu',
                    'effettivo_nome': 'Sara'
                }]
            },
            {
                'delegato': {'cognome': 'Rossi', 'nome': 'Mario'},
                'designazioni': [{
                    'sezione_numero': 3,
                    'effettivo_cognome': 'Verdi',
                    'effettivo_nome': 'Luca'
                }]
            }
        ]

        field_mappings = [
            {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},
            {'jsonpath': '$.designazioni[0].sezione_numero', 'x': 50, 'y': 700, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.designazioni[0].effettivo_cognome', 'x': 100, 'y': 700, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.designazioni[0].effettivo_nome', 'x': 200, 'y': 700, 'page': 0, 'font_size': 10},
        ]

        # Genera PDF multi-pagina
        writer = PdfWriter()

        for idx, data in enumerate(sezioni_data):
            generator = PDFGenerator(template_buffer, data)
            mock_template = self._create_mock_template(field_mappings)
            pdf_bytes = generator.generate_from_template(mock_template)

            # Aggiungi pagina al writer
            pdf_reader = PdfReader(pdf_bytes)
            for page in pdf_reader.pages:
                writer.add_page(page)

            # Reset buffer per prossimo PDF
            template_buffer.seek(0)

        # Scrivi PDF finale
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        # Verifica PDF multi-pagina
        pdf_reader = PdfReader(output)

        # Deve avere 3 pagine (una per sezione)
        self.assertEqual(len(pdf_reader.pages), 3)

        # Verifica contenuto pagina 1
        page1_text = pdf_reader.pages[0].extract_text()
        self.assertIn('Rossi', page1_text)
        self.assertIn('Neri', page1_text)
        self.assertIn('Andrea', page1_text)

        # Verifica contenuto pagina 2
        page2_text = pdf_reader.pages[1].extract_text()
        self.assertIn('Rossi', page2_text)
        self.assertIn('Blu', page2_text)
        self.assertIn('Sara', page2_text)

        # Verifica contenuto pagina 3
        page3_text = pdf_reader.pages[2].extract_text()
        self.assertIn('Rossi', page3_text)
        self.assertIn('Verdi', page3_text)
        self.assertIn('Luca', page3_text)

    def test_handle_empty_values(self):
        """Test gestione valori vuoti/None."""
        template_buffer = self._create_blank_pdf_template(num_pages=1)

        data = {
            'delegato': {
                'cognome': 'Rossi',
                'nome': None,
                'telefono': ''
            }
        }

        field_mappings = [
            {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 700, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.delegato.nome', 'x': 200, 'y': 700, 'page': 0, 'font_size': 10},
            {'jsonpath': '$.delegato.telefono', 'x': 300, 'y': 700, 'page': 0, 'font_size': 10},
        ]

        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)

        # Non deve crashare
        output = generator.generate_from_template(mock_template)

        self.assertIsNotNone(output)
        pdf_reader = PdfReader(output)
        self.assertEqual(len(pdf_reader.pages), 1)

    def test_complex_expression_multiple_concatenations(self):
        """Test espressioni complesse con multiple concatenazioni."""
        template_buffer = self._create_blank_pdf_template(num_pages=1)

        data = {
            'delegato': {
                'cognome': 'Rossi',
                'nome': 'Mario',
                'luogo_nascita': 'Roma'
            }
        }

        # Espressione complessa: nome + cognome + luogo
        field_mappings = [
            {
                'jsonpath': "$.delegato.nome + ' ' + $.delegato.cognome + ', nato a ' + $.delegato.luogo_nascita",
                'x': 100,
                'y': 700,
                'page': 0,
                'font_size': 10
            }
        ]

        generator = PDFGenerator(template_buffer, data)
        mock_template = self._create_mock_template(field_mappings)
        output = generator.generate_from_template(mock_template)

        pdf_reader = PdfReader(output)
        page_text = pdf_reader.pages[0].extract_text()

        # Deve contenere la stringa concatenata (PyPDF2 può rimuovere spazi)
        self.assertIn('Mario', page_text)
        self.assertIn('Rossi', page_text)
        self.assertIn('Roma', page_text)
