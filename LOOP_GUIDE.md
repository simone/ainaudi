# Guida Loop - Stampa Unione PDF

## 📋 Indice

1. [Cosa sono i Loop](#cosa-sono-i-loop)
2. [Espressioni JSONPath](#espressioni-jsonpath)
3. [Configurare un Loop](#configurare-un-loop)
4. [Merge Mode](#merge-mode)
5. [Esempi Pratici](#esempi-pratici)
6. [Troubleshooting](#troubleshooting)

---

## 🔄 Cosa sono i Loop

I **loop** permettono di generare automaticamente sezioni ripetute in un PDF.

### Caso d'Uso: Designazioni RDL

Un Delegato può avere **multiple designazioni** (una per sezione elettorale):

```
Delegato: Mario Rossi
├── Designazione 1: Sezione 001 - Effettivo: Luigi Verdi
├── Designazione 2: Sezione 002 - Effettivo: Anna Bianchi
└── Designazione 3: Sezione 003 - Effettivo: Paolo Neri
```

Con i **loop**, puoi creare automaticamente una riga per ogni designazione.

---

## 🧭 Espressioni JSONPath

### 1. JSONPath Semplice

Estrae un singolo campo dal JSON:

```javascript
// Dati
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario"
  }
}

// JSONPath
$.delegato.cognome
// Risultato: "Rossi"
```

### 2. JSONPath Concatenato

Concatena più campi con `+`:

```javascript
// JSONPath
$.delegato.cognome + " " + $.delegato.nome
// Risultato: "Rossi Mario"
```

### 3. JSONPath con Literal

Aggiungi testo statico con quote:

```javascript
// JSONPath
$.comune + " (" + $.provincia + ")"
// Risultato: "Roma (RM)"

// Oppure
"Sezione " + $.sezione.numero
// Risultato: "Sezione 001"
```

### 4. Loop Array

Estrae un array da iterare:

```javascript
// Dati
{
  "designazioni": [
    {"sezione": "001", "effettivo": "Verdi Luigi"},
    {"sezione": "002", "effettivo": "Bianchi Anna"}
  ]
}

// JSONPath Loop
$.designazioni
// Risultato: Array con 2 elementi
```

---

## ⚙️ Configurare un Loop

### Workflow Completo

#### 1. **Upload Template PDF**
- Usa un PDF con spazio per righe ripetute
- Esempio: template con tabella vuota

#### 2. **Definisci Area Loop**
Nel Template Editor:

1. **Apri template** → Click "Configura"
2. **Trascina area** sul PDF per definire la prima riga
3. **Compila form**:
   - **JSONPath**: `$.designazioni` (array da iterare)
   - **Tipo**: `loop`
   - **Coordinate**: Auto-popolate dalla selezione

#### 3. **Aggiungi Campi Loop**

Per ogni colonna della tabella, aggiungi un campo:

**Esempio: Tabella Designazioni**

| Campo | JSONPath | Posizione |
|-------|----------|-----------|
| Sezione | `$.sezione` | x:50, y:100 |
| Effettivo | `$.effettivo_cognome + " " + $.effettivo_nome` | x:150, y:100 |
| Email | `$.effettivo_email` | x:350, y:100 |

**Nota**: JSONPath nei loop è **relativo all'elemento corrente** dell'array!

#### 4. **Configura Paginazione**

Se la lista è lunga, configura la paginazione:

**Merge Mode**: `MULTI_PAGE_LOOP`

**Loop Config**:
```json
{
  "rows_first_page": 6,
  "rows_per_page": 13,
  "data_source": "$.designazioni"
}
```

- **rows_first_page**: Quante righe nella prima pagina (es: 6 se c'è header)
- **rows_per_page**: Quante righe nelle pagine successive (es: 13 se no header)
- **data_source**: JSONPath dell'array da iterare

---

## 📑 Merge Mode

### 1. `SINGLE_DOC_PER_RECORD`

**Un PDF per ogni record principale.**

**Esempio**: Un PDF per ogni Delegato (con tutte le sue designazioni).

```
Input: 3 Delegati con N designazioni ciascuno
Output: 3 PDF separati
```

**Quando usare**:
- Email individuali
- Stampa separata per ogni persona
- Archiviazione per delegato

### 2. `MULTI_PAGE_LOOP`

**Un unico PDF multi-pagina con tutti i record.**

**Esempio**: Un PDF con tutti i Delegati (uno sotto l'altro).

```
Input: 20 Delegati
Output: 1 PDF con 3 pagine (6+13+1 righe)
```

**Quando usare**:
- Report completo
- Stampa centralizzata
- Archivio unico

---

## 💡 Esempi Pratici

### Esempio 1: Designazioni RDL (Individuale)

**Template**: `individuale.pdf`
**Merge Mode**: `SINGLE_DOC_PER_RECORD`

#### Dati Input
```json
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario",
    "email": "mario.rossi@m5s.it"
  },
  "designazioni": [
    {
      "sezione": "001",
      "indirizzo": "Via Roma 1",
      "effettivo_cognome": "Verdi",
      "effettivo_nome": "Luigi",
      "effettivo_email": "luigi.verdi@example.com",
      "supplente_cognome": "Bianchi",
      "supplente_nome": "Anna",
      "supplente_email": "anna.bianchi@example.com"
    },
    {
      "sezione": "002",
      "indirizzo": "Via Milano 5",
      "effettivo_cognome": "Neri",
      "effettivo_nome": "Paolo",
      "effettivo_email": "paolo.neri@example.com",
      "supplente_cognome": null,
      "supplente_nome": null,
      "supplente_email": null
    }
  ]
}
```

#### Field Mappings

**Campi Singoli (Delegato)**:
```json
[
  {
    "jsonpath": "$.delegato.cognome + ' ' + $.delegato.nome",
    "type": "text",
    "area": {"x": 100, "y": 50, "width": 200, "height": 20},
    "page": 0
  },
  {
    "jsonpath": "$.delegato.email",
    "type": "text",
    "area": {"x": 100, "y": 80, "width": 250, "height": 20},
    "page": 0
  }
]
```

**Campi Loop (Designazioni)**:
```json
[
  {
    "jsonpath": "$.designazioni",
    "type": "loop",
    "area": {"x": 50, "y": 150, "width": 500, "height": 15},
    "page": 0,
    "loop_fields": [
      {
        "jsonpath": "$.sezione",
        "x_offset": 0
      },
      {
        "jsonpath": "$.indirizzo",
        "x_offset": 80
      },
      {
        "jsonpath": "$.effettivo_cognome + ' ' + $.effettivo_nome",
        "x_offset": 250
      },
      {
        "jsonpath": "$.supplente_cognome + ' ' + $.supplente_nome",
        "x_offset": 400
      }
    ]
  }
]
```

#### Risultato
```
┌─────────────────────────────────────────┐
│ Delegato: Mario Rossi                   │
│ Email: mario.rossi@m5s.it               │
│                                          │
│ Designazioni:                           │
│ ┌────────────────────────────────────┐  │
│ │ 001 │ Via Roma 1 │ Verdi Luigi │   │  │
│ │     │            │ Bianchi Anna│   │  │
│ ├────────────────────────────────────┤  │
│ │ 002 │ Via Milano │ Neri Paolo  │   │  │
│ │     │         5  │             │   │  │
│ └────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

### Esempio 2: Report Riepilogativo (Multi-page)

**Template**: `riepilogativo.pdf`
**Merge Mode**: `MULTI_PAGE_LOOP`

#### Loop Config
```json
{
  "rows_first_page": 6,
  "rows_per_page": 13,
  "data_source": "$.tutti_delegati"
}
```

#### Dati Input
```json
{
  "tutti_delegati": [
    {
      "cognome": "Rossi",
      "nome": "Mario",
      "comune": "Roma",
      "num_designazioni": 5
    },
    {
      "cognome": "Bianchi",
      "nome": "Anna",
      "comune": "Milano",
      "num_designazioni": 3
    }
    // ... altri 18 delegati
  ]
}
```

#### Field Mapping Loop
```json
{
  "jsonpath": "$.tutti_delegati",
  "type": "loop",
  "area": {"x": 50, "y": 100, "width": 500, "height": 20},
  "page": 0,
  "loop_fields": [
    {
      "jsonpath": "$.cognome + ' ' + $.nome",
      "x_offset": 0
    },
    {
      "jsonpath": "$.comune",
      "x_offset": 200
    },
    {
      "jsonpath": "$.num_designazioni",
      "x_offset": 350
    }
  ]
}
```

#### Risultato
```
Pagina 1: Righe 1-6
┌──────────────────────────────────┐
│ Nome         │ Comune  │ N.Des. │
├──────────────────────────────────┤
│ Rossi Mario  │ Roma    │ 5      │
│ Bianchi Anna │ Milano  │ 3      │
│ ...                              │
│ (6 righe totali)                 │
└──────────────────────────────────┘

Pagina 2: Righe 7-19
┌──────────────────────────────────┐
│ Verdi Luigi  │ Torino  │ 2      │
│ ...                              │
│ (13 righe totali)                │
└──────────────────────────────────┘

Pagina 3: Riga 20
┌──────────────────────────────────┐
│ Neri Paolo   │ Napoli  │ 4      │
└──────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### ❌ "Campo vuoto nel PDF"

**Causa**: JSONPath non trova il dato.

**Soluzioni**:
1. Verifica JSONPath nel browser console:
   ```javascript
   data = {delegato: {cognome: "Rossi"}};
   // Test
   data.delegato.cognome; // "Rossi"
   ```

2. Controlla maiuscole/minuscole:
   - ✅ `$.delegato.cognome`
   - ❌ `$.Delegato.Cognome`

3. Verifica che il campo esista:
   ```javascript
   // Usa fallback per campi opzionali
   $.supplente_cognome || ""
   ```

---

### ❌ "Loop non genera righe"

**Causa**: JSONPath loop non restituisce array.

**Soluzioni**:
1. Verifica che `data_source` punti ad array:
   ```json
   {
     "designazioni": [...]  // ✅ Array
   }
   ```

2. Controlla tipo campo:
   - Loop deve avere `"type": "loop"`

3. Verifica `loop_config`:
   ```json
   {
     "data_source": "$.designazioni",  // Deve esistere!
     "rows_first_page": 6
   }
   ```

---

### ❌ "Righe sovrapposte"

**Causa**: `height` o `y_offset` sbagliati.

**Soluzioni**:
1. Aumenta `height` nel loop area:
   ```json
   "area": {"height": 25}  // Era 15, troppo piccolo
   ```

2. Configura `y_spacing` (se supportato):
   ```json
   "loop_config": {
     "y_spacing": 20  // Spazio tra righe
   }
   ```

---

### ❌ "Testo troncato"

**Causa**: `width` troppo piccolo.

**Soluzioni**:
1. Aumenta `width`:
   ```json
   "area": {"width": 300}  // Era 150
   ```

2. Usa font più piccolo (backend):
   ```python
   page.insert_text(..., fontsize=8)  # Era 10
   ```

---

## 📚 Best Practices

### 1. **Testa con Dati Reali**
Prima di generare centinaia di PDF, testa con 2-3 record.

### 2. **Usa Nomi Descrittivi**
```json
// ❌ Sbagliato
"jsonpath": "$.d.c"

// ✅ Corretto
"jsonpath": "$.delegato.cognome"
```

### 3. **Documenta Loop Config**
Aggiungi commenti nel template:
```json
{
  "loop_config": {
    "rows_first_page": 6,  // Sotto header
    "rows_per_page": 13    // Senza header
  }
}
```

### 4. **Gestisci Campi Opzionali**
Usa espressioni con fallback:
```javascript
// Se supplente può essere null
$.supplente_cognome + " " + $.supplente_nome
// Diventa: "null null" se mancante

// Meglio (backend deve supportare):
$.supplente_cognome || "-"
```

### 5. **Preview Prima di Conferma**
Usa workflow preview → conferma per evitare errori.

---

## 🎓 Risorse

- **Template Editor**: Delegati → Template Designazioni
- **Test Dati**: `backend_django/documents/tests/fixtures/`
- **Codice JSONPath**: `backend_django/documents/jsonpath_resolver.py`
- **Worker PDF**: `pdf/generate_adapter.py`

---

**Versione**: 1.0
**Ultima modifica**: 2026-02-05
**Autore**: Sistema RDL AInaudi
