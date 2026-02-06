# Guida Loop Multi-Pagina

## 📋 Problema

Quando un loop genera più righe di quelle che entrano in una pagina, il PDF si estende su **pagine multiple**.

**Problema**: La **prima pagina** ha spesso un **header/intestazione** che occupa spazio, quindi il loop inizia più in basso (es. Y=200). Le **pagine successive** non hanno header, quindi il loop può iniziare dall'alto (es. Y=50).

**Soluzione**: Configurare **due posizioni diverse** per il loop.

---

## 🎯 Soluzione: Due Configurazioni Loop

### Concetto

Crea **DUE campi loop** con:
- **Stesso JSONPath** (es. `$.designazioni`)
- **Stessi loop_fields** (stesse colonne)
- **Page diverso**:
  - `page=0`: Prima pagina (con header)
  - `page=1`: Template per pagine successive (senza header)
- **Y diverso**:
  - page=0: Y più basso (es. Y=200)
  - page=1: Y più alto (es. Y=50)

### Comportamento Backend

Il backend:
1. **Prima pagina**: Usa il loop con `page=0`
2. **Pagine 2, 3, 4, ...**: Usa il loop con `page=1` per tutte

---

## 📐 Esempio Pratico

### Scenario

**Template**: Designazione RDL con 30 sezioni
- **Prima pagina**: Header con logo, titolo (occupa fino a Y=180)
- **Righe prima pagina**: 6 righe (Y=200, altezza=20 → fino a Y=320)
- **Pagine successive**: Niente header, righe iniziano da Y=50
- **Righe per pagina successiva**: 13 righe

### Layout PDF

```
┌──────────────────────────────────────────────┐
│ PAGINA 1                                     │
│                                              │
│ ┌──────────────────────────────────────┐    │ Y=0
│ │ HEADER / LOGO                        │    │
│ │ Delegato: Mario Rossi                │    │
│ │ SubDelegato: Anna Bianchi            │    │
│ └──────────────────────────────────────┘    │ Y=180
│                                              │
│ ┌──────────────────────────────────────┐    │ Y=200 (LOOP page=0)
│ │ 001 │ Verdi Luigi    │ Gialli Maria  │    │
│ │ 002 │ Neri Paolo     │ Blu Carla     │    │
│ │ 003 │ Rossi Luca     │ -             │    │
│ │ 004 │ Bianchi Marco  │ Verdi Sara    │    │
│ │ 005 │ Gialli Pietro  │ Neri Marta    │    │
│ │ 006 │ Blu Andrea     │ Rossi Clara   │    │
│ └──────────────────────────────────────┘    │ Y=320
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ PAGINA 2                                     │
│                                              │
│ ┌──────────────────────────────────────┐    │ Y=50 (LOOP page=1)
│ │ 007 │ Verde Lucia    │ Bianco Tom    │    │
│ │ 008 │ Nero Silvia    │ Rosa Aldo     │    │
│ │ ...                                   │    │
│ │ 019 │ Azzurro Gino   │ Viola Lisa    │    │
│ └──────────────────────────────────────┘    │ Y=310
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ PAGINA 3                                     │
│                                              │
│ ┌──────────────────────────────────────┐    │ Y=50 (LOOP page=1)
│ │ 020 │ Grigio Sara    │ Arancio Max   │    │
│ │ ...                                   │    │
│ │ 030 │ Marrone Rita   │ Celeste Leo   │    │
│ └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

---

## 🛠 Configurazione nel Template Editor

### Step 1: Configura Loop Prima Pagina (page=0)

1. **Apri Template Editor**
2. **Visualizza pagina 1** del PDF
3. **Seleziona area** della prima riga (sotto il header)
   - X: 50
   - Y: 200 (dopo header)
   - Width: 500
   - Height: 20
4. **Compila form**:
   - **JSONPath**: `$.designazioni`
   - **Tipo**: `loop`
   - **Pagina**: `0` (prima pagina)
5. **Gestisci Colonne** (se implementato):
   - Sezione: `$.sezione_numero` → x_offset: 0
   - Effettivo: `$.effettivo_nome_completo` → x_offset: 80
   - Supplente: `$.supplente_nome_completo` → x_offset: 250
6. **Salva**

### Step 2: Configura Loop Pagine Successive (page=1)

1. **Visualizza pagina 2** del PDF (o immagina layout senza header)
2. **Seleziona area** della prima riga (dall'alto)
   - X: 50
   - Y: 50 (niente header, inizia subito)
   - Width: 500
   - Height: 20
3. **Compila form**:
   - **JSONPath**: `$.designazioni` (STESSO del page=0!)
   - **Tipo**: `loop`
   - **Pagina**: `1` (template pagine successive)
4. **Gestisci Colonne** (STESSE del page=0):
   - Sezione: `$.sezione_numero` → x_offset: 0
   - Effettivo: `$.effettivo_nome_completo` → x_offset: 80
   - Supplente: `$.supplente_nome_completo` → x_offset: 250
5. **Salva**

### Risultato

Avrai **2 configurazioni loop** nella tabella:

| JSONPath | Tipo | Pagina | Posizione | Note |
|----------|------|--------|-----------|------|
| `$.designazioni` | loop | 0 | x:50, y:200 | Prima pagina (con header) |
| `$.designazioni` | loop | 1 | x:50, y:50 | Pagine successive (senza header) |

---

## 📊 Struttura JSON nel Database

```json
{
  "field_mappings": [
    {
      "jsonpath": "$.designazioni",
      "type": "loop",
      "page": 0,
      "area": {
        "x": 50,
        "y": 200,
        "width": 500,
        "height": 20
      },
      "loop_fields": [
        {"jsonpath": "$.sezione_numero", "x_offset": 0},
        {"jsonpath": "$.effettivo_nome_completo", "x_offset": 80},
        {"jsonpath": "$.supplente_nome_completo", "x_offset": 250}
      ]
    },
    {
      "jsonpath": "$.designazioni",
      "type": "loop",
      "page": 1,
      "area": {
        "x": 50,
        "y": 50,
        "width": 500,
        "height": 20
      },
      "loop_fields": [
        {"jsonpath": "$.sezione_numero", "x_offset": 0},
        {"jsonpath": "$.effettivo_nome_completo", "x_offset": 80},
        {"jsonpath": "$.supplente_nome_completo", "x_offset": 250}
      ]
    }
  ],
  "loop_config": {
    "rows_first_page": 6,
    "rows_per_page": 13
  }
}
```

---

## 🔧 Backend: Come Usare le Due Configurazioni

### Pseudocodice Generazione PDF

```python
def generate_multi_page_loop(template, data):
    designazioni = data['designazioni']

    # Trova le due configurazioni loop
    loop_page_0 = find_loop(template.field_mappings, page=0)
    loop_page_1 = find_loop(template.field_mappings, page=1)

    rows_first_page = template.loop_config['rows_first_page']  # 6
    rows_per_page = template.loop_config['rows_per_page']      # 13

    # PRIMA PAGINA - usa loop_page_0
    pdf.add_page()
    for i in range(min(rows_first_page, len(designazioni))):
        render_loop_row(
            designazione=designazioni[i],
            y_start=loop_page_0['area']['y'],  # 200
            row_height=loop_page_0['area']['height'],  # 20
            row_index=i
        )

    # PAGINE SUCCESSIVE - usa loop_page_1
    remaining = designazioni[rows_first_page:]
    while remaining:
        pdf.add_page()
        page_rows = remaining[:rows_per_page]
        for i, designazione in enumerate(page_rows):
            render_loop_row(
                designazione=designazione,
                y_start=loop_page_1['area']['y'],  # 50
                row_height=loop_page_1['area']['height'],  # 20
                row_index=i
            )
        remaining = remaining[rows_per_page:]
```

### Logica Chiave

1. **Prima pagina**: Usa `page=0` → Y=200, 6 righe
2. **Pagine 2+**: Usa `page=1` → Y=50, 13 righe per pagina

---

## ✅ Vantaggi

### 1. Layout Ottimizzato
- ✅ Prima pagina con header professionale
- ✅ Pagine successive sfruttano tutto lo spazio
- ✅ Nessuno spazio sprecato

### 2. Flessibilità
- ✅ Y diverso per ogni pagina
- ✅ X e Width possono anche variare (es. margini diversi)
- ✅ loop_fields identici o diversi

### 3. Riuso Configurazione
- ✅ page=1 usato per TUTTE le pagine successive
- ✅ Non serve configurare page=2, page=3, ecc.

---

## 🚨 Errori Comuni

### ❌ Errore 1: Dimenticare page=1

**Sintomo**: Le pagine successive hanno il loop nella stessa posizione di page=0 (troppo in basso)

**Soluzione**: Crea il secondo loop con page=1 e Y diverso

### ❌ Errore 2: JSONPath Diversi

**Sintomo**: Alcune righe mancano o duplicati

**Problema**:
```json
// SBAGLIATO
{"jsonpath": "$.designazioni", "page": 0}
{"jsonpath": "$.designazioni_page2", "page": 1}  // ❌ JSONPath diverso!
```

**Corretto**:
```json
{"jsonpath": "$.designazioni", "page": 0}
{"jsonpath": "$.designazioni", "page": 1}  // ✅ Stesso JSONPath
```

### ❌ Errore 3: loop_fields Diversi

**Sintomo**: Colonne appaiono in posizioni diverse tra pagine

**Problema**: I loop_fields devono essere identici (stessi x_offset)

**Soluzione**: Copia esattamente i loop_fields da page=0 a page=1

### ❌ Errore 4: Altezza Diversa

**Sintomo**: Righe sovrapposte o spazi vuoti tra righe

**Problema**: `height` diverso tra page=0 e page=1

**Soluzione**: Usa la **stessa altezza** (es. 20px) per entrambe

---

## 🎨 Varianti Avanzate

### Variante 1: X Offset Diverso

Se la seconda pagina ha margini diversi:

```json
// page=0: margine sinistro 50
{"area": {"x": 50, "y": 200, ...}, "page": 0}

// page=1: margine sinistro 30 (più largo)
{"area": {"x": 30, "y": 50, ...}, "page": 1}
```

### Variante 2: Width Diverso

Se la seconda pagina usa tutto lo spazio:

```json
// page=0: larghezza 500 (con margini)
{"area": {"x": 50, "y": 200, "width": 500, ...}, "page": 0}

// page=1: larghezza 550 (più larga)
{"area": {"x": 30, "y": 50, "width": 550, ...}, "page": 1}
```

### Variante 3: Colonne Diverse

(Raro) Se le pagine successive hanno colonne diverse:

```json
// page=0: 3 colonne
{"loop_fields": [
  {"jsonpath": "$.col1", "x_offset": 0},
  {"jsonpath": "$.col2", "x_offset": 100},
  {"jsonpath": "$.col3", "x_offset": 200}
], "page": 0}

// page=1: 4 colonne (più spazio)
{"loop_fields": [
  {"jsonpath": "$.col1", "x_offset": 0},
  {"jsonpath": "$.col2", "x_offset": 80},
  {"jsonpath": "$.col3", "x_offset": 160},
  {"jsonpath": "$.col4", "x_offset": 240}
], "page": 1}
```

---

## 📚 Risorse

- **Template Editor**: Visual tool per configurare i loop
- **LOOP_GUIDE.md**: Guida base sui loop
- **VARIABLES_SCHEMA_REFERENCE.md**: Schemi JSONPath disponibili

---

## 🔍 Debug

### Verificare Configurazione

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import Template

t = Template.objects.get(name__icontains='individuale')

# Trova loop page=0 e page=1
loops = [m for m in t.field_mappings if m['type'] == 'loop']

for loop in loops:
    print(f'Loop page={loop[\"page\"]}: Y={loop[\"area\"][\"y\"]}')
"
```

**Output atteso**:
```
Loop page=0: Y=200
Loop page=1: Y=50
```

### Test Generazione

Genera un PDF con 30 designazioni e verifica:
- ✅ Pagina 1: 6 righe iniziano da Y=200
- ✅ Pagina 2: 13 righe iniziano da Y=50
- ✅ Pagina 3: 11 righe iniziano da Y=50

---

**Data Creazione**: 2026-02-05
**Versione**: 1.0
**Feature**: Loop Multi-Pagina con Posizioni Diverse
