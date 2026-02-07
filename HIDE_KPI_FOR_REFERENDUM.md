# Nascondere KPI "Diretta" per Referendum

## Problema

Il componente KPI ("Diretta") è stato progettato per **elezioni con liste e candidati** (Europee, Politiche, Comunali), ma ora il sistema sta gestendo un **referendum** che ha una struttura completamente diversa:

### Elezioni (Europee/Politiche)
- Liste elettorali
- Candidati con preferenze
- Grafici per liste
- Grafici per candidati
- Voti di preferenza

### Referendum
- Solo SI/NO
- Niente liste
- Niente candidati
- Niente preferenze

## Root Cause

Il componente `Kpi.js`:
1. Carica candidati e liste che **non esistono** per referendum
2. Mostra grafici non pertinenti (liste, preferenze)
3. API `/api/election/candidates` e `/api/election/lists` ritornano `[]` per referendum
4. useEffect loop continua a provare a caricare dati inesistenti

## Soluzione

### Nascondere "Diretta" per Referendum

Per referendum, usiamo **solo "Risultati Live"** (ScrutinioAggregato) che è perfetto per:
- ✅ Affluenza
- ✅ Risultati SI/NO per scheda
- ✅ Navigazione territoriale gerarchica
- ✅ Dati aggregati real-time

## Implementazione

### 1. Logica di Visibilità

Usiamo il campo `consultazione.has_subdelegations` per distinguere:
- `has_subdelegations === false` → È un **referendum** (solo referendum, niente liste)
- `has_subdelegations !== false` → È **elezione** (Europee/Politiche/Comunali con liste)

### 2. App.js - Menu

**Prima:**
```javascript
{/* DIRETTA - sempre visibile */}
{consultazione && permissions.can_view_kpi && (
    <li className="nav-item">
        <a>Diretta 🔴</a>
    </li>
)}
```

**Dopo:**
```javascript
{/* DIRETTA - solo per elezioni (non referendum) */}
{consultazione && permissions.can_view_kpi && consultazione.has_subdelegations !== false && (
    <li className="nav-item">
        <a>Diretta 🔴</a>
    </li>
)}
```

### 3. Dashboard.js - Card

**Prima:**
```javascript
{
    id: 'diretta',
    permission: permissions.can_view_kpi && consultazione,
    ...
}
```

**Dopo:**
```javascript
{
    id: 'diretta',
    permission: permissions.can_view_kpi && consultazione && consultazione.has_subdelegations !== false,
    ...
}
```

## Comportamento Utente

### Per Referendum (has_subdelegations = false)

Menu:
- ✅ Risultati Live 🟢 (visibile)
- ❌ Diretta 🔴 (nascosto)

Dashboard:
- ✅ Card "Risultati Live" (visibile)
- ❌ Card "Diretta" (nascosta)

### Per Elezioni (has_subdelegations = true)

Menu:
- ✅ Risultati Live 🟢 (visibile)
- ✅ Diretta 🔴 (visibile)

Dashboard:
- ✅ Card "Risultati Live" (visibile)
- ✅ Card "Diretta" (visibile)

## Vantaggi

1. **UX chiara**: Non mostrare funzionalità inutili per referendum
2. **No errori**: Evita chiamate API per candidati/liste inesistenti
3. **Performance**: Meno chiamate API inutili
4. **Compatibilità**: Supporta sia referendum che elezioni con lo stesso codebase

## Alternative Considerate

### Opzione A: Adattare Kpi.js per Referendum ❌

**Pro:** Unico componente per tutto
**Contro:**
- Troppo complesso gestire due layout completamente diversi
- Codice esistente molto specifico per liste/candidati
- Difficile mantenere

### Opzione B: Creare KpiReferendum.js separato ❌

**Pro:** Componente dedicato per referendum
**Contro:**
- Duplicazione codice
- ScrutinioAggregato esiste già ed è perfetto

### Opzione C: Nascondere "Diretta" per Referendum ✅ (SCELTA)

**Pro:**
- Semplice da implementare
- Usa componente esistente (ScrutinioAggregato)
- Nessuna duplicazione codice
- Zero impatto su elezioni esistenti

**Contro:**
- Nessuno

## Testing

### Test Referendum

1. Login come delegato con consultazione referendum
2. Menu: ✅ Mostra solo "Risultati Live 🟢", nasconde "Diretta 🔴"
3. Dashboard: ✅ Mostra solo card "Risultati Live", nasconde "Diretta"
4. Click "Risultati Live": ✅ Mostra affluenza e SI/NO correttamente

### Test Elezioni

1. Login come delegato con consultazione elezioni (Europee/Politiche)
2. Menu: ✅ Mostra sia "Risultati Live 🟢" che "Diretta 🔴"
3. Dashboard: ✅ Mostra entrambe le card
4. Click "Diretta": ✅ Mostra liste, candidati, preferenze

## Note Backend

Il campo `has_subdelegations` è calcolato in `ConsultazioneElettorale.has_subdelegations()`:

```python
def has_subdelegations(self):
    """
    Referendum NON hanno sub-deleghe, solo Europee/Politiche/Comunali.
    """
    referendum_types = self.tipi_elezione.filter(tipo='REFERENDUM')
    # Se contiene SOLO referendum, NO sub-deleghe
    if referendum_types.exists() and self.tipi_elezione.count() == referendum_types.count():
        return False
    return True
```

Questo campo viene serializzato e inviato al frontend nell'oggetto `consultazione`.

## File Modificati

- `src/App.js` - Menu item "Diretta" condizionale
- `src/Dashboard.js` - Dashboard card "Diretta" condizionale

## File NON Modificati

- `src/Kpi.js` - Rimane invariato (usato solo per elezioni)
- `src/ScrutinioAggregato.js` - Rimane invariato (usato per referendum E elezioni)
- `backend_django/kpi/views.py` - Rimane invariato

---

**Implementato**: 2026-02-07
**Impact**: Referendum ora usano solo "Risultati Live", elezioni usano entrambi
**Benefit**: UX più chiara, nessuna confusione con componenti non pertinenti
