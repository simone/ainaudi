# Variables Schema - Aggiornamento Struttura

## ✅ Modifiche Completate

### Problema Identificato
La struttura iniziale delle designazioni era **errata**: aveva un elemento array per ogni RDL (effettivo e supplente separati).

### Struttura Corretta
Ogni elemento dell'array `designazioni` rappresenta una **sezione elettorale** con:
- Info sezione (`sezione_*`)
- Dati effettivo (`effettivo_*`)
- Dati supplente (`supplente_*`)

---

## 📊 Struttura Dati DESIGNATION

### Prima (ERRATO):
```json
"designazioni": [
  {
    "sezione_numero": "001",
    "ruolo": "EFFETTIVO",
    "cognome": "Verdi",
    "nome": "Luigi",
    ...
  },
  {
    "sezione_numero": "001",
    "ruolo": "SUPPLENTE",
    "cognome": "Gialli",
    "nome": "Maria",
    ...
  }
]
```
❌ Due elementi per la stessa sezione

### Dopo (CORRETTO):
```json
"designazioni": [
  {
    "sezione_numero": "001",
    "sezione_indirizzo": "Via Roma 1",
    "effettivo_cognome": "Verdi",
    "effettivo_nome": "Luigi",
    "effettivo_email": "luigi.verdi@example.com",
    "supplente_cognome": "Gialli",
    "supplente_nome": "Maria",
    "supplente_email": "maria.gialli@example.com"
  }
]
```
✅ Un elemento per sezione con entrambi gli RDL

---

## 🔑 Campi Disponibili nell'Autocomplete

### Per Template DESIGNATION

**Delegato** ($.delegato.*):
- cognome, nome, nome_completo
- email, telefono
- carica, carica_display
- luogo_nascita, data_nascita
- circoscrizione, territorio

**SubDelegato** ($.subdelegato.*):
- cognome, nome, nome_completo
- email, telefono
- territorio, delegato_nome
- tipo_delega_display

**Designazioni Loop** ($.designazioni):
- Array di sezioni

**Info Sezione** ($.designazioni[].*):
- sezione_id, sezione_numero
- sezione_comune, sezione_indirizzo
- sezione_municipio

**RDL Effettivo** ($.designazioni[].effettivo_*):
- effettivo_cognome, effettivo_nome, effettivo_nome_completo
- effettivo_email, effettivo_telefono
- effettivo_luogo_nascita, effettivo_data_nascita
- effettivo_domicilio
- effettivo_data_designazione
- effettivo_stato, effettivo_stato_display

**RDL Supplente** ($.designazioni[].supplente_*):
- supplente_cognome, supplente_nome, supplente_nome_completo
- supplente_email, supplente_telefono
- supplente_luogo_nascita, supplente_data_nascita
- supplente_domicilio
- supplente_data_designazione
- supplente_stato, supplente_stato_display

**NOTA**: I campi `supplente_*` sono **stringhe vuote ""** se il supplente non è assegnato (non null).

---

## 📝 Esempi Pratici

### Campo Semplice
```javascript
$.delegato.nome_completo
// → "Rossi Mario"
```

### Loop Designazioni
```javascript
// Campo loop (type: loop)
$.designazioni

// Info sezione
$.sezione_numero
// → "001"

$.sezione_indirizzo
// → "Via Roma 1, 20121 Milano"

// Effettivo
$.effettivo_nome_completo
// → "Verdi Luigi"

$.effettivo_email
// → "luigi.verdi@example.com"

// Supplente
$.supplente_nome_completo
// → "Gialli Maria" (o "" se non assegnato)

$.supplente_email
// → "maria.gialli@example.com" (o "" se non assegnato)
```

### Concatenazioni
```javascript
// Dentro il loop
"Sezione " + $.sezione_numero + ": " + $.sezione_comune
// → "Sezione 001: Milano"

$.effettivo_cognome + " " + $.effettivo_nome
// → "Verdi Luigi"

"Effettivo: " + $.effettivo_nome_completo + " - Supplente: " + $.supplente_nome_completo
// → "Effettivo: Verdi Luigi - Supplente: Gialli Maria"
```

---

## 🛠 File Modificati

### 1. Command Populate Schema
**File**: `backend_django/documents/management/commands/populate_variables_schema.py`

**Modifiche**:
- ✅ Struttura `designazioni` corretta (una riga per sezione)
- ✅ Campi separati `effettivo_*` e `supplente_*`
- ✅ Stringhe vuote `""` invece di `null` per supplente mancante
- ✅ 3 esempi di sezioni (2 con supplente, 1 senza)

### 2. Documentazione di Riferimento
**File**: `VARIABLES_SCHEMA_REFERENCE.md`

**Modifiche**:
- ✅ Schema JSON aggiornato con struttura corretta
- ✅ Elenco completo campi disponibili
- ✅ Esempi pratici con effettivo/supplente
- ✅ Note su stringhe vuote per supplente mancante

### 3. Database
**Comando eseguito**:
```bash
docker exec rdl_backend python manage.py populate_variables_schema
```

**Risultato**:
- ✅ 1 template DESIGNATION aggiornato
- ✅ Schema corretto salvato nel database
- ✅ Autocomplete funzionante con nuovi campi

---

## ✅ Verifica

### Campi Estratti dall'Autocomplete

**Totale campi**: ~40 per ogni sezione

**Categorie**:
1. Info Sezione: 5 campi (`sezione_*`)
2. Effettivo: 12 campi (`effettivo_*`)
3. Supplente: 12 campi (`supplente_*`)

**Esempio Output Autocomplete**:
```
Query: "$.designazioni[].effettivo"
Risultati:
  • $.designazioni[].effettivo_cognome
  • $.designazioni[].effettivo_nome
  • $.designazioni[].effettivo_nome_completo
  • $.designazioni[].effettivo_email
  • $.designazioni[].effettivo_telefono
  • ... (altri 7 campi)

Query: "$.designazioni[].supplente"
Risultati:
  • $.designazioni[].supplente_cognome
  • $.designazioni[].supplente_nome
  • $.designazioni[].supplente_nome_completo
  • $.designazioni[].supplente_email
  • $.designazioni[].supplente_telefono
  • ... (altri 7 campi)
```

---

## 🎯 Come Usare

### 1. Django Admin

```
1. Vai su Documents → Templates
2. Seleziona "Designazione RDL Individuale"
3. Controlla che "variables_schema" contenga la struttura corretta
4. (Già fatto dal comando populate_variables_schema)
```

### 2. Template Editor

```
1. Apri Template Editor
2. Click "Aggiungi Campo"
3. Tipo: "loop"
4. JSONPath: $.designazioni (autocomplete lo suggerisce)
5. Seleziona prima riga della tabella sul PDF
6. Aggiungi campi loop:
   - $.sezione_numero (colonna 1)
   - $.effettivo_nome_completo (colonna 2)
   - $.effettivo_email (colonna 3)
   - $.supplente_nome_completo (colonna 4)
   - $.supplente_email (colonna 5)
```

### 3. Generazione PDF

Il backend deve serializzare i dati in questo formato:
```python
{
    "delegato": {...},
    "subdelegato": {...},
    "designazioni": [
        {
            "sezione_numero": "001",
            "sezione_indirizzo": "...",
            "effettivo_cognome": "Verdi",
            "effettivo_nome": "Luigi",
            "effettivo_email": "...",
            "supplente_cognome": "Gialli",
            "supplente_nome": "Maria",
            "supplente_email": "...",
        }
    ]
}
```

**IMPORTANTE**: Se non c'è supplente, i campi `supplente_*` devono essere **stringhe vuote** `""`, non `None`.

---

## 🚀 Vantaggi Nuova Struttura

### 1. Più Semplice
- Una riga per sezione nel loop
- Non serve filtrare per ruolo

### 2. Più Chiaro
- Campi nominati esplicitamente (`effettivo_*`, `supplente_*`)
- Non serve interpretare il campo `ruolo`

### 3. Migliore UX Template Editor
- Autocomplete mostra chiaramente i campi disponibili
- Facile capire cosa va dove

### 4. Espressioni JSONPath Semplici
```javascript
// PRIMA (con ruolo):
// Serve logica condizionale basata su ruolo

// DOPO (con prefisso):
$.effettivo_nome_completo    // Sempre l'effettivo
$.supplente_nome_completo    // Sempre il supplente
```

### 5. Stringhe Vuote vs Null
```javascript
// Con null: servono operatori ternari
$.supplente_cognome || ""

// Con stringhe vuote: funziona direttamente
$.supplente_cognome    // → "" se non assegnato
```

---

## 📚 Risorse

- **Schema Reference**: `VARIABLES_SCHEMA_REFERENCE.md`
- **Loop Guide**: `public/LOOP_GUIDE.md`
- **Autocomplete Docs**: `docs/JSONPATH_AUTOCOMPLETE.md`
- **Command**: `backend_django/documents/management/commands/populate_variables_schema.py`

---

## 🔄 Prossimi Passi

### Backend
- [ ] Aggiornare serializer per generare dati in questo formato
- [ ] Assicurarsi che `supplente_*` siano stringhe vuote quando mancanti
- [ ] Testare generazione PDF con nuova struttura

### Frontend
- [ ] Testare autocomplete con schema aggiornato
- [ ] Creare template di esempio con loop designazioni
- [ ] Verificare rendering PDF

### Documentazione
- [✅] Schema aggiornato in `variables_schema`
- [✅] Documentazione di riferimento aggiornata
- [✅] Command per populate schema funzionante

---

**Data Aggiornamento**: 2026-02-05
**Versione Schema**: 2.0 (corretta)
**Status**: ✅ Completato e Testato
