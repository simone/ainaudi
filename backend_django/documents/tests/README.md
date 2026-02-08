# PDF Generator Tests

## Test Suite

### Unit Tests (`test_pdf_generator.py`)
Test del modulo `pdf_generator.py` in isolamento:

- ✅ **test_generate_single_page_simple_fields**: Genera PDF singola pagina con campi semplici (cognome, nome, carica)
- ✅ **test_generate_with_expression_concatenation**: Test espressioni con concatenazione (`nome + ' ' + cognome`)
- ✅ **test_generate_multipage_with_loop_small**: Loop con pochi elementi (1 pagina)
- ✅ **test_generate_multipage_with_loop_large**: Loop con molti elementi (forza multi-pagina)
- ✅ **test_evaluate_expression_with_date**: Formattazione date (dd/mm/yyyy)
- ✅ **test_generate_individuale_zip**: Generazione ZIP con N PDF individuali
- ✅ **test_handle_empty_values**: Gestione valori None/vuoti senza crash
- ✅ **test_complex_expression_multiple_concatenations**: Espressioni complesse con multiple concatenazioni

### Integration Tests (`delegations/tests/test_processo_pdf_generation.py`)
Test del flusso completo tramite `ProcessoDesignazione`:

- ✅ **test_genera_pdf_individuale_produces_zip**: Verifica che `_genera_pdf_individuale()` produca uno ZIP con N PDF (uno per sezione)
- ✅ **test_genera_pdf_cumulativo_produces_multipage**: Verifica che `_genera_pdf_cumulativo()` produca un PDF multi-pagina
- ✅ **test_genera_pdf_cumulativo_with_many_items**: Test multi-pagina con 40 designazioni
- ✅ **test_pdf_contains_date_formatted**: Verifica formattazione date nel PDF finale

## Eseguire i Test

### Tutti i test
```bash
cd backend_django
python manage.py test documents.tests
python manage.py test delegations.tests.test_processo_pdf_generation
```

### Solo unit test PDF generator
```bash
python manage.py test documents.tests.test_pdf_generator
```

### Solo integration test processo
```bash
python manage.py test delegations.tests.test_processo_pdf_generation
```

### Test specifico
```bash
python manage.py test documents.tests.test_pdf_generator.PDFGeneratorTestCase.test_generate_multipage_with_loop_large
```

### Con coverage
```bash
coverage run --source='.' manage.py test documents.tests delegations.tests.test_processo_pdf_generation
coverage report
coverage html  # Genera report HTML in htmlcov/
```

### Con verbose output
```bash
python manage.py test documents.tests --verbosity=2
```

## Docker

```bash
docker exec rdl_backend python manage.py test documents.tests
docker exec rdl_backend python manage.py test delegations.tests.test_processo_pdf_generation
```

## Cosa Testano

### PDF Individuale
- **Input**: 3 sezioni con designazioni
- **Output**: 1 ZIP file contenente 3 PDF (uno per sezione)
- **Verifica**:
  - ZIP contiene esattamente 3 file
  - Ogni PDF è singola pagina
  - Dati delegato presenti in ogni PDF
  - Dati RDL specifici per sezione presenti

### PDF Cumulativo
- **Input**: N sezioni con designazioni
- **Output**: 1 PDF multi-pagina
- **Verifica**:
  - Con 3 elementi: 1 pagina
  - Con 40 elementi: >= 2 pagine (calcolo: items_per_page = available_height / y_offset)
  - Tutti i dati presenti nel PDF
  - Dati distribuiti su più pagine

### Espressioni JSONPath
- Campi semplici: `$.delegato.cognome` → "Rossi"
- Concatenazione: `$.delegato.nome + ' ' + $.delegato.cognome` → "Mario Rossi"
- Loop: `$.designazioni[*].effettivo_cognome` → array values
- Date: `$.delegato.data_nascita` → "15/05/1980"

## Troubleshooting

### PyPDF2 non trovato
```bash
pip install PyPDF2 jsonpath-ng reportlab
```

### Test falliscono su estrazione testo
Il text extraction di PyPDF2 può essere impreciso. I test verificano la presenza di stringhe chiave, non l'esatta posizione.

### Template PDF non trovati
I test creano PDF template in memoria con ReportLab, non serve avere file fisici.
