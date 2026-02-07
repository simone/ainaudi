# Risultati Live - Visualizzazione Gerarchica

## 📋 Overview

Funzionalità "**Risultati Live**" per **Delegati e Sub-Delegati** che permette di visualizzare i dati di scrutinio in tempo reale in modo gerarchico con navigazione drill-down attraverso i livelli territoriali.

### Problema Risolto

Quando un delegato supervisiona molte sezioni (più municipi, province o regioni), l'elenco diventa ingestibile. Questa funzionalità fornisce:

1. **Aggregazione dati** per livello territoriale
2. **Navigazione intuitiva** con drill-down progressivo
3. **Skip automatico** se c'è solo una entità a un livello
4. **Visualizzazione mobile-first** ottimizzata per touch

---

## 🎯 Navigazione Gerarchica

```
Italia (root)
  ↓
Regioni (es. Lazio, Lombardia)
  ↓
Province (es. Roma, Milano)
  ↓
Comuni (es. Roma, Milano)
  ↓
Municipi (es. Municipio I, II - solo se esistono)
  ↓
Sezioni Elettorali (dati finali)
```

### Skip Automatico

Se a un livello c'è **solo una entità**, il sistema salta automaticamente al livello successivo:

**Esempio 1**: Delegato di una sola regione
- Skip regioni → Mostra direttamente province

**Esempio 2**: Sub-delegato di una sola provincia
- Skip regioni → Skip province → Mostra direttamente comuni

**Esempio 3**: Mappatura singolo comune senza municipi
- Skip regioni → Skip province → Skip comuni → Mostra direttamente sezioni

---

## 💾 API Endpoint

### `GET /api/scrutinio/aggregato`

Endpoint con query parameters progressivi per navigazione drill-down.

#### Parameters

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `consultazione_id` | int | ID consultazione (opzionale, default: attiva) |
| `regione_id` | int | Drill-down in una regione specifica |
| `provincia_id` | int | Drill-down in una provincia specifica |
| `comune_id` | int | Drill-down in un comune specifico |
| `municipio_id` | int | Drill-down in un municipio specifico |

#### Response Structure

```json
{
  "level": "regioni|province|comuni|municipi|sezioni",
  "consultazione_id": 1,
  "regione_id": 12,
  "provincia_id": 58,
  "comune_id": 5432,
  "municipio_id": null,
  "breadcrumbs": [
    {"tipo": "root", "nome": "Italia"},
    {"tipo": "regione", "id": 12, "nome": "Lazio"},
    {"tipo": "provincia", "id": 58, "nome": "Roma"}
  ],
  "items": [
    {
      "id": 5432,
      "tipo": "comune|municipio|sezione",
      "nome": "Roma",
      "sigla": "RM",

      // Dati aggregati
      "totale_sezioni": 150,
      "sezioni_complete": 120,
      "totale_elettori": 500000,
      "totale_votanti": 300000,
      "affluenza_percentuale": 60.0,

      // Risultati per scheda
      "schede": [
        {
          "scheda_id": 1,
          "scheda_nome": "Quesito 1 - Cittadinanza",
          "voti": {
            "si": 180000,
            "no": 120000
          }
        }
      ]
    }
  ]
}
```

#### Esempi di Chiamate

**1. Root (lista regioni)**
```bash
GET /api/scrutinio/aggregato?consultazione_id=1
```

**2. Drill-down in Lazio**
```bash
GET /api/scrutinio/aggregato?consultazione_id=1&regione_id=12
# Restituisce province nel Lazio
```

**3. Drill-down in Provincia di Roma**
```bash
GET /api/scrutinio/aggregato?consultazione_id=1&regione_id=12&provincia_id=58
# Restituisce comuni in Provincia di Roma
```

**4. Drill-down in Comune di Roma**
```bash
GET /api/scrutinio/aggregato?consultazione_id=1&regione_id=12&provincia_id=58&comune_id=5432
# Restituisce municipi o sezioni (se no municipi)
```

---

## 🎨 UI Mobile-First

### Caratteristiche

✅ **Touch-friendly**
- Cards grandi con area cliccabile ampia
- Tap highlight ottimizzato
- Gesture-friendly (scroll smooth)

✅ **Header Sticky**
- Sempre visibile durante lo scroll
- Pulsante "Indietro" per risalire la gerarchia
- Breadcrumbs compatti con path corrente

✅ **Cards Ottimizzate**
- Layout a colonna singola su mobile
- Grid responsive su desktop
- Dati aggregati prominenti:
  - **Affluenza** (box grande, evidenziato)
  - Votanti, Elettori, Sezioni complete
  - Risultati per scheda (compatti)

✅ **Footer Fisso**
- Info/help sempre visibili
- Non copre contenuto (padding bottom)

### Layout Mobile

```
┌─────────────────────────────────┐
│  ← Indietro │ COMUNI │ Badge    │ ← Sticky Header
│  Italia › Lazio › Roma           │ ← Breadcrumbs
├─────────────────────────────────┤
│                                  │
│  ┌───────────────────────────┐  │
│  │ Roma (RM)                 ▸│  │ ← Card Comune
│  │                           │  │
│  │  [ 60.0% ]  [300K] [500K] │  │ ← Stats
│  │  Affluenza  Votanti Elettori │
│  │                           │  │
│  │  120/150 Complete         │  │
│  └───────────────────────────┘  │
│                                  │
│  ┌───────────────────────────┐  │
│  │ Fiumicino (RM)            ▸│  │
│  │  [ 55.2% ] ...            │  │
│  └───────────────────────────┘  │
│                                  │
│  ...                             │
│                                  │
├─────────────────────────────────┤
│  ℹ️ Tocca per esplorare         │ ← Fixed Footer
└─────────────────────────────────┘
```

---

## 🔐 Permissions

### Chi può accedere

✅ **Delegati** (con permesso `can_view_kpi`)
- Vedono tutte le sezioni del loro territorio
- Possono navigare l'intera gerarchia accessibile
- Read-only: visualizzazione dati aggregati, non inserimento

✅ **Sub-Delegati** (con permesso `can_view_kpi`)
- Vedono solo le sezioni della loro sub-delega
- Navigazione limitata al territorio assegnato
- Read-only: visualizzazione dati aggregati, non inserimento

❌ **RDL semplici**
- NON hanno accesso a scrutinio aggregato
- Hanno solo `has_scrutinio_access` per inserimento dati delle proprie sezioni
- Usano "Scrutinio" standard per data entry

### Backend Permission Check

```python
# Permission class
permission_classes = [permissions.IsAuthenticated, CanViewKPI]

# Role check
roles = get_user_delegation_roles(request.user, consultazione.id)
if not (roles['is_delegato'] or roles['is_sub_delegato']):
    return Response({'error': 'Accesso riservato...'}, status=403)
```

### Permission Semantics

- **`can_view_kpi`**: Accesso KPI dashboard + scrutinio aggregato (supervisione)
- **`has_scrutinio_access`**: Inserimento dati scrutinio (data entry RDL)

---

## 📊 Aggregazione Dati

### Query SQL Ottimizzate

L'endpoint esegue aggregazione SQL efficiente invece di loop Python:

```python
dati_sezioni.aggregate(
    totale_elettori_m=Coalesce(Sum('elettori_maschi'), 0),
    totale_elettori_f=Coalesce(Sum('elettori_femmine'), 0),
    totale_votanti_m=Coalesce(Sum('votanti_maschi'), 0),
    totale_votanti_f=Coalesce(Sum('votanti_femmine'), 0),
    sezioni_complete=Count('id', filter=Q(is_complete=True))
)
```

### Calcolo Affluenza

```python
totale_elettori = elettori_m + elettori_f
totale_votanti = votanti_m + votanti_f
affluenza = (totale_votanti / totale_elettori * 100) if totale_elettori > 0 else 0
```

### Aggregazione Risultati

#### Referendum (SI/NO)
```python
for dati_scheda in schede:
    totale_si += dati_scheda.voti.get('si', 0)
    totale_no += dati_scheda.voti.get('no', 0)
```

#### Elezioni (Liste/Candidati)
```python
# TODO: Implementare aggregazione liste/candidati
# Somma voti per lista e preferenze per candidato
```

---

## 🚀 Uso e Testing

### 1. Accesso Menu

**Per Delegati/Sub-Delegati:**
1. Login con credenziali delegato
2. Menu principale → **"Risultati Live"** (con pallino verde animato 🟢)
3. Navigazione automatica al livello appropriato (con skip)

### 2. Navigazione

**Mobile:**
- Tap su card per drill-down
- Pulsante "Indietro" in alto a sinistra
- Scroll verticale per lista

**Desktop:**
- Click su card per drill-down
- Breadcrumbs cliccabili per risalire
- Grid responsive (2-3 colonne)

### 3. Test Locali

```bash
# Backend
docker logs rdl_backend -f

# Test endpoint (con token JWT)
curl http://localhost:3001/api/scrutinio/aggregato \
  -H "Authorization: Bearer YOUR_TOKEN"

# Frontend
# Naviga a http://localhost:3000
# Login come delegato
# Click su "Risultati Live" 🟢
```

---

## 📱 Screenshots & Demo Flow

### Flow Esempio: Delegato Regione Lazio

**Step 1**: Root → Skip automatico (1 regione)
```
SKIP: Regioni
↓
Mostra: Province nel Lazio
- Frosinone
- Latina
- Rieti
- Roma     [Affluenza: 60%] [120/150 sezioni]
- Viterbo
```

**Step 2**: Tap su "Roma"
```
Mostra: Comuni in Provincia di Roma
- Anzio
- Fiumicino
- Roma     [Affluenza: 59.5%] [100/120 sezioni]
- ...
```

**Step 3**: Tap su "Roma" (comune)
```
Mostra: Municipi a Roma
- Municipio I   [Affluenza: 62%]
- Municipio II  [Affluenza: 58%]
- ...
- Municipio XV  [Affluenza: 55%]
```

**Step 4**: Tap su "Municipio I"
```
Mostra: Sezioni in Municipio I
- Sezione 123 - Scuola Garibaldi  [Affluenza: 63%] [✓ Completa]
  Risultati: SI: 523, NO: 300
- Sezione 124 - Liceo Mameli      [Affluenza: 61%] [⏱ In corso]
- ...
```

---

## 🔧 Manutenzione e Estensioni

### Aggregazione Liste/Candidati

Attualmente implementato solo per **referendum (SI/NO)**. Per elezioni con liste:

```python
# TODO in views_scrutinio_aggregato.py:_aggregate_sezioni()

# For elections: aggregate by list
else:
    dati_schede = DatiScheda.objects.filter(
        dati_sezione__sezione__in=sezioni_qs,
        dati_sezione__consultazione=consultazione,
        scheda=scheda
    )

    liste_aggregate = {}
    for ds in dati_schede:
        if ds.voti and 'liste' in ds.voti:
            for lista, voti in ds.voti['liste'].items():
                liste_aggregate[lista] = liste_aggregate.get(lista, 0) + voti

    schede_aggregate.append({
        'scheda_id': scheda.id,
        'scheda_nome': scheda.nome,
        'voti': {'liste': liste_aggregate}
    })
```

### Performance Optimization

Per grandi dataset (>1000 sezioni), considerare:

1. **Caching Redis** dei dati aggregati
2. **Materialized Views** PostgreSQL per aggregazioni pre-calcolate
3. **Pagination** a livello sezioni (già implementato skip)

### Real-Time Updates

Implementare WebSocket per aggiornamenti live:

```javascript
// Pseudo-code
const ws = new WebSocket('wss://api.example.com/scrutinio/live');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    // Update affluenza in real-time
};
```

---

## 📚 File Modificati

### Backend
```
backend_django/
├── data/
│   ├── views_scrutinio_aggregato.py  [NUOVO] - View aggregazione
│   └── urls.py                        [MOD]  - Registrato endpoint
```

### Frontend
```
src/
├── ScrutinioAggregato.js  [NUOVO] - Componente mobile-first
└── App.js                 [MOD]  - Integrato menu e routing
```

---

## ✅ Checklist Go-Live

- [x] Backend endpoint implementato
- [x] Aggregazione SQL ottimizzata
- [x] Skip automatico livelli singoli
- [x] Frontend mobile-first
- [x] Permission check (delegati/sub-delegati)
- [x] Breadcrumbs navigazione
- [x] Header sticky + footer fisso
- [ ] Aggregazione liste/candidati (TODO elezioni)
- [ ] Test con dataset reale (>100 sezioni)
- [ ] Performance profiling query SQL
- [ ] Real-time updates (opzionale)

---

**Implementato il**: 7 Febbraio 2026
**Pronto per**: Scrutinio 27 Marzo 2026
**Target users**: Delegati e Sub-Delegati che supervisionano territori estesi
