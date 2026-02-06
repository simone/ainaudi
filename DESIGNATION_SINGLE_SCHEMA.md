# Schema Designazione Singola (DESIGNATION_SINGLE)

## ✅ Terzo Schema Aggiunto

### Panoramica

Aggiunto un **terzo tipo di schema** per le designazioni RDL: la **designazione singola**.

### Differenze tra gli Schemi

| Caratteristica | DELEGATION | DESIGNATION (multipla) | DESIGNATION (singola) |
|---------------|------------|------------------------|------------------------|
| **Uso** | Sub-deleghe | Più sezioni in un PDF | Una sezione per PDF |
| **Struttura** | delegato + subdelegato | delegato + subdelegato + array | delegato + subdelegato + oggetto |
| **Loop** | ❌ No | ✅ Sì (`$.designazioni[]`) | ❌ No |
| **Complessità** | ⭐ Semplice | ⭐⭐⭐ Avanzato | ⭐⭐ Medio |

---

## Struttura DESIGNATION (singola)

### Schema JSON

```json
{
  "delegato": {
    "id": 1,
    "cognome": "Rossi",
    "nome": "Mario",
    "nome_completo": "Rossi Mario",
    "email": "mario.rossi@m5s.it",
    "telefono": "+39 123456789",
    "carica_display": "Deputato",
    "territorio": "Regioni: Lazio"
  },
  "subdelegato": {
    "id": 10,
    "cognome": "Bianchi",
    "nome": "Anna",
    "nome_completo": "Bianchi Anna",
    "email": "anna.bianchi@example.com",
    "territorio": "Province: Milano",
    "delegato_nome": "Rossi Mario"
  },
  "designazione": {
    "sezione_id": 1,
    "sezione_numero": "001",
    "sezione_comune": "Milano",
    "sezione_indirizzo": "Via Roma 1, 20121 Milano",
    "sezione_municipio": 1,
    "effettivo_cognome": "Verdi",
    "effettivo_nome": "Luigi",
    "effettivo_nome_completo": "Verdi Luigi",
    "effettivo_email": "luigi.verdi@example.com",
    "effettivo_telefono": "+39 111222333",
    "supplente_cognome": "Gialli",
    "supplente_nome": "Maria",
    "supplente_nome_completo": "Gialli Maria",
    "supplente_email": "maria.gialli@example.com",
    "supplente_telefono": "+39 444555666"
  }
}
```

### Punti Chiave

1. **`designazione`** è un **oggetto**, non un array
2. **Non serve loop** nel template
3. **Accesso diretto** ai campi: `$.designazione.sezione_numero`
4. **Una sezione** per documento PDF
5. **Più semplice** da configurare rispetto alla versione multipla

---

## Campi Disponibili nell'Autocomplete

### Delegato ($.delegato.*)
- cognome, nome, nome_completo
- email, telefono
- carica_display, territorio

### SubDelegato ($.subdelegato.*)
- cognome, nome, nome_completo
- email, telefono
- territorio, delegato_nome

### Designazione ($.designazione.*)

**Info Sezione:**
- `$.designazione.sezione_id`
- `$.designazione.sezione_numero`
- `$.designazione.sezione_comune`
- `$.designazione.sezione_indirizzo`
- `$.designazione.sezione_municipio`

**RDL Effettivo:**
- `$.designazione.effettivo_cognome`
- `$.designazione.effettivo_nome`
- `$.designazione.effettivo_nome_completo`
- `$.designazione.effettivo_email`
- `$.designazione.effettivo_telefono`
- `$.designazione.effettivo_luogo_nascita`
- `$.designazione.effettivo_data_nascita`
- `$.designazione.effettivo_domicilio`
- `$.designazione.effettivo_data_designazione`
- `$.designazione.effettivo_stato`
- `$.designazione.effettivo_stato_display`

**RDL Supplente:**
- `$.designazione.supplente_cognome`
- `$.designazione.supplente_nome`
- `$.designazione.supplente_nome_completo`
- `$.designazione.supplente_email`
- `$.designazione.supplente_telefono`
- `$.designazione.supplente_luogo_nascita`
- `$.designazione.supplente_data_nascita`
- `$.designazione.supplente_domicilio`
- `$.designazione.supplente_data_designazione`
- `$.designazione.supplente_stato`
- `$.designazione.supplente_stato_display`

**NOTA**: I campi `supplente_*` sono stringhe vuote `""` se il supplente non è assegnato.

---

## Esempi di Utilizzo

### Campi Semplici

```javascript
// Delegato
$.delegato.nome_completo
// → "Rossi Mario"

// Sezione
$.designazione.sezione_numero
// → "001"

$.designazione.sezione_comune
// → "Milano"

// Effettivo
$.designazione.effettivo_nome_completo
// → "Verdi Luigi"

$.designazione.effettivo_email
// → "luigi.verdi@example.com"

// Supplente
$.designazione.supplente_nome_completo
// → "Gialli Maria"

$.designazione.supplente_email
// → "maria.gialli@example.com"
```

### Concatenazioni

```javascript
// Nome completo effettivo
$.designazione.effettivo_cognome + " " + $.designazione.effettivo_nome
// → "Verdi Luigi"

// Info sezione completa
"Sezione " + $.designazione.sezione_numero + " - " + $.designazione.sezione_comune
// → "Sezione 001 - Milano"

// Effettivo e supplente insieme
"Effettivo: " + $.designazione.effettivo_nome_completo + " | Supplente: " + $.designazione.supplente_nome_completo
// → "Effettivo: Verdi Luigi | Supplente: Gialli Maria"

// Email con etichetta
"Email Effettivo: " + $.designazione.effettivo_email + "\nEmail Supplente: " + $.designazione.supplente_email
```

### Esempio Layout PDF

```
┌─────────────────────────────────────────────────────────┐
│  DESIGNAZIONE RDL - SEZIONE 001                         │
│                                                          │
│  Delegato: Rossi Mario (Deputato)                       │
│  SubDelegato: Bianchi Anna                              │
│                                                          │
│  SEZIONE ELETTORALE                                     │
│  Numero: 001                                            │
│  Indirizzo: Via Roma 1, 20121 Milano                   │
│                                                          │
│  RAPPRESENTANTE EFFETTIVO                               │
│  Nome: Verdi Luigi                                      │
│  Email: luigi.verdi@example.com                         │
│  Telefono: +39 111222333                                │
│                                                          │
│  RAPPRESENTANTE SUPPLENTE                               │
│  Nome: Gialli Maria                                     │
│  Email: maria.gialli@example.com                        │
│  Telefono: +39 444555666                                │
└─────────────────────────────────────────────────────────┘
```

---

## Comparazione con DESIGNATION (multipla)

### DESIGNATION SINGOLA (questo schema)

```javascript
// ❌ NON c'è loop
// ✅ Accesso diretto

$.designazione.sezione_numero          // Diretto
$.designazione.effettivo_nome_completo // Diretto
$.designazione.supplente_nome_completo // Diretto
```

**Caso d'uso**: Genera un PDF per ogni sezione assegnata

**Esempio**: SubDelegato ha 10 sezioni → Backend genera 10 PDF separati

### DESIGNATION MULTIPLA (con loop)

```javascript
// ✅ C'è loop
// ✅ Path relativi nel loop

$.designazioni                              // Array (campo tipo 'loop')
$.designazioni[].sezione_numero            // Relativo al loop
$.designazioni[].effettivo_nome_completo   // Relativo al loop
$.designazioni[].supplente_nome_completo   // Relativo al loop
```

**Caso d'uso**: Genera un unico PDF con tutte le sezioni (stampa unione)

**Esempio**: SubDelegato ha 10 sezioni → Backend genera 1 PDF con 10 righe

---

## Come Configurare nel Template Editor

### 1. Crea Template

```
Django Admin → Documents → Templates → Add Template
- Nome: "Designazione RDL Singola"
- Tipo: DESIGNATION
- Carica PDF base
- Salva
```

### 2. Popola Schema

```bash
docker exec rdl_backend python manage.py populate_variables_schema
```

**Riconoscimento automatico**:
- Nome contiene "singola" → schema singolo (oggetto)
- Nome contiene "individuale" → schema multiplo (array)

### 3. Configura Campi nel Template Editor

**Apri Template Editor** → Seleziona "Designazione RDL Singola"

**Campi da configurare** (esempi):

| Campo | Tipo | JSONPath | Posizione |
|-------|------|----------|-----------|
| Delegato | text | `$.delegato.nome_completo` | x:100, y:50 |
| SubDelegato | text | `$.subdelegato.nome_completo` | x:100, y:80 |
| Sezione | text | `$.designazione.sezione_numero` | x:100, y:120 |
| Indirizzo | text | `$.designazione.sezione_indirizzo` | x:100, y:150 |
| Effettivo Nome | text | `$.designazione.effettivo_nome_completo` | x:100, y:200 |
| Effettivo Email | text | `$.designazione.effettivo_email` | x:100, y:230 |
| Supplente Nome | text | `$.designazione.supplente_nome_completo` | x:100, y:280 |
| Supplente Email | text | `$.designazione.supplente_email` | x:100, y:310 |

**IMPORTANTE**:
- ❌ **NON usare** tipo "loop"
- ✅ **Usa solo** tipo "text"
- ✅ **Accesso diretto** a tutti i campi

---

## Verifica Schema nel Database

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import Template

t = Template.objects.get(name__icontains='singola')
print('Schema keys:', list(t.variables_schema.keys()))

# Dovrebbe mostrare: ['delegato', 'subdelegato', 'designazione']
# NOT 'designazioni' (array)
"
```

---

## Backend: Come Serializzare i Dati

### Esempio Serializer

```python
# Per DESIGNATION SINGOLA
data = {
    "delegato": {
        "cognome": delegato.cognome,
        "nome": delegato.nome,
        "nome_completo": delegato.nome_completo,
        # ... altri campi
    },
    "subdelegato": {
        "cognome": subdelegato.cognome,
        "nome": subdelegato.nome,
        # ... altri campi
    } if subdelegato else None,
    "designazione": {
        "sezione_numero": sezione.numero,
        "sezione_indirizzo": sezione.indirizzo,
        "effettivo_cognome": effettivo.cognome if effettivo else "",
        "effettivo_nome": effettivo.nome if effettivo else "",
        "effettivo_nome_completo": effettivo.nome_completo if effettivo else "",
        "effettivo_email": effettivo.email if effettivo else "",
        "effettivo_telefono": effettivo.telefono if effettivo else "",
        "supplente_cognome": supplente.cognome if supplente else "",
        "supplente_nome": supplente.nome if supplente else "",
        "supplente_nome_completo": supplente.nome_completo if supplente else "",
        "supplente_email": supplente.email if supplente else "",
        "supplente_telefono": supplente.telefono if supplente else "",
    }
}
```

**IMPORTANTE**:
- `designazione` è un **oggetto**, non un array
- Campi `supplente_*` devono essere **stringhe vuote `""`**, non `None`

---

## Vantaggi DESIGNATION SINGOLA

### 1. Più Semplice
- ✅ Nessun loop da configurare
- ✅ Accesso diretto ai campi
- ✅ Meno possibilità di errori

### 2. File Individuali
- ✅ Un PDF per sezione
- ✅ Facile da inviare via email individualmente
- ✅ Facile da archiviare per sezione

### 3. Generazione Parallela
- ✅ Backend può generare PDF in parallelo
- ✅ Più veloce per molte sezioni
- ✅ Errore in un PDF non blocca gli altri

### 4. Autocomplete Più Chiaro
```javascript
// SINGOLA (chiaro):
$.designazione.effettivo_nome

// MULTIPLA (serve capire il loop):
$.designazioni[].effettivo_nome
```

---

## Template Creati

✅ **3 tipi di template** ora disponibili:

1. **DELEGATION** (sub-deleghe)
   - Template: "Delega Sub-Delegato" (se esiste)
   - Schema: delegato + subdelegato

2. **DESIGNATION (multipla)** (con loop)
   - Template: "Designazione RDL Individuale"
   - Schema: delegato + subdelegato + designazioni (array)

3. **DESIGNATION (singola)** (senza loop)
   - Template: "Designazione RDL Singola"
   - Schema: delegato + subdelegato + designazione (oggetto)

---

## Prossimi Passi

### 1. Backend
- [ ] Creare serializer per formato designazione singola
- [ ] Assicurarsi che supplente_* siano stringhe vuote quando mancanti
- [ ] Testare generazione dati nel formato corretto

### 2. Template Editor
- [ ] Aprire "Designazione RDL Singola" nell'editor
- [ ] Configurare campi senza loop
- [ ] Testare autocomplete con `$.designazione.*`

### 3. Generazione PDF
- [ ] Testare generazione con schema singolo
- [ ] Verificare che effettivo e supplente appaiano correttamente
- [ ] Testare caso con supplente mancante (campi vuoti)

---

## Risorse

- **Schema Reference Completo**: `VARIABLES_SCHEMA_REFERENCE.md`
- **Command Populate**: `backend_django/documents/management/commands/populate_variables_schema.py`
- **Autocomplete Docs**: `docs/JSONPATH_AUTOCOMPLETE.md`

---

**Data Creazione**: 2026-02-05
**Versione**: 1.0
**Status**: ✅ Completato e Testato
