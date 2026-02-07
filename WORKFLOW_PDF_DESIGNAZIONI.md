# Workflow Generazione PDF Designazioni

## Problema Attuale

Quando l'utente importa la mappatura, vede subito stato "CONFERMATO" invece di "BOZZA".

### Causa del Problema

Nel backend `delegations/views.py:635-637`:

```python
stato_iniziale = 'CONFERMATA' if (
    (sub_delega and sub_delega.tipo_delega == 'FIRMA_AUTENTICATA') or delegato_diretto
) else 'BOZZA'
```

Il subdelegato dell'utente ha probabilmente `tipo_delega='FIRMA_AUTENTICATA'` quando dovrebbe essere `'MAPPATURA'` per creare designazioni in BOZZA.

### Soluzione

1. **Verificare nel database** quale tipo_delega ha il subdelegato:
   ```sql
   SELECT email, tipo_delega FROM delegations_subdelega WHERE email = 'linda.meleo@...';
   ```

2. **Cambiare tipo_delega** da FIRMA_AUTENTICATA a MAPPATURA se necessario:
   ```sql
   UPDATE delegations_subdelega
   SET tipo_delega = 'MAPPATURA'
   WHERE email = 'linda.meleo@...' AND tipo_delega = 'FIRMA_AUTENTICATA';
   ```

## Workflow PDF Completo da Implementare

### 1. Aggiungere Tab "Lista Designazioni"

In `GestioneDesignazioni.js`, aggiungere nuova tab che mostra:
- Lista completa designazioni con stato (BOZZA/CONFERMATA)
- Checkbox per selezione multipla (solo per BOZZE)
- Badge colorato per stato:
  - BOZZA → giallo warning
  - CONFERMATA → verde success
- Filtri per comune/municipio
- Ricerca per nome RDL

### 2. Selezione Multipla

- Checkbox "Seleziona tutte le bozze"
- Checkbox individuale per ogni designazione in BOZZA
- Contatore selezionate: "5 designazioni selezionate"
- Pulsante "Genera PDF" attivo solo se almeno 1 selezionata

### 3. Modale Generazione PDF (Multi-Step)

#### Step 1: Selezione Template
```javascript
const templates = await client.templates.list(consultazione.id);
```

Mostrare:
- Lista template disponibili per la consultazione
- Descrizione e anteprima di ogni template
- Selezione radio button
- Pulsante "Avanti"

#### Step 2: Form Dati Delegato/Subdelegato

Auto-compilare dal `client.deleghe.miaCatena()`:
- Se subdelegato: cognome, nome, luogo_nascita, data_nascita, domicilio, tipo_documento, numero_documento
- Se delegato: cognome, nome, carica, circoscrizione

Form editabile per completare campi mancanti:
- Luogo nascita (se mancante)
- Data nascita (se mancante)
- Domicilio (se mancante)
- Tipo documento (select: Carta d'Identità, Patente, Passaporto)
- Numero documento

Validazione:
```javascript
const requiredFields = template.required_fields || [
  'cognome', 'nome', 'data_nascita', 'domicilio'
];

const missingFields = requiredFields.filter(field => !formData[field]);
```

Mostrare alert se campi mancanti, disabilitare "Avanti" se validazione fallisce.

#### Step 3: Preview PDF

```javascript
const previewBlob = await client.templates.preview(selectedTemplate.id, {
  delegato: formData,
  designazioni: Array.from(selectedDesignazioni)
});

// Mostrare PDF in iframe o object
<object data={URL.createObjectURL(previewBlob)} type="application/pdf" width="100%" height="600px">
  Preview PDF non disponibile
</object>
```

Pulsanti:
- "Indietro" → torna a Step 2
- "Genera PDF" → crea batch e genera documento

#### Step 4: Generazione Batch

```javascript
// Crea batch
const batch = await client.batch.create({
  consultazione_id: consultazione.id,
  tipo: 'INDIVIDUALE',
  solo_sezioni: Array.from(selectedDesignazioni).map(d => d.sezione_id)
});

// Genera PDF
await client.batch.genera(batch.id);

// Stato batch diventa GENERATO
// Download automatico o link download
```

### 4. Stati Batch

- **BOZZA**: Batch creato, PDF non generato
- **GENERATO**: PDF generato, designazioni ancora in BOZZA
- **APPROVATO**: PDF approvato, designazioni passano da BOZZA → CONFERMATA
- **INVIATO**: PDF inviato/stampato

### 5. Approvazione Batch

Dopo generazione PDF, mostrare pulsante "Approva Batch":
```javascript
await client.batch.approva(batch.id);
// Questo cambia stato designazioni da BOZZA → CONFERMATA
```

## File da Modificare

1. **src/Client.js** ✅ (API già aggiunte)
2. **src/GestioneDesignazioni.js** (aggiungere tab Lista + logica selezione multipla)
3. **src/components/PdfGenerationModal.js** (nuovo componente per modale multi-step)
4. **backend_django/delegations/views.py** (verificare/correggere tipo_delega)

## Stima Implementazione

- Tab Lista: ~100 righe
- Selezione multipla: ~50 righe
- Modale PDF (3 steps): ~400 righe
- Form validation: ~50 righe
- Preview PDF: ~50 righe
- Batch generation logic: ~100 righe

**Totale: ~750 righe di codice**

## Next Steps

1. ✅ Verificare tipo_delega nel database
2. ✅ Correggere se necessario
3. ⏳ Testare che import crei BOZZE
4. ⏳ Implementare tab Lista
5. ⏳ Implementare selezione multipla
6. ⏳ Implementare modale PDF multi-step
7. ⏳ Testing completo workflow

## Note

- I template PDF devono essere configurati in Django admin
- Serve configurare i template document in backend (`documents` app)
- Preview PDF potrebbe richiedere libreria PDF.js se browser non supporta nativamente
