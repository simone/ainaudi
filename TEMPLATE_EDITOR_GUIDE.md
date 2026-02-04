# Guida Template Editor

## 📊 Stato Attuale

### ✅ **Implementato e Funzionante**

#### Backend (100% Completo)
- ✅ Modello database con campi `field_mappings`, `loop_config`, `merge_mode`
- ✅ API Endpoint `/api/documents/templates/{id}/editor/` (GET/PUT)
- ✅ Validazione dati
- ✅ Salvataggio/recupero configurazione

#### Frontend (Versione Base)
- ✅ Componente `TemplateEditor.js` creato
- ✅ Interfaccia per gestire field mappings
- ✅ Configurazione merge mode e loop
- ⚠️ Input manuale coordinate (no click visuale su PDF)

### ⏳ **Da Implementare per Versione Completa**

- ❌ Integrazione PDF.js per rendering PDF nel browser
- ❌ Click sul PDF per posizionare campi visualmente
- ❌ Drag & drop per ridimensionare aree
- ❌ Preview real-time con dati di esempio

---

## 🎯 Come Funziona Adesso

### Sistema Attuale: Template Hardcoded

Il sistema PDF funziona **SENZA** l'editor, usando logica hardcoded:

```python
# pdf/generate_adapter.py
def _generate_individual(data):
    # Cerca placeholder nel PDF con formato {KEY}
    text_instances = page.search_for(f"{{{key.upper()}}}")

    # Sostituisce con il valore dai dati
    for inst in text_instances:
        rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
        new_page.insert_text((rect.x0, rect.y1), str(value))
```

**Vantaggi**:
- ✅ Funziona subito
- ✅ Nessuna configurazione necessaria
- ✅ Semplice da capire

**Svantaggi**:
- ❌ Modifiche richiedono deploy codice
- ❌ Posizioni fisse nel template PDF
- ❌ Non flessibile

### Sistema con Editor: Template Configurabili

Con l'editor, potresti:

1. **Caricare** un PDF template vuoto
2. **Cliccare** sulle aree dove vuoi i dati
3. **Specificare** quale dato va in quell'area (JSONPath)
4. **Salvare** la configurazione nel database
5. Il worker **usa la configurazione** invece del codice hardcoded

---

## 🚀 Come Usare l'Editor Base (Ora)

### Step 1: Aggiungi Route in App.js

```javascript
// src/App.js
import TemplateEditor from './TemplateEditor';

// Nel render, aggiungi:
{activeTab === 'template-editor' && user?.is_superuser && (
    <TemplateEditor templateId={1} client={client} />
)}
```

### Step 2: Accedi all'Editor

1. Login come admin/superuser
2. Naviga alla tab "Template Editor"
3. Seleziona template da configurare

### Step 3: Configura Campi Manualmente

```javascript
// Esempio configurazione campo:
{
  "area": {
    "x": 100,      // Posizione orizzontale
    "y": 200,      // Posizione verticale
    "width": 200,  // Larghezza area
    "height": 20   // Altezza area
  },
  "jsonpath": "$.delegato.cognome",  // Da dove prendere il dato
  "type": "text",                     // Tipo campo (text o loop)
  "page": 0                           // Pagina del PDF (0-based)
}
```

### Step 4: Configura Loop (Opzionale)

Per documenti multi-pagina:

```javascript
{
  "merge_mode": "MULTI_PAGE_LOOP",
  "loop_config": {
    "rows_first_page": 6,   // Righe sulla prima pagina
    "rows_per_page": 13,    // Righe per pagine successive
    "data_source": "$.designazioni"
  }
}
```

### Step 5: Salva Configurazione

Click "Salva Template" → Configurazione salvata in database

---

## 🔧 Come Integrare con il Worker

### Modifica 1: Far Leggere la Configurazione al Worker

Attualmente il worker NON legge i `field_mappings`. Per abilitarlo:

```python
# pdf/generate_adapter.py

def generate_pdf_from_template(template_name, data):
    # PRIMA: Cerca template nel database
    template_data = _fetch_template_from_django(template_name)

    if template_data and template_data.get('field_mappings'):
        # USA field_mappings dal database
        return _generate_with_mappings(template_data, data)
    else:
        # FALLBACK: usa logica hardcoded
        return _generate_individual(data)

def _fetch_template_from_django(template_name):
    """
    Fetch template configuration from Django API.
    Cache locally to avoid repeated calls.
    """
    import requests

    # Chiama Django API
    response = requests.get(
        f'http://backend:8000/api/documents/templates/?name={template_name}'
    )

    if response.ok:
        templates = response.json()
        return templates[0] if templates else None
    return None

def _generate_with_mappings(template_data, data):
    """
    Generate PDF using field_mappings from database.
    """
    import fitz

    doc = fitz.open(template_data['template_file_path'])
    output_doc = fitz.open()

    # Per ogni mapping, inserisci il testo nelle coordinate specificate
    for mapping in template_data['field_mappings']:
        area = mapping['area']
        jsonpath = mapping['jsonpath']

        # Risolvi il JSONPath nei dati
        value = _resolve_jsonpath(jsonpath, data)

        # Inserisci testo nell'area specificata
        page = output_doc[mapping.get('page', 0)]
        page.insert_text(
            (area['x'], area['y'] + area['height']),
            str(value),
            fontsize=10
        )

    # ... return PDF bytes
```

### Modifica 2: Cache della Configurazione

```python
# pdf/template_cache.py

_template_cache = {}

def get_template_config(template_name):
    """Get template config with caching."""
    if template_name not in _template_cache:
        _template_cache[template_name] = _fetch_template_from_django(template_name)
    return _template_cache[template_name]

def clear_cache():
    """Clear cache when templates are updated."""
    global _template_cache
    _template_cache = {}
```

---

## 🎨 Upgrade a Editor Visuale Completo

Per avere il **click sul PDF** per posizionare i campi:

### Step 1: Installa PDF.js

```bash
npm install pdfjs-dist
```

### Step 2: Modifica TemplateEditor.js

```javascript
import * as pdfjsLib from 'pdfjs-dist/webpack';

function TemplateEditor({ templateId, client }) {
    const [pdfDoc, setPdfDoc] = useState(null);
    const canvasRef = useRef(null);

    // Carica e renderizza PDF
    useEffect(() => {
        if (template?.template_file_url) {
            loadPDF(template.template_file_url);
        }
    }, [template]);

    const loadPDF = async (url) => {
        const pdf = await pdfjsLib.getDocument(url).promise;
        setPdfDoc(pdf);
        renderPage(pdf, 1);
    };

    const renderPage = async (pdf, pageNum) => {
        const page = await pdf.getPage(pageNum);
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const viewport = page.getViewport({ scale: 1.5 });

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        await page.render({ canvasContext: ctx, viewport }).promise;

        // Disegna field mappings esistenti
        drawExistingMappings(ctx);
    };

    const handleCanvasClick = (e) => {
        const rect = canvasRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Inizia selezione area
        startAreaSelection(x, y);
    };

    return (
        <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            style={{ border: '1px solid #ccc', cursor: 'crosshair' }}
        />
    );
}
```

### Step 3: Aggiungi Selezione Drag

```javascript
const [isSelecting, setIsSelecting] = useState(false);
const [selectionStart, setSelectionStart] = useState(null);
const [currentSelection, setCurrentSelection] = useState(null);

const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    setSelectionStart({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    });
    setIsSelecting(true);
};

const handleMouseMove = (e) => {
    if (!isSelecting) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    setCurrentSelection({
        x: selectionStart.x,
        y: selectionStart.y,
        width: currentX - selectionStart.x,
        height: currentY - selectionStart.y
    });

    // Ridisegna PDF con rettangolo selezione
    redrawWithSelection();
};

const handleMouseUp = () => {
    if (!isSelecting || !currentSelection) return;

    setIsSelecting(false);

    // Apri dialog per configurare questo campo
    openFieldConfigDialog(currentSelection);
};
```

---

## 📊 Confronto Approcci

### Opzione A: Template Hardcoded (Attuale) ⭐

**Pro**:
- ✅ Funziona subito, zero configurazione
- ✅ Veloce da sviluppare
- ✅ Nessuna dipendenza frontend pesante
- ✅ Facile debug

**Contro**:
- ❌ Modifiche richiedono deploy
- ❌ Non flessibile
- ❌ Un template per tipo

**Quando usare**: Se hai pochi template stabili che cambiano raramente.

### Opzione B: Editor Base (Implementato Ora) 🔨

**Pro**:
- ✅ Configurazione salvata in database
- ✅ Modifiche senza deploy
- ✅ Backend pronto
- ✅ Semplice da capire

**Contro**:
- ⚠️ Richiede input manuale coordinate
- ⚠️ Scomodo per tanti campi
- ⚠️ Worker deve essere modificato per usarlo

**Quando usare**: Se hai admin tecnici che sanno usare coordinate.

### Opzione C: Editor Visuale Completo (Da Fare) 🎨

**Pro**:
- ✅ Interfaccia user-friendly
- ✅ Click sul PDF per posizionare
- ✅ Preview real-time
- ✅ Massima flessibilità

**Contro**:
- ❌ Richiede PDF.js (~100KB)
- ❌ Più complesso da sviluppare
- ❌ Più testing necessario

**Quando usare**: Se hai molti template o utenti non tecnici.

---

## ✅ Raccomandazione

### Per Adesso: Usa Template Hardcoded

Il sistema attuale funziona bene perché:
1. Hai pochi template (individuale, riepilogativo)
2. I template sono stabili
3. Zero overhead di configurazione
4. Già implementato e testato

### In Futuro: Aggiungi Editor se Necessario

Implementa l'editor solo se:
- Hai bisogno di creare nuovi template spesso
- Le posizioni dei campi cambiano frequentemente
- Vuoi dare la possibilità agli admin di configurare senza dev

---

## 🎯 Prossimi Passi (Se Vuoi l'Editor Completo)

1. **Testa l'editor base** con input manuale
   ```bash
   # Aggiungi route in App.js
   # Accedi come superuser
   # Prova ad aggiungere/rimuovere campi
   ```

2. **Modifica il worker** per leggere field_mappings
   ```python
   # Aggiungi _fetch_template_from_django()
   # Aggiungi _generate_with_mappings()
   # Testa con template configurato
   ```

3. **Se serve visuale**, aggiungi PDF.js
   ```bash
   npm install pdfjs-dist
   # Segui "Upgrade a Editor Visuale Completo"
   ```

---

## 📚 Riferimenti

- **Backend API**: `backend_django/documents/views.py` (TemplateEditorView)
- **Modello Database**: `backend_django/documents/models.py` (Template.field_mappings)
- **Frontend Base**: `src/TemplateEditor.js` (appena creato)
- **Worker**: `pdf/generate_adapter.py` (da modificare per usare field_mappings)

---

## ❓ FAQ

**Q: Devo per forza usare l'editor?**
A: No! Il sistema funziona già con template hardcoded.

**Q: Posso migrare template esistenti all'editor?**
A: Sì, ma devi mappare i placeholder {KEY} alle coordinate.

**Q: L'editor è obbligatorio per il two-phase workflow?**
A: No, sono sistemi separati. Il two-phase funziona con qualsiasi template.

**Q: Posso usare l'editor solo per alcuni template?**
A: Sì, il worker fa fallback automatico se non trova field_mappings.

**Q: L'editor funziona con tutti i PDF?**
A: Sì, ma devi configurare manualmente le posizioni dei campi.

---

**Stato**: Editor Base Implementato ✅ | Editor Visuale Opzionale ⏳
**Versione**: 1.0
**Data**: 2026-02-04
