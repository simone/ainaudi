# Template Editor - Implementazione Completa

## ✅ Cosa è Stato Implementato

### 1. Backend Django (100% Funzionante)

#### API Endpoints CRUD Completi
- ✅ **GET** `/api/documents/templates/` - Lista template
- ✅ **POST** `/api/documents/templates/` - Crea template (admin only)
- ✅ **GET** `/api/documents/templates/{id}/` - Dettaglio template
- ✅ **PUT** `/api/documents/templates/{id}/` - Modifica template (admin only)
- ✅ **DELETE** `/api/documents/templates/{id}/` - Elimina template (soft delete, admin only)
- ✅ **GET** `/api/documents/templates/{id}/editor/` - Configurazione editor
- ✅ **PUT** `/api/documents/templates/{id}/editor/` - Salva field mappings

**File**: `backend_django/documents/views.py`

#### Permessi
- Lettura: Qualsiasi utente autenticato
- Creazione/Modifica/Elimina: Solo admin/superuser

### 2. Client.js - Metodi HTTP Generici

Aggiunti metodi generici per chiamate API:

```javascript
client.get(url, options)      // GET request
client.post(url, data, options) // POST request
client.put(url, data, options)  // PUT request
client.delete(url, options)     // DELETE request
client.upload(url, formData, options) // Upload multipart/form-data
```

**File**: `src/Client.js`

### 3. Frontend Template Editor (Completo)

#### Funzionalità
- ✅ **Lista Template**: Carica tutti i template dal database
- ✅ **Selettore**: Dropdown per scegliere quale template modificare
- ✅ **Crea Nuovo**: Form per creare template con upload PDF
- ✅ **Modifica Mappings**: Aggiungi/rimuovi field mappings
- ✅ **Configura Loop**: Imposta merge mode e pagination
- ✅ **Salva**: Salva configurazione nel database
- ✅ **Elimina**: Elimina template (soft delete)

**File**: `src/TemplateEditor.js`, `src/TemplateEditor.css`

#### Interfaccia

```
┌────────────────────────────────────────────────────┐
│ Editor Template PDF                                │
│                                                     │
│ Seleziona Template: [individuale ▼]                │
│                                                     │
│ [+ Nuovo Template] [Salva Configurazione] [Elimina]│
└────────────────────────────────────────────────────┘
```

### 4. Routing e Menu

Aggiunto nell'app principale:

- Menu: **Admin** → **Template PDF**
- Solo visibile per superuser
- Tab nell'applicazione

**File**: `src/App.js`

---

## 🎯 Come Usare

### Step 1: Accedi come Admin

1. Login su http://localhost:3000
2. Account con `is_superuser=True`

### Step 2: Naviga all'Editor

1. Click su menu **Admin** (icona ingranaggio)
2. Click su **Template PDF**

### Step 3: Crea Nuovo Template

1. Click **+ Nuovo Template**
2. Compila form:
   - **Nome**: es. "individuale"
   - **Tipo**: Delega/Scrutinio/Segnalazione
   - **Descrizione**: testo libero
   - **File PDF**: upload file `.pdf`
3. Click **Crea Template**

### Step 4: Configura Field Mappings

1. Seleziona template dal dropdown
2. Click **Aggiungi Campo**
3. Inserisci:
   - **JSONPath**: `$.delegato.cognome`
   - **Tipo**: `text` o `loop`
   - **Coordinate**: x, y, width, height
4. Ripeti per ogni campo
5. Click **Salva Configurazione**

### Step 5: Configura Merge Mode (Opzionale)

Per documenti multi-pagina:

1. Seleziona **Modalità Unione**: "Documento multi-pagina con loop"
2. Imposta:
   - **Righe prima pagina**: 6
   - **Righe per pagina**: 13
3. Click **Salva Configurazione**

---

## 📊 Struttura Dati

### Template Model (Django)

```python
class Template(models.Model):
    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(choices=TemplateType.choices)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to='templates/')
    is_active = models.BooleanField(default=True)

    # Editor fields
    field_mappings = models.JSONField(default=list)
    loop_config = models.JSONField(default=dict)
    merge_mode = models.CharField(max_length=25)
```

### Field Mapping Example

```json
{
  "area": {
    "x": 100,
    "y": 200,
    "width": 200,
    "height": 20
  },
  "jsonpath": "$.delegato.cognome",
  "type": "text",
  "page": 0
}
```

### Loop Config Example

```json
{
  "rows_first_page": 6,
  "rows_per_page": 13,
  "data_source": "$.designazioni"
}
```

---

## 🔧 Limitazioni Attuali

### ⚠️ Input Manuale Coordinate

L'editor **NON ha** click visuale sul PDF. Le coordinate devono essere inserite manualmente.

**Come trovare le coordinate**:
1. Apri il PDF in un viewer che mostra coordinate (Adobe Acrobat)
2. Nota la posizione x, y del punto in alto a sinistra
3. Nota larghezza e altezza dell'area

### ⚠️ Worker Non Integrato

Il worker PDF attualmente **NON usa** i `field_mappings` dal database.

Per integrarlo:
1. Vedi `TEMPLATE_EDITOR_GUIDE.md` sezione "Come Integrare con il Worker"
2. Modifica `pdf/generate_adapter.py`
3. Aggiungi `_fetch_template_from_django()`
4. Aggiungi `_generate_with_mappings()`

---

## 🎨 Upgrade Futuro: Editor Visuale

Per aggiungere click sul PDF:

### 1. Installa PDF.js

```bash
npm install pdfjs-dist
```

### 2. Modifica TemplateEditor.js

Aggiungi:
- Canvas interattivo con rendering PDF
- Click handler per iniziare selezione area
- Drag handler per ridimensionare area
- Dialog per configurare campo selezionato

Vedi `TEMPLATE_EDITOR_GUIDE.md` per codice completo.

---

## 📁 File Modificati/Creati

### Backend
- ✅ `backend_django/documents/views.py` - CRUD completo
- ✅ `backend_django/documents/models.py` - Field mappings (già fatto)

### Frontend
- ✅ `src/Client.js` - Metodi HTTP generici
- ✅ `src/TemplateEditor.js` - Componente completo
- ✅ `src/TemplateEditor.css` - Stili
- ✅ `src/App.js` - Routing e menu

### Documentazione
- ✅ `TEMPLATE_EDITOR_GUIDE.md` - Guida completa
- ✅ `TEMPLATE_EDITOR_FIXED.md` - Questo file

---

## ✅ Testing

### Test Creazione Template

```bash
# 1. Login come superuser
# 2. Naviga: Admin → Template PDF
# 3. Click "+ Nuovo Template"
# 4. Compila form e upload PDF
# 5. Verifica creazione in database

docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, name, template_type FROM documents_template;"
```

### Test Field Mappings

```bash
# 1. Seleziona template
# 2. Aggiungi campo con coordinate
# 3. Salva configurazione
# 4. Verifica in database

docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, name, field_mappings FROM documents_template WHERE id=1;"
```

### Test Eliminazione

```bash
# 1. Seleziona template
# 2. Click "Elimina"
# 3. Conferma dialog
# 4. Verifica soft delete (is_active=False)

docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, name, is_active FROM documents_template;"
```

---

## 🐛 Troubleshooting

### Errore: "client.get is not a function"

✅ **RISOLTO** - Metodi generici aggiunti al Client.js

### Errore: "Method not allowed" su POST

✅ **RISOLTO** - ViewSet cambiato da ReadOnly a ModelViewSet

### Errore: "Permission denied"

Verifica di essere loggato come superuser:
```bash
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT email, is_superuser FROM core_user WHERE email='your@email.com';"
```

### Template non appare in lista

Verifica `is_active=True`:
```bash
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT * FROM documents_template;"
```

---

## 🎯 Prossimi Passi

### Opzione A: Usa Template Hardcoded (Raccomandato per ora)

Il sistema PDF funziona già perfettamente senza l'editor.

**Pro**:
- Zero configurazione
- Veloce
- Testato

**Quando**: Hai pochi template che cambiano raramente

### Opzione B: Integra Worker con Field Mappings

Se vuoi usare l'editor per configurare i PDF:

1. Modifica `pdf/generate_adapter.py`
2. Aggiungi fetch configurazione da Django
3. Usa field_mappings invece di search placeholder

Vedi `TEMPLATE_EDITOR_GUIDE.md` per implementazione.

### Opzione C: Aggiungi Editor Visuale

Se vuoi il click sul PDF:

1. Installa PDF.js
2. Aggiungi canvas interattivo
3. Implementa drag & drop

Vedi `TEMPLATE_EDITOR_GUIDE.md` per guida completa.

---

## 📊 Stato Attuale

| Componente | Stato | Note |
|------------|-------|------|
| **Backend CRUD** | ✅ 100% | Tutti gli endpoint funzionanti |
| **Client Methods** | ✅ 100% | GET, POST, PUT, DELETE, Upload |
| **Frontend UI** | ✅ 100% | CRUD completo con form |
| **Routing/Menu** | ✅ 100% | Accessibile da menu Admin |
| **Upload PDF** | ✅ 100% | Multipart upload funzionante |
| **Field Mappings** | ✅ 100% | Aggiungi/rimuovi campi |
| **Editor Visuale** | ⏳ 0% | Serve PDF.js (opzionale) |
| **Worker Integration** | ⏳ 0% | Worker usa ancora hardcoded |

---

## 📝 Riepilogo

### ✅ Cosa Funziona Adesso

1. **CRUD Completo Template**
   - Crea nuovo template con upload PDF
   - Modifica configurazione field mappings
   - Elimina template (soft delete)

2. **Editor Base**
   - Selezione template da lista
   - Gestione field mappings (input manuale)
   - Configurazione merge mode e loop
   - Salvataggio in database

3. **Interfaccia Admin**
   - Menu Admin accessibile
   - Componente integrato in App.js
   - Solo per superuser

### ⏳ Cosa Serve Ancora (Opzionale)

1. **Editor Visuale**
   - PDF.js per rendering
   - Click su PDF per posizionare
   - Drag & drop per ridimensionare

2. **Worker Integration**
   - Lettura field_mappings da DB
   - Generazione PDF con coordinate
   - Fallback a hardcoded

---

**Versione**: 2.0 - Completamente Funzionale
**Data**: 2026-02-04
**Stato**: ✅ Pronto per l'uso (input manuale coordinate)
