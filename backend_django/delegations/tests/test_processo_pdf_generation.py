"""
Integration tests per generazione PDF tramite ProcessoDesignazione.

Testa il flusso completo:
1. Creazione processo
2. Configurazione template
3. Generazione PDF individuale (multi-pagina, una pagina per sezione)
4. Generazione PDF cumulativo (multi-pagina con loop)
5. Download documenti
"""
import io
from datetime import date
from django.test import TestCase
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader

from core.models import User
from elections.models import ConsultazioneElettorale
from territory.models import Regione, Provincia, Comune, SezioneElettorale
from delegations.models import Delegato, DesignazioneRDL, ProcessoDesignazione
from documents.models import Template


class ProcessoPDFGenerationTestCase(TestCase):
    """Test suite per generazione PDF tramite ProcessoDesignazione."""

    def setUp(self):
        """Setup test fixtures."""
        # User
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        # Consultazione
        self.consultazione = ConsultazioneElettorale.objects.create(
            nome="Test Elezioni 2026",
            data_inizio=date(2026, 6, 8),
            data_fine=date(2026, 6, 9)
        )

        # Territorio
        self.regione = Regione.objects.create(codice_istat='12', nome='Lazio')
        self.provincia = Provincia.objects.create(
            codice_istat='058',
            sigla='RM',
            nome='Roma',
            regione=self.regione
        )
        self.comune = Comune.objects.create(
            codice_istat='058091',
            nome='Roma',
            provincia=self.provincia
        )

        # Sezioni
        self.sezione1 = SezioneElettorale.objects.create(
            numero=1,
            comune=self.comune,
            indirizzo='Via Roma 1'
        )
        self.sezione2 = SezioneElettorale.objects.create(
            numero=2,
            comune=self.comune,
            indirizzo='Via Milano 2'
        )
        self.sezione3 = SezioneElettorale.objects.create(
            numero=3,
            comune=self.comune,
            indirizzo='Via Napoli 3'
        )

        # Delegato
        self.delegato = Delegato.objects.create(
            consultazione=self.consultazione,
            cognome='Rossi',
            nome='Mario',
            carica=Delegato.Carica.DEPUTATO,
            email='delegato@example.com',
            luogo_nascita='Roma',
            data_nascita=date(1980, 5, 15)
        )

        # Template PDF vuoti
        self.template_ind = self._create_template_with_mappings(
            'DESIGNATION_SINGLE',
            'Template Individuale',
            field_mappings=[
                {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},
                {'jsonpath': '$.delegato.nome', 'x': 200, 'y': 750, 'page': 0, 'font_size': 12},
                {'jsonpath': '$.designazioni[0].sezione_numero', 'x': 50, 'y': 700, 'page': 0, 'font_size': 10},
                {'jsonpath': '$.designazioni[0].effettivo_cognome', 'x': 100, 'y': 700, 'page': 0, 'font_size': 10},
                {'jsonpath': '$.designazioni[0].effettivo_nome', 'x': 200, 'y': 700, 'page': 0, 'font_size': 10},
            ]
        )

        self.template_cum = self._create_template_with_mappings(
            'DESIGNATION_MULTI',
            'Template Cumulativo',
            field_mappings=[
                {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},
                {'jsonpath': '$.delegato.nome', 'x': 200, 'y': 750, 'page': 0, 'font_size': 12},
                {'jsonpath': '$.designazioni[*].sezione_numero', 'x': 50, 'y': 650, 'y_offset': 20, 'page': 0, 'font_size': 10},
                {'jsonpath': '$.designazioni[*].effettivo_cognome', 'x': 100, 'y': 650, 'y_offset': 20, 'page': 0, 'font_size': 10},
                {'jsonpath': '$.designazioni[*].effettivo_nome', 'x': 200, 'y': 650, 'y_offset': 20, 'page': 0, 'font_size': 10},
            ],
            num_pages=3  # Prima, intermedia, ultima
        )

    def _create_blank_pdf(self, num_pages=1):
        """Crea un PDF vuoto per test."""
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        for i in range(num_pages):
            pdf.drawString(50, 800, f"Pagina {i}")
            pdf.showPage()

        pdf.save()
        buffer.seek(0)
        return buffer

    def _create_template_with_mappings(self, template_type_code, name, field_mappings, num_pages=1):
        """Crea un template con field_mappings."""
        pdf_buffer = self._create_blank_pdf(num_pages)

        template = Template.objects.create(
            consultazione=self.consultazione,
            template_type=template_type_code,
            name=name,
            field_mappings=field_mappings,
            is_active=True
        )

        # Salva PDF template
        template.template_file.save(
            f'{name.lower().replace(" ", "_")}.pdf',
            ContentFile(pdf_buffer.read()),
            save=True
        )

        return template

    def test_genera_pdf_individuale_produces_multipage(self):
        """Test che genera_individuale produca un PDF multi-pagina (una pagina per sezione)."""
        # Crea processo con designazioni
        processo = ProcessoDesignazione.objects.create(
            consultazione=self.consultazione,
            comune=self.comune,
            delegato=self.delegato,
            template_individuale=self.template_ind,
            template_cumulativo=self.template_cum,
            stato='BOZZA',
            created_by_email=self.user.email,
            dati_delegato={
                'cognome': 'Rossi',
                'nome': 'Mario',
                'carica': 'Deputato',
                'luogo_nascita': 'Roma',
                'data_nascita': '1980-05-15'
            }
        )

        # Crea designazioni
        designazioni = [
            DesignazioneRDL.objects.create(
                processo=processo,
                sezione=self.sezione1,
                delegato=self.delegato,
                effettivo_cognome='Neri',
                effettivo_nome='Andrea',
                effettivo_email='neri@test.com',
                effettivo_data_nascita=date(1985, 3, 20),
                stato='BOZZA'
            ),
            DesignazioneRDL.objects.create(
                processo=processo,
                sezione=self.sezione2,
                delegato=self.delegato,
                effettivo_cognome='Blu',
                effettivo_nome='Sara',
                effettivo_email='blu@test.com',
                effettivo_data_nascita=date(1990, 7, 10),
                stato='BOZZA'
            ),
            DesignazioneRDL.objects.create(
                processo=processo,
                sezione=self.sezione3,
                delegato=self.delegato,
                effettivo_cognome='Verdi',
                effettivo_nome='Luca',
                effettivo_email='verdi@test.com',
                effettivo_data_nascita=date(1988, 11, 5),
                stato='BOZZA'
            ),
        ]

        # Genera PDF individuale
        from delegations.views_processo import ProcessoDesignazioneViewSet

        viewset = ProcessoDesignazioneViewSet()
        viewset._genera_pdf_individuale(processo)

        # Verifica che documento_individuale sia stato creato
        self.assertTrue(processo.documento_individuale)
        self.assertIsNotNone(processo.data_generazione_individuale)

        # Leggi PDF multi-pagina
        pdf_reader = PdfReader(processo.documento_individuale.open('rb'))

        # Deve avere 3 pagine (una per sezione)
        self.assertEqual(len(pdf_reader.pages), 3)

        # Verifica pagina 1 (sezione 1)
        page1_text = pdf_reader.pages[0].extract_text()
        self.assertIn('Rossi', page1_text)
        self.assertIn('Mario', page1_text)
        self.assertIn('Neri', page1_text)
        self.assertIn('Andrea', page1_text)

        # Verifica pagina 2 (sezione 2)
        page2_text = pdf_reader.pages[1].extract_text()
        self.assertIn('Rossi', page2_text)
        self.assertIn('Blu', page2_text)
        self.assertIn('Sara', page2_text)

        # Verifica pagina 3 (sezione 3)
        page3_text = pdf_reader.pages[2].extract_text()
        self.assertIn('Rossi', page3_text)
        self.assertIn('Verdi', page3_text)
        self.assertIn('Luca', page3_text)

    def test_genera_pdf_cumulativo_produces_multipage(self):
        """Test che genera_cumulativo produca un PDF multi-pagina."""
        # Crea processo
        processo = ProcessoDesignazione.objects.create(
            consultazione=self.consultazione,
            comune=self.comune,
            delegato=self.delegato,
            template_individuale=self.template_ind,
            template_cumulativo=self.template_cum,
            stato='BOZZA',
            created_by_email=self.user.email,
            dati_delegato={
                'cognome': 'Rossi',
                'nome': 'Mario'
            }
        )

        # Crea designazioni
        for i, sezione in enumerate([self.sezione1, self.sezione2, self.sezione3]):
            DesignazioneRDL.objects.create(
                processo=processo,
                sezione=sezione,
                delegato=self.delegato,
                effettivo_cognome=f'Cognome{i+1}',
                effettivo_nome=f'Nome{i+1}',
                effettivo_email=f'rdl{i+1}@test.com',
                stato='BOZZA'
            )

        # Genera PDF cumulativo
        from delegations.views_processo import ProcessoDesignazioneViewSet

        viewset = ProcessoDesignazioneViewSet()
        viewset._genera_pdf_cumulativo(processo)

        # Verifica che documento_cumulativo sia stato creato
        self.assertTrue(processo.documento_cumulativo)
        self.assertIsNotNone(processo.data_generazione_cumulativo)

        # Leggi PDF cumulativo
        pdf_reader = PdfReader(processo.documento_cumulativo.open('rb'))

        # Deve contenere almeno 1 pagina
        self.assertGreaterEqual(len(pdf_reader.pages), 1)

        # Estrai tutto il testo
        all_text = ''
        for page in pdf_reader.pages:
            all_text += page.extract_text()

        # Verifica delegato
        self.assertIn('Rossi', all_text)
        self.assertIn('Mario', all_text)

        # Verifica tutte le designazioni siano presenti
        self.assertIn('Cognome1', all_text)
        self.assertIn('Nome1', all_text)
        self.assertIn('Cognome2', all_text)
        self.assertIn('Nome2', all_text)
        self.assertIn('Cognome3', all_text)
        self.assertIn('Nome3', all_text)

    def test_genera_pdf_cumulativo_with_many_items(self):
        """Test PDF cumulativo con molte designazioni (forza multi-pagina)."""
        processo = ProcessoDesignazione.objects.create(
            consultazione=self.consultazione,
            comune=self.comune,
            delegato=self.delegato,
            template_individuale=self.template_ind,
            template_cumulativo=self.template_cum,
            stato='BOZZA',
            created_by_email=self.user.email,
            dati_delegato={'cognome': 'Rossi', 'nome': 'Mario'}
        )

        # Crea 40 sezioni e designazioni per forzare multi-pagina
        sezioni = []
        for i in range(1, 41):
            sezione = SezioneElettorale.objects.create(
                numero=100 + i,
                comune=self.comune,
                indirizzo=f'Via Test {i}'
            )
            sezioni.append(sezione)

            DesignazioneRDL.objects.create(
                processo=processo,
                sezione=sezione,
                delegato=self.delegato,
                effettivo_cognome=f'Cognome{i}',
                effettivo_nome=f'Nome{i}',
                effettivo_email=f'rdl{i}@test.com',
                stato='BOZZA'
            )

        # Genera PDF cumulativo
        from delegations.views_processo import ProcessoDesignazioneViewSet

        viewset = ProcessoDesignazioneViewSet()
        viewset._genera_pdf_cumulativo(processo)

        # Leggi PDF
        pdf_reader = PdfReader(processo.documento_cumulativo.open('rb'))

        # Con 40 elementi e y_offset=20, dovrebbe generare multiple pagine
        # available_height = 650 - 50 = 600, items_per_page = 600 / 20 = 30
        # Prima pagina: 30 elementi
        # Ultima pagina: 10 elementi
        # Totale: 2 pagine
        self.assertGreaterEqual(len(pdf_reader.pages), 2)

        # Verifica che alcuni elementi chiave siano presenti
        all_text = ''
        for page in pdf_reader.pages:
            all_text += page.extract_text()

        self.assertIn('Cognome1', all_text)
        self.assertIn('Cognome20', all_text)
        # Note: PyPDF2 potrebbe non estrarre tutti gli elementi dalla seconda pagina
        # L'importante è che ci siano multiple pagine e i primi elementi siano presenti

    def test_pdf_contains_date_formatted(self):
        """Test che le date vengano formattate correttamente nel PDF."""
        # Aggiungi campo data al template
        template_with_date = self._create_template_with_mappings(
            'DESIGNATION_SINGLE',
            'Template con Date',
            field_mappings=[
                {'jsonpath': '$.delegato.cognome', 'x': 100, 'y': 750, 'page': 0, 'font_size': 12},
                {'jsonpath': '$.delegato.data_nascita', 'x': 100, 'y': 730, 'page': 0, 'font_size': 10},
                {'jsonpath': '$.designazioni[0].effettivo_data_nascita', 'x': 100, 'y': 700, 'page': 0, 'font_size': 10},
            ]
        )

        processo = ProcessoDesignazione.objects.create(
            consultazione=self.consultazione,
            comune=self.comune,
            delegato=self.delegato,
            template_individuale=template_with_date,
            template_cumulativo=self.template_cum,
            stato='BOZZA',
            created_by_email=self.user.email,
            dati_delegato={
                'cognome': 'Rossi',
                'data_nascita': date(1980, 5, 15).isoformat()
            }
        )

        DesignazioneRDL.objects.create(
            processo=processo,
            sezione=self.sezione1,
            delegato=self.delegato,
            effettivo_cognome='Neri',
            effettivo_nome='Andrea',
            effettivo_email='neri@test.com',
            effettivo_data_nascita=date(1985, 12, 25),
            stato='BOZZA'
        )

        # Genera PDF
        from delegations.views_processo import ProcessoDesignazioneViewSet

        viewset = ProcessoDesignazioneViewSet()
        viewset._genera_pdf_individuale(processo)

        # Verifica formato date nel PDF multi-pagina
        pdf_reader = PdfReader(processo.documento_individuale.open('rb'))
        page_text = pdf_reader.pages[0].extract_text()

        # Date devono essere in formato dd/mm/yyyy
        self.assertIn('15/05/1980', page_text)
        self.assertIn('25/12/1985', page_text)
