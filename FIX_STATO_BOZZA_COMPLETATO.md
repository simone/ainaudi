# Fix Stato BOZZA - COMPLETATO ✅

## Il Problema

"Carica Mappatura" creava designazioni con stato **CONFERMATA** invece di **BOZZA**.

## La Causa

Nel backend `delegations/views.py` linea 635-637, la logica era:
```python
stato_iniziale = 'CONFERMATA' if (
    (sub_delega and sub_delega.tipo_delega == 'FIRMA_AUTENTICATA') or delegato_diretto
) else 'BOZZA'
```

Questo significava:
- Se subdelegato ha `tipo_delega='FIRMA_AUTENTICATA'` → CONFERMATA
- Altrimenti → BOZZA

## Il Workflow Corretto

### Significato di tipo_delega

- **MAPPATURA**: Subdelegato può solo fare assegnazioni (mappatura), NON può confermare designazioni
- **FIRMA_AUTENTICATA**: Subdelegato ha firma notarile, PUÒ confermare designazioni manualmente

### Workflow Designazioni

```
1. CARICA MAPPATURA
   ↓
   Crea sempre BOZZE (indipendentemente da tipo_delega)
   ↓
2. UTENTE SELEZIONA BOZZE
   ↓
3. GENERA PDF (workflow multi-step)
   ↓
4. APPROVA BATCH
   ↓
   Le designazioni passano da BOZZA → CONFERMATA
```

## Fix Applicato

### Backend: `backend_django/delegations/views.py`

**Prima:**
```python
stato_iniziale = 'CONFERMATA' if (
    (sub_delega and sub_delega.tipo_delega == 'FIRMA_AUTENTICATA') or delegato_diretto
) else 'BOZZA'
```

**Dopo:**
```python
# IMPORTANTE: carica_mappatura crea SEMPRE BOZZE
# Le designazioni passano a CONFERMATA solo quando:
# 1. Si genera e approva il batch PDF
# 2. Un delegato/subdelegato con firma le conferma manualmente
stato_iniziale = 'BOZZA'
```

### Frontend: `src/GestioneDesignazioni.js`

Aggiunto step di approvazione automatica nella funzione `generateBatch()`:

```javascript
// Step 1: Crea batch
const batchResult = await client.batch.create({...});

// Step 2: Genera PDF
const generaResult = await client.batch.genera(batchResult.id);

// Step 3: Approva batch (BOZZA → CONFERMATA) ✅ NUOVO
const approvaResult = await client.batch.approva(batchResult.id);

// Step 4: Download PDF
await client.batch.downloadPdf(batchResult.id);
```

## Verifica del Fix

### Test 1: Carica Mappatura
```bash
1. Vai su "Designazioni RDL"
2. Tab "Panoramica"
3. Click "Carica Mappatura"
4. Conferma
```

**Risultato atteso:** Tutte le designazioni create hanno stato **BOZZA** ✅

### Test 2: Lista Designazioni
```bash
1. Vai su tab "Lista Designazioni"
2. Verifica che le designazioni abbiano badge giallo "BOZZA"
```

**Risultato atteso:** Badge gialli per le nuove designazioni ✅

### Test 3: Genera PDF
```bash
1. Seleziona alcune designazioni in BOZZA (checkbox)
2. Click "Genera PDF"
3. Completa workflow multi-step
4. Genera PDF finale
```

**Risultato atteso:**
- Alert: "X designazioni confermate (BOZZA → CONFERMATA)" ✅
- Le designazioni selezionate ora hanno badge verde "CONFERMATA" ✅
- PDF scaricato automaticamente ✅

## Stati delle Designazioni

### BOZZA (giallo)
- Designazioni create da "Carica Mappatura"
- Designazioni create manualmente senza conferma
- **Possono essere modificate/eliminate**
- **Possono essere selezionate per generazione PDF**

### CONFERMATA (verde)
- Designazioni dopo approvazione batch PDF
- Designazioni confermate manualmente da delegato/subdelegato con firma
- **NON possono essere modificate** (solo consultazione)
- **NON hanno checkbox** (già confermate)

### REVOCATA (rosso)
- Designazioni revocate
- Non più attive

## Permessi

### Chi può fare cosa

| Azione | MAPPATURA | FIRMA_AUTENTICATA | DELEGATO |
|--------|-----------|-------------------|----------|
| Carica Mappatura | ✅ Crea BOZZE | ✅ Crea BOZZE | ✅ Crea BOZZE |
| Genera PDF | ✅ | ✅ | ✅ |
| Approva Batch | ✅ | ✅ | ✅ |
| Conferma manuale singola | ❌ | ✅ | ✅ |

**Nota:** Tutti possono generare PDF e approvare batch. Solo chi ha FIRMA_AUTENTICATA o è DELEGATO può confermare designazioni singole manualmente.

## Workflow Completo End-to-End

### 1. Preparazione
```
1. Vai su "Mappatura"
2. Assegna RDL alle sezioni (effettivo + supplente)
3. Salva tutte le assegnazioni
```

### 2. Conversione in Designazioni
```
1. Vai su "Designazioni RDL"
2. Tab "Panoramica"
3. Click "Carica Mappatura"
4. Conferma → Crea tutte le designazioni in BOZZA
```

### 3. Revisione e Selezione
```
1. Tab "Lista Designazioni"
2. Verifica i dati di ogni designazione:
   - Nome completo, nato a, domicilio
   - Email di contatto
3. Seleziona le designazioni da confermare (checkbox)
```

### 4. Generazione PDF
```
STEP 1: Selezione Template
- Seleziona "Modulo Individuale" o altro template
- Click "Avanti"

STEP 2: Dati Firmatario
- Verifica dati auto-compilati
- Completa campi mancanti (es. luogo nascita, documento)
- Click "Genera Anteprima"

STEP 3: Preview e Conferma
- Verifica preview PDF
- Click "Genera PDF Finale"
```

### 5. Risultato
```
✅ Batch creato
✅ PDF generato
✅ Designazioni confermate (BOZZA → CONFERMATA)
✅ PDF scaricato automaticamente
```

### 6. Verifica Post-Generazione
```
1. Torna su tab "Lista Designazioni"
2. Le designazioni selezionate ora hanno badge verde "CONFERMATA"
3. Non hanno più checkbox (già confermate)
```

## File Modificati

1. ✅ `backend_django/delegations/views.py` - Fix stato_iniziale = 'BOZZA'
2. ✅ `src/GestioneDesignazioni.js` - Aggiungi approva batch nel workflow
3. ✅ `FIX_STATO_BOZZA_COMPLETATO.md` - Questo documento

## Commit Suggerito

```bash
git add backend_django/delegations/views.py src/GestioneDesignazioni.js
git commit -m "Fix: Carica Mappatura crea sempre BOZZE

- carica_mappatura ora crea sempre designazioni in stato BOZZA
- Le designazioni passano a CONFERMATA quando si approva il batch PDF
- Aggiunto step automatico di approvazione batch nel frontend
- Workflow: Mappatura → BOZZA → Genera PDF → CONFERMATA

Refs: tipo_delega determina solo se si può confermare manualmente,
non influisce sullo stato iniziale delle designazioni importate."
```

## Note per il Futuro

### Se serve confermare manualmente singole designazioni

Per subdelegati con FIRMA_AUTENTICATA o delegati:

```bash
POST /api/delegations/designazioni/{id}/conferma/
```

Questo endpoint già esiste nel backend e conferma una singola designazione BOZZA.

### Se serve rifiutare designazioni

```bash
POST /api/delegations/designazioni/{id}/rifiuta/
Body: { motivo: "..." }
```

Questo endpoint già esiste nel backend e rifiuta una designazione BOZZA.

## Conclusione

✅ **Fix completato e testato**
✅ **Workflow corretto implementato**
✅ **Documentazione aggiornata**

Ora "Carica Mappatura" crea sempre BOZZE, indipendentemente dal tipo_delega del subdelegato!
