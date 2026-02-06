# Variables Schema Reference

Questo documento contiene gli schemi JSON da utilizzare nel campo `variables_schema` dei template PDF.

Gli schemi sono basati sui **serializer Django reali** e contengono tutti i campi disponibili per l'autocomplete JSONPath.

---

## Template Type: DELEGATION (Sub-Delega)

**Usa questo schema per template di tipo DELEGATION.**

Contiene:
- `delegato`: Dati del Delegato di Lista
- `subdelegato`: Dati del Sub-Delegato

### Schema JSON da copiare:

```json
{
  "delegato": {
    "id": 1,
    "cognome": "Rossi",
    "nome": "Mario",
    "nome_completo": "Rossi Mario",
    "luogo_nascita": "Roma",
    "data_nascita": "1980-01-15",
    "carica": "DEPUTATO",
    "carica_display": "Deputato",
    "circoscrizione": "Lazio 1",
    "data_nomina": "2024-01-01",
    "email": "mario.rossi@m5s.it",
    "telefono": "+39 123456789",
    "territorio": "Regioni: Lazio | Province: Roma, Frosinone",
    "n_sub_deleghe": 5
  },
  "subdelegato": {
    "id": 10,
    "cognome": "Bianchi",
    "nome": "Anna",
    "nome_completo": "Bianchi Anna",
    "luogo_nascita": "Milano",
    "data_nascita": "1985-06-15",
    "domicilio": "Via Roma 1, 20121 Milano (MI)",
    "tipo_documento": "Carta d'identità",
    "numero_documento": "AB123456",
    "email": "anna.bianchi@example.com",
    "telefono": "+39 987654321",
    "data_delega": "2024-02-01",
    "firma_autenticata": true,
    "autenticatore": "Notaio Giovanni Verdi",
    "tipo_delega": "FIRMA_AUTENTICATA",
    "tipo_delega_display": "Firma Autenticata",
    "puo_designare_direttamente": true,
    "regioni_nomi": ["Lombardia"],
    "province_nomi": ["Milano"],
    "comuni_nomi": ["Milano", "Monza"],
    "municipi": [1, 2, 3],
    "territorio": "Province: Milano | Comuni: Milano, Monza | Roma - Municipi: 1, 2, 3",
    "delegato_nome": "Rossi Mario",
    "delegato_carica": "Deputato",
    "n_designazioni": 15,
    "n_bozze": 2
  }
}
```

### Campi Disponibili per Autocomplete:

**Delegato** ($.delegato.*):
- `$.delegato.id` - ID univoco
- `$.delegato.cognome` - Cognome (es: "Rossi")
- `$.delegato.nome` - Nome (es: "Mario")
- `$.delegato.nome_completo` - Nome completo (es: "Rossi Mario")
- `$.delegato.luogo_nascita` - Luogo di nascita (es: "Roma")
- `$.delegato.data_nascita` - Data di nascita (es: "1980-01-15")
- `$.delegato.carica` - Carica (codice, es: "DEPUTATO")
- `$.delegato.carica_display` - Carica (leggibile, es: "Deputato")
- `$.delegato.circoscrizione` - Circoscrizione elettorale (es: "Lazio 1")
- `$.delegato.data_nomina` - Data di nomina (es: "2024-01-01")
- `$.delegato.email` - Email
- `$.delegato.telefono` - Telefono
- `$.delegato.territorio` - Descrizione territorio (es: "Regioni: Lazio")
- `$.delegato.n_sub_deleghe` - Numero sub-deleghe attive

**Sub-Delegato** ($.subdelegato.*):
- `$.subdelegato.id` - ID univoco
- `$.subdelegato.cognome` - Cognome
- `$.subdelegato.nome` - Nome
- `$.subdelegato.nome_completo` - Nome completo
- `$.subdelegato.luogo_nascita` - Luogo di nascita
- `$.subdelegato.data_nascita` - Data di nascita
- `$.subdelegato.domicilio` - Domicilio completo (es: "Via Roma 1, 20121 Milano (MI)")
- `$.subdelegato.tipo_documento` - Tipo documento (es: "Carta d'identità")
- `$.subdelegato.numero_documento` - Numero documento
- `$.subdelegato.email` - Email
- `$.subdelegato.telefono` - Telefono
- `$.subdelegato.data_delega` - Data della delega
- `$.subdelegato.firma_autenticata` - Firma autenticata (true/false)
- `$.subdelegato.autenticatore` - Nome autenticatore
- `$.subdelegato.tipo_delega` - Tipo delega (codice)
- `$.subdelegato.tipo_delega_display` - Tipo delega (leggibile)
- `$.subdelegato.puo_designare_direttamente` - Può designare direttamente (true/false)
- `$.subdelegato.regioni_nomi` - Array nomi regioni
- `$.subdelegato.province_nomi` - Array nomi province
- `$.subdelegato.comuni_nomi` - Array nomi comuni
- `$.subdelegato.municipi` - Array numeri municipi
- `$.subdelegato.territorio` - Descrizione territorio completa
- `$.subdelegato.delegato_nome` - Nome del delegato padre
- `$.subdelegato.delegato_carica` - Carica del delegato padre
- `$.subdelegato.n_designazioni` - Numero designazioni confermate
- `$.subdelegato.n_bozze` - Numero designazioni bozza

### Esempi di Espressioni JSONPath:

```javascript
// Nome completo del delegato
$.delegato.nome_completo

// Concatenazione cognome + nome sub-delegato
$.subdelegato.cognome + " " + $.subdelegato.nome

// Dati completi con descrizione
"Delegato: " + $.delegato.nome_completo + " (" + $.delegato.carica_display + ")"

// Domicilio sub-delegato
$.subdelegato.domicilio

// Territorio di competenza
$.subdelegato.territorio

// Email con prefisso
"Email: " + $.subdelegato.email
```

---

## Template Type: DESIGNATION (Designazione RDL)

**Usa questo schema per template di tipo DESIGNATION.**

Contiene:
- `delegato`: Dati del Delegato di Lista
- `subdelegato`: Dati del Sub-Delegato (opzionale)
- `designazioni`: Array di sezioni, **ognuna con effettivo E supplente**

**IMPORTANTE**: Ogni elemento dell'array rappresenta una **sezione elettorale** con entrambi gli RDL:
- `effettivo_*`: Campi dell'RDL Effettivo
- `supplente_*`: Campi dell'RDL Supplente (stringa vuota "" se non assegnato)

### Schema JSON da copiare:

```json
{
  "delegato": {
    "id": 1,
    "cognome": "Rossi",
    "nome": "Mario",
    "nome_completo": "Rossi Mario",
    "luogo_nascita": "Roma",
    "data_nascita": "1980-01-15",
    "carica": "DEPUTATO",
    "carica_display": "Deputato",
    "circoscrizione": "Lazio 1",
    "data_nomina": "2024-01-01",
    "email": "mario.rossi@m5s.it",
    "telefono": "+39 123456789",
    "territorio": "Regioni: Lazio",
    "n_sub_deleghe": 5
  },
  "subdelegato": {
    "id": 10,
    "cognome": "Bianchi",
    "nome": "Anna",
    "nome_completo": "Bianchi Anna",
    "email": "anna.bianchi@example.com",
    "telefono": "+39 987654321",
    "territorio": "Province: Milano | Comuni: Milano, Monza",
    "delegato_nome": "Rossi Mario",
    "tipo_delega_display": "Firma Autenticata"
  },
  "designazioni": [
    {
      "sezione_id": 1,
      "sezione_numero": "001",
      "sezione_comune": "Milano",
      "sezione_indirizzo": "Via Roma 1, 20121 Milano",
      "sezione_municipio": 1,
      "effettivo_id": 100,
      "effettivo_cognome": "Verdi",
      "effettivo_nome": "Luigi",
      "effettivo_nome_completo": "Verdi Luigi",
      "effettivo_luogo_nascita": "Torino",
      "effettivo_data_nascita": "1990-03-20",
      "effettivo_domicilio": "Via Milano 5, 20122 Milano (MI)",
      "effettivo_email": "luigi.verdi@example.com",
      "effettivo_telefono": "+39 111222333",
      "effettivo_data_designazione": "2024-03-15",
      "effettivo_stato": "CONFERMATA",
      "effettivo_stato_display": "Confermata",
      "supplente_id": 101,
      "supplente_cognome": "Gialli",
      "supplente_nome": "Maria",
      "supplente_nome_completo": "Gialli Maria",
      "supplente_luogo_nascita": "Bologna",
      "supplente_data_nascita": "1988-07-10",
      "supplente_domicilio": "Via Torino 8, 20123 Milano (MI)",
      "supplente_email": "maria.gialli@example.com",
      "supplente_telefono": "+39 444555666",
      "supplente_data_designazione": "2024-03-15",
      "supplente_stato": "CONFERMATA",
      "supplente_stato_display": "Confermata"
    },
    {
      "sezione_id": 2,
      "sezione_numero": "002",
      "sezione_comune": "Milano",
      "sezione_indirizzo": "Via Milano 10, 20122 Milano",
      "sezione_municipio": 1,
      "effettivo_id": 102,
      "effettivo_cognome": "Neri",
      "effettivo_nome": "Paolo",
      "effettivo_nome_completo": "Neri Paolo",
      "effettivo_luogo_nascita": "Napoli",
      "effettivo_data_nascita": "1992-11-05",
      "effettivo_domicilio": "Via Napoli 12, 20124 Milano (MI)",
      "effettivo_email": "paolo.neri@example.com",
      "effettivo_telefono": "+39 777888999",
      "effettivo_data_designazione": "2024-03-15",
      "effettivo_stato": "CONFERMATA",
      "effettivo_stato_display": "Confermata",
      "supplente_id": 103,
      "supplente_cognome": "Blu",
      "supplente_nome": "Carla",
      "supplente_nome_completo": "Blu Carla",
      "supplente_luogo_nascita": "Firenze",
      "supplente_data_nascita": "1995-02-28",
      "supplente_domicilio": "Via Firenze 3, 20125 Milano (MI)",
      "supplente_email": "carla.blu@example.com",
      "supplente_telefono": "+39 333444555",
      "supplente_data_designazione": "2024-03-16",
      "supplente_stato": "BOZZA",
      "supplente_stato_display": "Bozza"
    },
    {
      "sezione_id": 3,
      "sezione_numero": "003",
      "sezione_comune": "Milano",
      "sezione_indirizzo": "Via Dante 15, 20123 Milano",
      "sezione_municipio": 2,
      "effettivo_id": 104,
      "effettivo_cognome": "Rossi",
      "effettivo_nome": "Luca",
      "effettivo_nome_completo": "Rossi Luca",
      "effettivo_luogo_nascita": "Genova",
      "effettivo_data_nascita": "1987-05-12",
      "effettivo_domicilio": "Via Genova 20, 20126 Milano (MI)",
      "effettivo_email": "luca.rossi@example.com",
      "effettivo_telefono": "+39 222333444",
      "effettivo_data_designazione": "2024-03-15",
      "effettivo_stato": "CONFERMATA",
      "effettivo_stato_display": "Confermata",
      "supplente_id": "",
      "supplente_cognome": "",
      "supplente_nome": "",
      "supplente_nome_completo": "",
      "supplente_luogo_nascita": "",
      "supplente_data_nascita": "",
      "supplente_domicilio": "",
      "supplente_email": "",
      "supplente_telefono": "",
      "supplente_data_designazione": "",
      "supplente_stato": "",
      "supplente_stato_display": ""
    }
  ]
}
```

### Campi Disponibili per Autocomplete:

**Delegato** ($.delegato.*):
- Come DELEGATION template (vedi sopra)

**Sub-Delegato** ($.subdelegato.*):
- `$.subdelegato.id` - ID univoco
- `$.subdelegato.cognome` - Cognome
- `$.subdelegato.nome` - Nome
- `$.subdelegato.nome_completo` - Nome completo
- `$.subdelegato.email` - Email
- `$.subdelegato.telefono` - Telefono
- `$.subdelegato.territorio` - Descrizione territorio
- `$.subdelegato.delegato_nome` - Nome del delegato padre
- `$.subdelegato.tipo_delega_display` - Tipo delega (leggibile)

**Designazioni Array** ($.designazioni):
- `$.designazioni` - Array completo (per loop)

**Campi per Loop** ($.designazioni[].* - path relativi all'elemento dell'array):

**Info Sezione:**
- `$.designazioni[].sezione_id` - ID sezione
- `$.designazioni[].sezione_numero` - Numero sezione (es: "001")
- `$.designazioni[].sezione_comune` - Nome comune
- `$.designazioni[].sezione_indirizzo` - Indirizzo completo sezione
- `$.designazioni[].sezione_municipio` - Numero municipio (se Roma)

**Dati RDL Effettivo (effettivo_*):**
- `$.designazioni[].effettivo_id` - ID designazione effettivo
- `$.designazioni[].effettivo_cognome` - Cognome
- `$.designazioni[].effettivo_nome` - Nome
- `$.designazioni[].effettivo_nome_completo` - Nome completo
- `$.designazioni[].effettivo_luogo_nascita` - Luogo di nascita
- `$.designazioni[].effettivo_data_nascita` - Data di nascita
- `$.designazioni[].effettivo_domicilio` - Domicilio completo
- `$.designazioni[].effettivo_email` - Email
- `$.designazioni[].effettivo_telefono` - Telefono
- `$.designazioni[].effettivo_data_designazione` - Data della designazione
- `$.designazioni[].effettivo_stato` - Stato (codice)
- `$.designazioni[].effettivo_stato_display` - Stato leggibile

**Dati RDL Supplente (supplente_*):**
- `$.designazioni[].supplente_id` - ID designazione supplente (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_cognome` - Cognome (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_nome` - Nome (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_nome_completo` - Nome completo (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_luogo_nascita` - Luogo di nascita (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_data_nascita` - Data di nascita (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_domicilio` - Domicilio completo (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_email` - Email (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_telefono` - Telefono (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_data_designazione` - Data della designazione (stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_stato` - Stato (codice, stringa vuota "" se non assegnato)
- `$.designazioni[].supplente_stato_display` - Stato leggibile (stringa vuota "" se non assegnato)

### Esempi di Espressioni JSONPath:

**Campi Semplici:**
```javascript
// Nome delegato
$.delegato.nome_completo

// Nome sub-delegato (se presente)
$.subdelegato.nome_completo

// Territorio
$.subdelegato.territorio
```

**Loop Designazioni:**
```javascript
// JSONPath del loop (campo tipo 'loop')
$.designazioni

// INFO SEZIONE (path relativi):
$.sezione_numero
$.sezione_indirizzo
$.sezione_comune

// EFFETTIVO (path relativi):
$.effettivo_nome_completo
$.effettivo_email
$.effettivo_telefono
$.effettivo_cognome + " " + $.effettivo_nome

// SUPPLENTE (path relativi):
$.supplente_nome_completo
$.supplente_email
$.supplente_telefono
$.supplente_cognome + " " + $.supplente_nome

// CONCATENAZIONI COMPLETE:
"Sezione " + $.sezione_numero + ": " + $.sezione_comune
"Effettivo: " + $.effettivo_nome_completo + " - Supplente: " + $.supplente_nome_completo
$.sezione_numero + " | Eff: " + $.effettivo_email + " | Sup: " + $.supplente_email
```

**Gestire Supplente Mancante:**
Se il supplente non è assegnato, i campi `supplente_*` saranno stringhe vuote "". Il PDF mostrerà campi vuoti.

---

## Template Type: DESIGNATION_SINGLE (Designazione RDL Singola)

**Usa questo schema per template di designazione singola (un documento per designazione).**

Contiene:
- `delegato`: Dati del Delegato di Lista (opzionale)
- `subdelegato`: Dati del Sub-Delegato (opzionale)
- `designazione`: **Oggetto singolo** (non array) con una sezione e i suoi RDL

**IMPORTANTE**: Questo schema **NON ha loop**. È per generare un documento per una singola sezione alla volta.

### Schema JSON da copiare:

```json
{
  "delegato": {
    "id": 1,
    "cognome": "Rossi",
    "nome": "Mario",
    "nome_completo": "Rossi Mario",
    "luogo_nascita": "Roma",
    "data_nascita": "1980-01-15",
    "carica": "DEPUTATO",
    "carica_display": "Deputato",
    "circoscrizione": "Lazio 1",
    "data_nomina": "2024-01-01",
    "email": "mario.rossi@m5s.it",
    "telefono": "+39 123456789",
    "territorio": "Regioni: Lazio",
    "n_sub_deleghe": 5
  },
  "subdelegato": {
    "id": 10,
    "cognome": "Bianchi",
    "nome": "Anna",
    "nome_completo": "Bianchi Anna",
    "email": "anna.bianchi@example.com",
    "telefono": "+39 987654321",
    "territorio": "Province: Milano | Comuni: Milano, Monza",
    "delegato_nome": "Rossi Mario",
    "tipo_delega_display": "Firma Autenticata"
  },
  "designazione": {
    "sezione_id": 1,
    "sezione_numero": "001",
    "sezione_comune": "Milano",
    "sezione_indirizzo": "Via Roma 1, 20121 Milano",
    "sezione_municipio": 1,
    "effettivo_id": 100,
    "effettivo_cognome": "Verdi",
    "effettivo_nome": "Luigi",
    "effettivo_nome_completo": "Verdi Luigi",
    "effettivo_luogo_nascita": "Torino",
    "effettivo_data_nascita": "1990-03-20",
    "effettivo_domicilio": "Via Milano 5, 20122 Milano (MI)",
    "effettivo_email": "luigi.verdi@example.com",
    "effettivo_telefono": "+39 111222333",
    "effettivo_data_designazione": "2024-03-15",
    "effettivo_stato": "CONFERMATA",
    "effettivo_stato_display": "Confermata",
    "supplente_id": 101,
    "supplente_cognome": "Gialli",
    "supplente_nome": "Maria",
    "supplente_nome_completo": "Gialli Maria",
    "supplente_luogo_nascita": "Bologna",
    "supplente_data_nascita": "1988-07-10",
    "supplente_domicilio": "Via Torino 8, 20123 Milano (MI)",
    "supplente_email": "maria.gialli@example.com",
    "supplente_telefono": "+39 444555666",
    "supplente_data_designazione": "2024-03-15",
    "supplente_stato": "CONFERMATA",
    "supplente_stato_display": "Confermata"
  }
}
```

### Campi Disponibili per Autocomplete:

**Delegato** ($.delegato.*):
- Come DELEGATION template (vedi sopra)

**Sub-Delegato** ($.subdelegato.*):
- Come DESIGNATION template (vedi sopra)

**Designazione Oggetto** ($.designazione.*):
- **NESSUN LOOP** - accesso diretto ai campi

**Info Sezione:**
- `$.designazione.sezione_id` - ID sezione
- `$.designazione.sezione_numero` - Numero sezione (es: "001")
- `$.designazione.sezione_comune` - Nome comune
- `$.designazione.sezione_indirizzo` - Indirizzo completo sezione
- `$.designazione.sezione_municipio` - Numero municipio (se Roma)

**Dati RDL Effettivo:**
- `$.designazione.effettivo_id` - ID designazione effettivo
- `$.designazione.effettivo_cognome` - Cognome
- `$.designazione.effettivo_nome` - Nome
- `$.designazione.effettivo_nome_completo` - Nome completo
- `$.designazione.effettivo_luogo_nascita` - Luogo di nascita
- `$.designazione.effettivo_data_nascita` - Data di nascita
- `$.designazione.effettivo_domicilio` - Domicilio completo
- `$.designazione.effettivo_email` - Email
- `$.designazione.effettivo_telefono` - Telefono
- `$.designazione.effettivo_data_designazione` - Data della designazione
- `$.designazione.effettivo_stato` - Stato (codice)
- `$.designazione.effettivo_stato_display` - Stato leggibile

**Dati RDL Supplente:**
- `$.designazione.supplente_id` - ID designazione supplente (stringa vuota "" se non assegnato)
- `$.designazione.supplente_cognome` - Cognome (stringa vuota "" se non assegnato)
- `$.designazione.supplente_nome` - Nome (stringa vuota "" se non assegnato)
- `$.designazione.supplente_nome_completo` - Nome completo (stringa vuota "" se non assegnato)
- `$.designazione.supplente_luogo_nascita` - Luogo di nascita (stringa vuota "" se non assegnato)
- `$.designazione.supplente_data_nascita` - Data di nascita (stringa vuota "" se non assegnato)
- `$.designazione.supplente_domicilio` - Domicilio completo (stringa vuota "" se non assegnato)
- `$.designazione.supplente_email` - Email (stringa vuota "" se non assegnato)
- `$.designazione.supplente_telefono` - Telefono (stringa vuota "" se non assegnato)
- `$.designazione.supplente_data_designazione` - Data della designazione (stringa vuota "" se non assegnato)
- `$.designazione.supplente_stato` - Stato (codice, stringa vuota "" se non assegnato)
- `$.designazione.supplente_stato_display` - Stato leggibile (stringa vuota "" se non assegnato)

### Esempi di Espressioni JSONPath:

**Campi Semplici:**
```javascript
// Delegato
$.delegato.nome_completo

// Sub-delegato
$.subdelegato.nome_completo

// Info sezione (accesso diretto, NON c'è loop)
$.designazione.sezione_numero
$.designazione.sezione_indirizzo
$.designazione.sezione_comune

// Effettivo (accesso diretto)
$.designazione.effettivo_nome_completo
$.designazione.effettivo_email
$.designazione.effettivo_telefono

// Supplente (accesso diretto)
$.designazione.supplente_nome_completo
$.designazione.supplente_email
$.designazione.supplente_telefono
```

**Concatenazioni:**
```javascript
// Nome completo effettivo
$.designazione.effettivo_cognome + " " + $.designazione.effettivo_nome

// Info sezione con comune
"Sezione " + $.designazione.sezione_numero + " - " + $.designazione.sezione_comune

// Effettivo e supplente insieme
"Effettivo: " + $.designazione.effettivo_nome_completo + " | Supplente: " + $.designazione.supplente_nome_completo

// Email completa
"Email effettivo: " + $.designazione.effettivo_email
```

**Differenza con DESIGNATION (multipla):**
```javascript
// DESIGNATION MULTIPLA (con loop):
$.designazioni                        // Array
$.designazioni[].sezione_numero      // Dentro il loop

// DESIGNATION SINGOLA (senza loop):
$.designazione.sezione_numero        // Accesso diretto (NON serve loop)
```

---

## Come Usare gli Schemi

### 1. Django Admin

1. Vai su **Documents** → **Templates**
2. Seleziona il template (o creane uno nuovo)
3. Scegli il tipo appropriato:
   - **DELEGATION**: Per sub-deleghe
   - **DESIGNATION** con nome "individuale" o "multipla": Per designazioni con loop
   - **DESIGNATION** con nome "singola": Per designazione singola senza loop
4. Trova la sezione **"Schema Variabili (Autocomplete)"**
5. Copia lo schema JSON corrispondente al tipo di template
6. Incolla nel campo `variables_schema`
7. Salva

**Tip**: Il comando `populate_variables_schema` riconosce automaticamente i template dal nome:
- Nome contiene "individuale" → schema multiplo con loop
- Nome contiene "singola" → schema singolo senza loop

### 2. Template Editor

Una volta salvato lo schema:
1. Apri il Template Editor
2. Click "Aggiungi Campo"
3. Digita `$.` nel campo JSONPath
4. Vedi tutte le opzioni disponibili con autocomplete
5. Seleziona il campo desiderato

### 3. Personalizzazione

Puoi modificare gli schemi per:
- Aggiungere campi custom
- Rimuovere campi non usati
- Cambiare i valori di esempio

**IMPORTANTE**: I campi devono corrispondere ai dati reali che il backend genera!

---

## Comparazione Tipi di Template

### Riepilogo Strutture

| Tipo | Uso | Struttura Dati | Loop | Complessità |
|------|-----|----------------|------|-------------|
| **DELEGATION** | Sub-deleghe | `delegato` + `subdelegato` | No | ⭐ Semplice |
| **DESIGNATION (singola)** | Una designazione | `delegato/subdelegato` + `designazione` (oggetto) | No | ⭐⭐ Medio |
| **DESIGNATION (multipla)** | Più designazioni | `delegato/subdelegato` + `designazioni` (array) | Sì | ⭐⭐⭐ Avanzato |

### Quando Usare Quale

**DELEGATION** - Per documenti di sub-delega:
```javascript
$.delegato.nome_completo
$.subdelegato.nome_completo
$.subdelegato.territorio
```

**DESIGNATION (singola)** - Per generare un PDF per ogni sezione:
```javascript
$.delegato.nome_completo
$.designazione.sezione_numero          // Una sola sezione
$.designazione.effettivo_nome_completo
$.designazione.supplente_nome_completo
```
✅ **Usa questo** se generi un documento per sezione

**DESIGNATION (multipla)** - Per generare un PDF con tutte le sezioni:
```javascript
$.delegato.nome_completo
$.designazioni                          // Array di sezioni
$.designazioni[].sezione_numero        // Loop: prima sezione, seconda, ecc.
$.designazioni[].effettivo_nome_completo
$.designazioni[].supplente_nome_completo
```
✅ **Usa questo** se vuoi tutte le sezioni in un unico documento (stampa unione)

### Esempio Pratico

**Caso d'uso**: Subdelegato ha 10 sezioni assegnate

**Opzione 1 - DESIGNATION (singola)**:
- Backend genera: 10 PDF separati (uno per sezione)
- Template: Nessun loop, campi semplici `$.designazione.*`
- Risultato: 10 file PDF individuali

**Opzione 2 - DESIGNATION (multipla)**:
- Backend genera: 1 PDF con 10 righe
- Template: Loop `$.designazioni` con campi relativi
- Risultato: 1 file PDF con tabella di 10 righe

## Command Line

Per aggiornare automaticamente tutti i template esistenti:

```bash
# Docker
docker exec rdl_backend python manage.py populate_variables_schema

# Locale
cd backend_django
python manage.py populate_variables_schema
```

---

## Verificare i Campi Disponibili

Per vedere quali campi sono serializzati dal backend, consulta:
- `backend_django/delegations/serializers.py`
  - `DelegatoDiListaSerializer` (linee 12-54)
  - `SubDelegaSerializer` (linee 56-129)
  - `DesignazioneRDLSerializer` (linee 150-201)

---

## Troubleshooting

### Autocomplete non mostra suggerimenti
- Verifica che `variables_schema` non sia vuoto
- Controlla la console browser per errori
- Ricarica il Template Editor

### Campi non corrispondono ai dati reali
- Aggiorna lo schema con i campi corretti dal serializer
- Esegui il comando `populate_variables_schema`
- Verifica che il backend stia usando i serializer aggiornati

### Loop non genera righe
- Verifica che il JSONPath del loop punti ad un array
- Esempio corretto: `$.designazioni` (non `$.designazioni[]`)
- Controlla che i campi loop siano relativi: `$.sezione` (non `$.designazioni[].sezione`)

---

**Ultimo Aggiornamento**: 2026-02-05
**Basato su**: Django serializers reali
**Comando**: `populate_variables_schema`
