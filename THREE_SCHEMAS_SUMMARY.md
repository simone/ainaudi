# Riepilogo 3 Schemi Template

## ✅ Implementazione Completa

Sono stati configurati **3 schemi** per i template PDF, ognuno con scopo e complessità diversi.

---

## 📊 Tabella Comparativa

| # | Tipo | Nome Template | Struttura | Loop | Autocomplete Preview | Complessità |
|---|------|--------------|-----------|------|----------------------|-------------|
| **1** | DELEGATION | Delega Sub-Delegato | `delegato` + `subdelegato` | ❌ No | `$.delegato.*`<br/>`$.subdelegato.*` | ⭐ Semplice |
| **2** | DESIGNATION (singola) | Designazione RDL Singola | `delegato` + `subdelegato` + `designazione` (oggetto) | ❌ No | `$.designazione.sezione_*`<br/>`$.designazione.effettivo_*`<br/>`$.designazione.supplente_*` | ⭐⭐ Medio |
| **3** | DESIGNATION (multipla) | Designazione RDL Individuale | `delegato` + `subdelegato` + `designazioni` (array) | ✅ Sì | `$.designazioni[]`<br/>`$.designazioni[].sezione_*`<br/>`$.designazioni[].effettivo_*`<br/>`$.designazioni[].supplente_*` | ⭐⭐⭐ Avanzato |

---

## 🎯 Quando Usare Quale

### 1️⃣ DELEGATION - Sub-Deleghe

**Caso d'uso**: Documenti di delega da Delegato a SubDelegato

**Struttura**:
```json
{
  "delegato": {
    "nome_completo": "Rossi Mario",
    "carica_display": "Deputato",
    "email": "mario.rossi@m5s.it"
  },
  "subdelegato": {
    "nome_completo": "Bianchi Anna",
    "territorio": "Milano e provincia",
    "email": "anna.bianchi@example.com"
  }
}
```

**JSONPath**:
```javascript
$.delegato.nome_completo
$.subdelegato.nome_completo
$.subdelegato.territorio
```

**Esempio Output**: 1 PDF per sub-delega

---

### 2️⃣ DESIGNATION SINGOLA - Una Sezione per PDF

**Caso d'uso**: Generare un documento separato per ogni sezione elettorale

**Struttura**:
```json
{
  "delegato": {...},
  "subdelegato": {...},
  "designazione": {
    "sezione_numero": "001",
    "sezione_indirizzo": "Via Roma 1, Milano",
    "effettivo_nome_completo": "Verdi Luigi",
    "effettivo_email": "luigi.verdi@example.com",
    "supplente_nome_completo": "Gialli Maria",
    "supplente_email": "maria.gialli@example.com"
  }
}
```

**JSONPath** (accesso diretto, NO loop):
```javascript
$.designazione.sezione_numero
$.designazione.effettivo_nome_completo
$.designazione.supplente_nome_completo
```

**Esempio Output**:
- SubDelegato con 10 sezioni → 10 PDF separati
- Facile da inviare via email individualmente

**✅ Vantaggi**:
- Semplice da configurare (no loop)
- File individuali per sezione
- Generazione parallela possibile

---

### 3️⃣ DESIGNATION MULTIPLA - Tutte le Sezioni in un PDF

**Caso d'uso**: Generare un unico documento con tabella di tutte le sezioni (stampa unione)

**Struttura**:
```json
{
  "delegato": {...},
  "subdelegato": {...},
  "designazioni": [
    {
      "sezione_numero": "001",
      "effettivo_nome_completo": "Verdi Luigi",
      "supplente_nome_completo": "Gialli Maria"
    },
    {
      "sezione_numero": "002",
      "effettivo_nome_completo": "Neri Paolo",
      "supplente_nome_completo": "Blu Carla"
    }
  ]
}
```

**JSONPath** (con loop):
```javascript
// Campo loop (type: 'loop')
$.designazioni

// Campi nel loop (path relativi)
$.sezione_numero
$.effettivo_nome_completo
$.supplente_nome_completo
```

**Esempio Output**:
- SubDelegato con 10 sezioni → 1 PDF con tabella di 10 righe
- Tutte le designazioni visibili in un colpo d'occhio

**✅ Vantaggi**:
- Un unico documento riepilogativo
- Stampa unione (mail merge style)
- Facile da archiviare come report completo

---

## 🔍 Differenze Chiave

### Accesso ai Dati

| Tipo | Designazioni | Accesso Sezione | Accesso Effettivo |
|------|--------------|-----------------|-------------------|
| **SINGOLA** | Oggetto | `$.designazione.sezione_numero` | `$.designazione.effettivo_nome` |
| **MULTIPLA** | Array | `$.designazioni[].sezione_numero` | `$.designazioni[].effettivo_nome` |

### Configurazione Template Editor

| Tipo | Loop Required? | Campi da Configurare |
|------|---------------|----------------------|
| **DELEGATION** | ❌ No | Solo text fields |
| **SINGOLA** | ❌ No | Solo text fields |
| **MULTIPLA** | ✅ Sì | 1 campo loop + N loop_fields |

### Output PDF

| Tipo | Input | Output |
|------|-------|--------|
| **DELEGATION** | 1 sub-delega | 1 PDF |
| **SINGOLA** | N sezioni | N PDF (uno per sezione) |
| **MULTIPLA** | N sezioni | 1 PDF (con N righe) |

---

## 📁 File Creati nel Database

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import Template
for t in Template.objects.all():
    print(f'{t.name} ({t.template_type})')
"
```

**Output**:
```
Designazione RDL Individuale (DESIGNATION)  → Schema MULTIPLA
Designazione RDL Singola (DESIGNATION)      → Schema SINGOLA
```

---

## 🚀 Come Popolare gli Schemi

### Command Automatico

```bash
docker exec rdl_backend python manage.py populate_variables_schema
```

**Riconoscimento automatico**:
- Nome contiene "**individuale**" → schema **multipla** (con array)
- Nome contiene "**singola**" → schema **singola** (con oggetto)
- Tipo DELEGATION → schema delega

### Verifica Schema Popolato

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import Template

for t in Template.objects.filter(template_type='DESIGNATION'):
    schema = t.variables_schema
    has_array = 'designazioni' in schema  # Array
    has_object = 'designazione' in schema  # Oggetto

    tipo = 'MULTIPLA (array)' if has_array else 'SINGOLA (oggetto)' if has_object else 'VUOTO'
    print(f'{t.name}: {tipo}')
"
```

---

## 💡 Esempi Pratici

### Scenario 1: SubDelegato con 5 Sezioni

**Opzione A - SINGOLA** (5 PDF separati):
```
sezione_001_verdi_luigi.pdf
sezione_002_neri_paolo.pdf
sezione_003_rossi_luca.pdf
sezione_004_bianchi_marco.pdf
sezione_005_gialli_sara.pdf
```
✅ Facile inviare individualmente via email

**Opzione B - MULTIPLA** (1 PDF con tabella):
```
designazioni_bianchi_anna.pdf
  ┌─────────────────────────────────────┐
  │ Sezione │ Effettivo    │ Supplente  │
  ├─────────────────────────────────────┤
  │ 001     │ Verdi Luigi  │ Rossi A.   │
  │ 002     │ Neri Paolo   │ Blu C.     │
  │ 003     │ Rossi Luca   │ -          │
  │ 004     │ Bianchi M.   │ Verdi S.   │
  │ 005     │ Gialli Sara  │ Neri M.    │
  └─────────────────────────────────────┘
```
✅ Comodo per avere panoramica completa

---

## 🎨 Template Editor - Come Configurare

### DELEGATION (Semplice)

1. Apri Template Editor
2. Aggiungi campi tipo "text":
   - `$.delegato.nome_completo` → x:100, y:50
   - `$.subdelegato.nome_completo` → x:100, y:100
   - `$.subdelegato.territorio` → x:100, y:150
3. Salva

### DESIGNATION SINGOLA (Medio)

1. Apri Template Editor
2. Aggiungi campi tipo "text":
   - `$.designazione.sezione_numero` → x:100, y:120
   - `$.designazione.effettivo_nome_completo` → x:100, y:200
   - `$.designazione.effettivo_email` → x:100, y:230
   - `$.designazione.supplente_nome_completo` → x:100, y:280
   - `$.designazione.supplente_email` → x:100, y:310
3. Salva

### DESIGNATION MULTIPLA (Avanzato)

1. Apri Template Editor
2. Aggiungi campo tipo **"loop"**:
   - JSONPath: `$.designazioni`
   - Seleziona **solo prima riga** tabella
3. Gestisci colonne loop:
   - Click "Gestisci Colonne"
   - Aggiungi: `$.sezione_numero` → x_offset: 0
   - Aggiungi: `$.effettivo_nome_completo` → x_offset: 80
   - Aggiungi: `$.supplente_nome_completo` → x_offset: 250
4. Salva

---

## 📚 Documentazione

| Documento | Contenuto |
|-----------|-----------|
| `VARIABLES_SCHEMA_REFERENCE.md` | Schemi JSON completi per tutti e 3 i tipi |
| `DESIGNATION_SINGLE_SCHEMA.md` | Guida dettagliata per schema singolo |
| `VARIABLES_SCHEMA_UPDATE.md` | Storia modifiche struttura designazioni |
| `JSONPATH_AUTOCOMPLETE.md` | Documentazione autocomplete |
| `LOOP_GUIDE.md` | Guida configurazione loop |

---

## ✅ Checklist Implementazione

- [✅] **Schema DELEGATION** creato e documentato
- [✅] **Schema DESIGNATION SINGOLA** creato e documentato
- [✅] **Schema DESIGNATION MULTIPLA** creato e documentato
- [✅] **Command populate_variables_schema** aggiornato
- [✅] **Autocomplete** funziona con tutti e 3 gli schemi
- [✅] **Template "Designazione RDL Singola"** creato nel DB
- [✅] **Template "Designazione RDL Individuale"** aggiornato nel DB
- [✅] **Documentazione completa** per tutti e 3 i tipi
- [✅] **Verifica schemi** eseguita con successo

---

## 🎯 Prossimi Passi

### Backend
1. Creare serializer per formato designazione singola
2. Decidere quando usare singola vs multipla
3. Assicurarsi che `supplente_*` siano stringhe vuote quando mancanti

### Template Editor
1. Configurare "Designazione RDL Singola" con campi text
2. Testare autocomplete con `$.designazione.*`
3. Configurare "Designazione RDL Individuale" con loop

### Testing
1. Generare PDF con schema singolo
2. Generare PDF con schema multiplo
3. Verificare supplente mancante (campi vuoti)

---

**Data Completamento**: 2026-02-05
**Schemi Implementati**: 3/3 ✅
**Status**: Pronto per configurazione template
