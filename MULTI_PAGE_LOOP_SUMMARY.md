# Loop Multi-Pagina - Implementazione Completata ✅

## 🎯 Problema Risolto

**Problema**: Quando un loop genera più pagine, la **prima pagina** ha un header che occupa spazio (loop inizia da Y=200), mentre le **pagine successive** non hanno header (loop può iniziare da Y=50).

**Soluzione**: Supporto per **due configurazioni loop diverse** in base alla pagina.

---

## ✅ Implementazione

### 1. Template Editor Aggiornato

**File**: `src/TemplateEditor.js`

**Modifiche**:
- ✅ Alert info nel form loop spiega il multi-pagina
- ✅ Campo "Pagina" con help text aggiornato:
  - `page=0`: Prima pagina
  - `page=1`: Template per pagine successive
- ✅ Sezione help aggiornata con istruzioni loop multi-pagina

### 2. Documentazione Creata

**File**: `MULTI_PAGE_LOOP_GUIDE.md`

**Contenuto**:
- ✅ Spiegazione concetto con diagrammi
- ✅ Esempio pratico (30 sezioni, 6+13 righe)
- ✅ Step-by-step configurazione nel Template Editor
- ✅ Struttura JSON nel database
- ✅ Pseudocodice backend per generazione
- ✅ Troubleshooting errori comuni

**File**: `public/LOOP_GUIDE.md`

**Aggiornato con**:
- ✅ Sezione "Loop Multi-Pagina" con esempio configurazione
- ✅ Link alla guida dettagliata

---

## 🛠 Come Configurare

### Step 1: Loop Prima Pagina (page=0)

```
Template Editor → Aggiungi Campo
- JSONPath: $.designazioni
- Tipo: loop
- Pagina: 0
- Area: Y=200 (sotto header)
- Gestisci Colonne: aggiungi sezione_numero, effettivo_*, supplente_*
```

### Step 2: Loop Pagine Successive (page=1)

```
Template Editor → Aggiungi Campo
- JSONPath: $.designazioni (STESSO!)
- Tipo: loop
- Pagina: 1
- Area: Y=50 (dall'alto, senza header)
- Gestisci Colonne: STESSE del page=0
```

### Risultato Tabella

| JSONPath | Tipo | Pagina | Y | Note |
|----------|------|--------|---|------|
| `$.designazioni` | loop | 0 | 200 | Prima pagina (con header) |
| `$.designazioni` | loop | 1 | 50 | Pagine successive (senza header) |

---

## 📐 Esempio Layout PDF

### Pagina 1 (usa page=0)

```
┌────────────────────────────────┐
│ HEADER / LOGO                  │ Y=0
│ Delegato: Mario Rossi          │
│ SubDelegato: Anna Bianchi      │ Y=180
├────────────────────────────────┤
│ 001 │ Verdi L. │ Gialli M.     │ Y=200 (LOOP page=0)
│ 002 │ Neri P.  │ Blu C.        │
│ 003 │ Rossi L. │ -             │
│ 004 │ Bianchi M│ Verdi S.      │
│ 005 │ Gialli P │ Neri M.       │
│ 006 │ Blu A.   │ Rossi C.      │ Y=320
└────────────────────────────────┘
```

### Pagina 2+ (usa page=1)

```
┌────────────────────────────────┐
│ 007 │ Verde L. │ Bianco T.     │ Y=50 (LOOP page=1)
│ 008 │ Nero S.  │ Rosa A.       │
│ ...                             │
│ 019 │ Azzurro G│ Viola L.      │ Y=310
└────────────────────────────────┘
```

**Differenza chiave**: Y=200 vs Y=50

---

## 🔧 Backend: Logica Generazione

```python
# Trova le due configurazioni
loop_page_0 = [m for m in template.field_mappings if m['type']=='loop' and m['page']==0][0]
loop_page_1 = [m for m in template.field_mappings if m['type']=='loop' and m['page']==1][0]

# Prima pagina - usa page=0
for i in range(rows_first_page):
    render_row(y=loop_page_0['area']['y'] + i * row_height)

# Pagine successive - usa page=1
for remaining_rows:
    pdf.add_page()
    for i in range(rows_per_page):
        render_row(y=loop_page_1['area']['y'] + i * row_height)
```

---

## ✅ Vantaggi

### 1. Layout Professionale
- ✅ Prima pagina con header elegante
- ✅ Pagine successive sfruttano tutto lo spazio
- ✅ Nessuno spazio sprecato

### 2. Flessibilità Totale
- ✅ Y diverso per ogni tipo di pagina
- ✅ X e Width anche diversi se necessario
- ✅ loop_fields possono variare (raro)

### 3. Semplicità
- ✅ Solo page=0 e page=1 (non serve page=2, 3, 4...)
- ✅ page=1 riusato per TUTTE le pagine successive

---

## 🚨 Checklist Configurazione

Prima di salvare, verifica:

- [ ] **Due loop** configurati con stesso JSONPath
- [ ] **page=0** per primo loop (prima pagina)
- [ ] **page=1** per secondo loop (pagine successive)
- [ ] **Y diverso**: page=0 più basso, page=1 più alto
- [ ] **Height uguale** per entrambi (es. 20px)
- [ ] **loop_fields identici** (stessi x_offset)
- [ ] **loop_config** popolato:
  - `rows_first_page`: quante righe in page=0
  - `rows_per_page`: quante righe in page=1

---

## 🎨 UI Aggiornata

### Alert Info nel Form Loop

Quando l'utente seleziona tipo "loop", vede:

```
📋 Come funziona il Loop

1. Seleziona solo la PRIMA riga della tabella sul PDF
2. Le righe successive verranno generate automaticamente
3. Ogni riga avrà la stessa altezza della prima
4. Il sistema trasla automaticamente ogni riga verso il basso

Esempio: Se la prima riga è a Y=150 con altezza 20px,
la seconda sarà a Y=170, la terza a Y=190, ecc.

⚠️ Loop Multi-Pagina
Se il loop va su più pagine con posizioni diverse:
1. Prima pagina (page=0): Seleziona riga con header (es. Y=200)
2. Seconda pagina+ (page=1): Crea un secondo loop con stesso
   JSONPath ma Y diverso (es. Y=50)
```

### Campo Pagina con Help

```
Pagina: [___]

0 = Prima pagina
1 = Template per pagine successive (per loop multi-pagina)
```

### Help Section

```
🔁 Loop: Come Selezionare

Per i campi di tipo loop (tabelle con più righe):
1. Seleziona solo la prima riga della tabella
2. L'altezza selezionata definisce l'altezza di ogni riga
3. Le righe successive saranno automaticamente generate traslando verticalmente
4. Esempio: Prima riga Y=150 h=20 → Seconda riga Y=170 → Terza Y=190...

Loop Multi-Pagina (2+ pagine):
1. Prima pagina: Crea loop con page=0 (es. Y=200 se c'è header)
2. Pagine successive: Crea secondo loop con stesso JSONPath, page=1,
   Y diverso (es. Y=50 senza header)
3. Il sistema userà page=0 per la prima pagina, page=1 per tutte le altre
```

---

## 📚 Documentazione

| File | Descrizione |
|------|-------------|
| `MULTI_PAGE_LOOP_GUIDE.md` | Guida completa con esempi e troubleshooting |
| `public/LOOP_GUIDE.md` | Guida base loop (aggiornata con sezione multi-pagina) |
| `src/TemplateEditor.js` | UI aggiornata con alert e help text |

---

## 🧪 Testing

### Test Case 1: 30 Designazioni

**Configurazione**:
- page=0: Y=200, 6 righe
- page=1: Y=50, 13 righe per pagina

**Output atteso**:
- Pagina 1: 6 righe (001-006) da Y=200
- Pagina 2: 13 righe (007-019) da Y=50
- Pagina 3: 11 righe (020-030) da Y=50

### Test Case 2: 5 Designazioni (no overflow)

**Configurazione**: Stessa di sopra

**Output atteso**:
- Pagina 1: 5 righe (001-005) da Y=200
- Nessuna pagina 2 (tutto entra in pagina 1)

### Test Case 3: Margini Diversi

**Configurazione**:
- page=0: X=60, Y=200 (margini standard)
- page=1: X=40, Y=50 (margini ridotti)

**Output atteso**:
- Pagina 1: loop inizia da X=60
- Pagine 2+: loop inizia da X=40

---

## 🚀 Prossimi Passi

### Backend
1. [ ] Implementare logica per selezionare page=0 vs page=1
2. [ ] Testare generazione con entrambe le configurazioni
3. [ ] Verificare paginazione corretta

### Frontend
1. [✅] UI aggiornata con alert e help
2. [✅] Documentazione completa
3. [ ] Testare configurazione in Template Editor

### Testing
1. [ ] Creare template con loop multi-pagina
2. [ ] Generare PDF con 30 sezioni
3. [ ] Verificare Y corretto su ogni pagina

---

## 💡 Note Implementative

### Perché Solo page=0 e page=1?

**Non serve** page=2, page=3, ecc. perché:
- page=0 è **unico** (prima pagina con header)
- page=1 è un **template** riusato per TUTTE le pagine successive

Questo semplifica configurazione e codice backend.

### Alternativa Non Implementata

Un approccio alternativo sarebbe stato:
```json
{
  "area": {"x": 50, "y": 200, ...},
  "second_page_area": {"x": 50, "y": 50, ...}  // Campo singolo
}
```

**Motivo per non usarlo**:
- ❌ Meno flessibile (solo Y diverso)
- ❌ Difficile aggiungere altre differenze (X, Width)
- ✅ Due campi loop separati è più esplicito e chiaro

---

**Data Implementazione**: 2026-02-05
**Feature**: Loop Multi-Pagina con Posizioni Diverse
**Status**: ✅ UI Completa, Backend da Implementare
