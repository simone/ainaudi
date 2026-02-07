# Rimozione Logica hasContributions

## Problema

La visualizzazione delle KPI (menu "Diretta" e dashboard) era condizionata dalla presenza di contributi nel database tramite la logica `hasContributions`. Questo causava:

1. **UX confusa**: L'utente con permessi `can_view_kpi` non vedeva il menu "Diretta" finché non c'erano dati
2. **Chiamate API extra**: Polling ogni 60 secondi per verificare se ci sono contributi
3. **Complessità inutile**: La presenza di permessi dovrebbe essere sufficiente per mostrare le sezioni

## Soluzione

Rimosso completamente il check `hasContributions`. Ora le KPI sono sempre visibili per gli utenti con permesso `can_view_kpi`, indipendentemente dalla presenza di dati nel database.

## Modifiche Applicate

### 1. App.js

**Rimosso state:**
```javascript
// Prima
const [hasContributions, setHasContributions] = useState(false);

// Dopo
// Rimosso completamente
```

**Rimosso useEffect di polling:**
```javascript
// Prima (linee 240-266)
useEffect(() => {
    if (client && isAuthenticated && permissions.can_view_kpi && consultazione) {
        const checkContributions = () => {
            client.kpi.hasContributions?.().then(data => {
                // ... logic
            });
        };
        checkContributions();
        const interval = setInterval(checkContributions, 60000);
        return () => clearInterval(interval);
    }
}, [client, isAuthenticated, permissions.can_view_kpi, consultazione]);

// Dopo
// Rimosso completamente
```

**Semplificata condizione menu:**
```javascript
// Prima
{consultazione && permissions.can_view_kpi && hasContributions && (
    <li className="nav-item">
        <a>Diretta</a>
    </li>
)}

// Dopo
{consultazione && permissions.can_view_kpi && (
    <li className="nav-item">
        <a>Diretta</a>
    </li>
)}
```

**Rimosso prop Dashboard:**
```javascript
// Prima
<Dashboard
    user={user}
    permissions={permissions}
    consultazione={consultazione}
    hasContributions={hasContributions}
    onNavigate={activate}
/>

// Dopo
<Dashboard
    user={user}
    permissions={permissions}
    consultazione={consultazione}
    onNavigate={activate}
/>
```

### 2. Dashboard.js

**Aggiornata signature:**
```javascript
// Prima
function Dashboard({ user, permissions, consultazione, hasContributions, onNavigate }) {

// Dopo
function Dashboard({ user, permissions, consultazione, onNavigate }) {
```

**Semplificata permission check sezione Diretta:**
```javascript
// Prima
permission: permissions.can_view_kpi && consultazione && hasContributions,

// Dopo
permission: permissions.can_view_kpi && consultazione,
```

## Impatto

### Prima della Modifica

```
Utente con can_view_kpi = true
└─ Login
   └─ API call: /api/kpi/has-contributions → false
      └─ Menu "Diretta" NASCOSTO ❌
      └─ Dashboard card "Diretta" NASCOSTA ❌
      └─ Polling ogni 60s per controllare se ci sono dati
```

### Dopo la Modifica

```
Utente con can_view_kpi = true
└─ Login
   └─ Menu "Diretta" VISIBILE ✅
   └─ Dashboard card "Diretta" VISIBILE ✅
   └─ Nessun polling (performance migliorata)
   └─ Se non ci sono dati, la pagina KPI mostrerà "Nessun dato disponibile"
```

## Vantaggi

1. **UX più chiara**: Se hai il permesso, vedi la funzionalità
2. **Performance**: Eliminato polling ogni 60 secondi
3. **Semplicità**: Meno stato da gestire nel frontend
4. **Consistenza**: Allineato con le altre sezioni (non si nascondono se vuote)

## Comportamento KPI con Zero Dati

La pagina KPI gestisce già correttamente il caso di zero dati:
- Mostra placeholder "Nessun dato disponibile"
- Non genera errori
- Permette all'utente di esplorare l'interfaccia

Questo è preferibile al nascondere completamente la sezione.

## File Modificati

- `src/App.js` - Rimosso state, useEffect, condizione menu, prop Dashboard
- `src/Dashboard.js` - Rimosso parametro, semplificata permission check

## Testing

### Verifica Comportamento

1. **Login come delegato** (con `can_view_kpi = true`)
   - ✅ Menu "Diretta 🔴" visibile immediatamente
   - ✅ Dashboard card "Diretta" visibile

2. **Click su "Diretta"**
   - ✅ Pagina KPI carica
   - Se zero dati: mostra "Nessun dato disponibile"
   - Se ci sono dati: mostra grafici e statistiche

3. **Performance**
   - ✅ Nessuna chiamata API `/api/kpi/has-contributions`
   - ✅ Nessun polling ogni 60 secondi
   - ✅ Ridotto network traffic

### Test User

```bash
# Login come test.delegato@example.com
# Verificare:
# - Menu "Diretta" visibile
# - Dashboard card "Diretta" visibile
# - Nessuna chiamata API has-contributions in DevTools Network tab
```

## Note

La logica `hasContributions` era stata introdotta per evitare di confondere gli utenti mostrando una pagina KPI vuota. Tuttavia:

- È più confuso nascondere completamente una funzionalità
- L'utente potrebbe pensare di non avere i permessi corretti
- È standard mostrare placeholder "nessun dato" invece di nascondere le sezioni

La nuova implementazione è più in linea con le best practice UX.

---

**Implementato**: 2026-02-07
**Impact**: KPI sempre visibili per utenti con permessi, migliore UX e performance
