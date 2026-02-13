# Guida Template PDF - JSONPath e Loop

## Indice

1. [Tipi di Template](#tipi-di-template)
2. [Espressioni JSONPath](#espressioni-jsonpath)
3. [Configurare un Loop (solo MULTI)](#configurare-un-loop)
4. [Esempi Pratici](#esempi-pratici)
5. [Troubleshooting](#troubleshooting)

---

## Tipi di Template

### DESIGNATION_SINGLE - Designazione Individuale

**Un documento per sezione**. Dati piatti al top level, nessun loop.

Struttura dati:
```json
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario",
    "luogo_nascita": "Roma",
    "data_nascita": "1980-01-15",
    "carica": "Deputato",
    "documento": "CI AB123456",
    "domicilio": "Via Roma 1, Roma"
  },
  "sezione": 2359,
  "comune": "Roma",
  "indirizzo": "VIA VALLOMBROSA, 31",
  "effettivo": {
    "cognome": "Verdi",
    "nome": "Luigi",
    "data_nascita": "1990-03-20",
    "luogo_nascita": "Torino",
    "domicilio": "Via Milano 5, Milano"
  },
  "supplente": {
    "cognome": "Gialli",
    "nome": "Maria",
    "data_nascita": "1988-07-10",
    "luogo_nascita": "Bologna",
    "domicilio": "Via Torino 8, Milano"
  }
}
```

**JSONPath disponibili:**
- `$.delegato.cognome`, `$.delegato.nome`, `$.delegato.data_nascita`, `$.delegato.luogo_nascita`, `$.delegato.carica`, `$.delegato.documento`, `$.delegato.domicilio`
- `$.sezione`, `$.comune`, `$.indirizzo`
- `$.effettivo.cognome`, `$.effettivo.nome`, `$.effettivo.data_nascita`, `$.effettivo.luogo_nascita`, `$.effettivo.domicilio`
- `$.supplente.cognome`, `$.supplente.nome`, `$.supplente.data_nascita`, `$.supplente.luogo_nascita`, `$.supplente.domicilio`

**Tutti i campi sono di tipo `text`**. Non serve nessun loop.

---

### DESIGNATION_MULTI - Designazione Riepilogativa

**Un documento con tutte le sezioni**. Delegato e comune al top level, designazioni in array per loop.

Struttura dati:
```json
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario",
    "luogo_nascita": "Roma",
    "data_nascita": "1980-01-15",
    "carica": "Deputato",
    "documento": "CI AB123456",
    "domicilio": "Via Roma 1, Roma"
  },
  "comune": "Roma",
  "designazioni": [
    {
      "sezione": 2359,
      "indirizzo": "VIA VALLOMBROSA, 31",
      "effettivo": {
        "cognome": "Verdi",
        "nome": "Luigi",
        "data_nascita": "1990-03-20",
        "luogo_nascita": "Torino",
        "domicilio": "Via Milano 5, Milano"
      },
      "supplente": {
        "cognome": "Gialli",
        "nome": "Maria",
        "data_nascita": "1988-07-10",
        "luogo_nascita": "Bologna",
        "domicilio": "Via Torino 8, Milano"
      }
    }
  ]
}
```

**JSONPath delegato e comune (tipo `text`, assoluti):**
- `$.delegato.cognome`, `$.delegato.nome`, etc.
- `$.comune` (uguale per tutte le sezioni, non si fanno documenti cross-comune)

**Loop jsonpath:** `$.designazioni`

**JSONPath nel loop (relativi ad ogni item):**
- `$.sezione`, `$.indirizzo`
- `$.effettivo.cognome`, `$.effettivo.nome`, `$.effettivo.data_nascita`, `$.effettivo.luogo_nascita`, `$.effettivo.domicilio`
- `$.supplente.cognome`, `$.supplente.nome`, `$.supplente.data_nascita`, `$.supplente.luogo_nascita`, `$.supplente.domicilio`

---

## Espressioni JSONPath

### JSONPath Semplice

Estrae un singolo campo:

```
$.delegato.cognome
// Risultato: "Rossi"
```

### JSONPath Concatenato

Concatena piu' campi con `+`:

```
$.delegato.cognome + " " + $.delegato.nome
// Risultato: "Rossi Mario"

$.effettivo.cognome + " " + $.effettivo.nome
// Risultato: "Verdi Luigi"
```

### Autocomplete

Digita `$.` nel campo JSONPath per vedere i suggerimenti. I suggerimenti derivano dallo schema di esempio del tipo template.

---

## Configurare un Loop

> Solo per template **DESIGNATION_MULTI** (riepilogativo).
> Per DESIGNATION_SINGLE non serve: tutti i campi sono `text`.

### Workflow

1. **Aggiungi campo** con tipo `loop` e JSONPath `$.designazioni`
2. **Seleziona la PRIMA riga** della tabella sul PDF (l'area del loop)
3. Le righe successive vengono generate automaticamente
4. Usa il pulsante **"Campi"** per definire le colonne del loop

### Campi Loop

Per ogni colonna della tabella, aggiungi un campo:

| Campo | JSONPath |
|-------|----------|
| Sezione | `$.sezione` |
| Comune | `$.comune` |
| Effettivo | `$.effettivo.cognome + " " + $.effettivo.nome` |
| Data nascita eff. | `$.effettivo.data_nascita` |
| Luogo nascita eff. | `$.effettivo.luogo_nascita` |
| Domicilio eff. | `$.effettivo.domicilio` |
| Supplente | `$.supplente.cognome + " " + $.supplente.nome` |
| Data nascita suppl. | `$.supplente.data_nascita` |
| Luogo nascita suppl. | `$.supplente.luogo_nascita` |
| Domicilio suppl. | `$.supplente.domicilio` |

I JSONPath nei loop sono **relativi all'elemento corrente** dell'array.

### Paginazione

Se la lista e' lunga, configura la paginazione:

```json
{
  "rows_first_page": 6,
  "rows_per_page": 13,
  "data_source": "$.designazioni"
}
```

- **rows_first_page**: Righe nella prima pagina (meno se c'e' header)
- **rows_per_page**: Righe nelle pagine successive

### Loop Multi-Pagina (posizioni diverse)

Se la prima pagina ha un header e le successive no:

1. **Prima pagina**: Seleziona riga sotto header, imposta page=0
2. **Pagine successive**: Seleziona riga dall'alto, imposta page=1
3. Il backend usa page=0 per pagina 1, page=1 per pagine 2, 3, 4...

---

## Esempi Pratici

### Esempio: DESIGNATION_SINGLE

**Field Mappings** (tutti `text`):
```json
[
  {
    "jsonpath": "$.delegato.cognome + ' ' + $.delegato.nome",
    "type": "text",
    "area": {"x": 100, "y": 50, "width": 200, "height": 20},
    "page": 0
  },
  {
    "jsonpath": "$.sezione",
    "type": "text",
    "area": {"x": 100, "y": 80, "width": 50, "height": 20},
    "page": 0
  },
  {
    "jsonpath": "$.effettivo.cognome + ' ' + $.effettivo.nome",
    "type": "text",
    "area": {"x": 100, "y": 110, "width": 200, "height": 20},
    "page": 0
  }
]
```

### Esempio: DESIGNATION_MULTI

**Campi delegato** (`text`) + **Loop designazioni**:
```json
[
  {
    "jsonpath": "$.delegato.cognome + ' ' + $.delegato.nome",
    "type": "text",
    "area": {"x": 100, "y": 50, "width": 200, "height": 20},
    "page": 0
  },
  {
    "jsonpath": "$.designazioni",
    "type": "loop",
    "area": {"x": 50, "y": 150, "width": 500, "height": 15},
    "page": 0,
    "rows": 6,
    "loop_fields": [
      {"jsonpath": "$.sezione", "x": 0, "y": 0, "width": 40, "height": 12},
      {"jsonpath": "$.comune", "x": 50, "y": 0, "width": 100, "height": 12},
      {"jsonpath": "$.effettivo.cognome + ' ' + $.effettivo.nome", "x": 160, "y": 0, "width": 150, "height": 12},
      {"jsonpath": "$.supplente.cognome + ' ' + $.supplente.nome", "x": 320, "y": 0, "width": 150, "height": 12}
    ]
  }
]
```

---

## Troubleshooting

### Campo vuoto nel PDF

**Causa**: JSONPath non trova il dato.

**Soluzioni**:
1. Controlla maiuscole/minuscole: `$.delegato.cognome` (non `$.Delegato.Cognome`)
2. Verifica che il path corrisponda alla struttura: i campi sono nested (`$.effettivo.cognome`, non `$.effettivo_cognome`)
3. Usa l'autocomplete per verificare i path disponibili

### Loop non genera righe

**Causa**: JSONPath loop non restituisce array.

**Soluzioni**:
1. Verifica che il JSONPath sia `$.designazioni` (deve puntare all'array)
2. Controlla che il tipo campo sia `loop`
3. Assicurati di aver aggiunto almeno un loop_field

### Righe sovrapposte

**Causa**: `height` troppo piccolo nel loop area.

**Soluzione**: Aumenta `height` nell'area del loop (es: da 15 a 25).

---

**Versione**: 2.0
**Ultima modifica**: 2026-02-13
