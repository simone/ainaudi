# Phase 4: Frontend Permission System Implementation

## Obiettivo
Implementare nel frontend React il sistema di permessi granulari Django, aggiornando la visibilità del menu e la gestione degli errori 403.

---

## Modifiche App.js

### 1. Stato Permissions Aggiornato

**PRIMA:**
```javascript
const [permissions, setPermissions] = useState({
    sections: false,
    referenti: false,
    kpi: false,
    gestione_rdl: false
});
```

**DOPO:**
```javascript
const [permissions, setPermissions] = useState({
    // Nuovi permessi granulari Django
    is_superuser: false,
    can_manage_territory: false,
    can_view_kpi: false,
    can_manage_elections: false,
    can_manage_delegations: false,
    can_manage_rdl: false,
    has_scrutinio_access: false,
    can_view_resources: false,
    can_ask_to_ai_assistant: false,
    can_generate_documents: false,
    can_manage_incidents: false,

    // Info catena deleghe
    is_delegato: false,
    is_sub_delegato: false,
    is_rdl: false,

    // Backwards compatibility (deprecati)
    sections: false,
    referenti: false,
    kpi: false,
    gestione_rdl: false,
    upload_sezioni: false
});
```

### 2. Logica Caricamento Permessi

**PRIMA:**
```javascript
if (!perms.sections && !perms.referenti && !perms.kpi) {
    setError(`La mail ${user.email} non ha permessi per accedere ad alcuna sezione`);
    setTimeout(() => handleSignoutClick(), 2000);
} else if (perms.referenti || perms.kpi) {
    setActiveTab('dashboard');
} else if (perms.sections) {
    setActiveTab('sections');
}
```

**DOPO:**
```javascript
const hasAnyPermission = (
    perms.is_superuser ||
    perms.can_manage_territory ||
    perms.can_view_kpi ||
    perms.can_manage_elections ||
    perms.can_manage_delegations ||
    perms.can_manage_rdl ||
    perms.has_scrutinio_access ||
    perms.can_generate_documents ||
    perms.can_manage_incidents
);

if (!hasAnyPermission) {
    setError(`La mail ${user.email} non ha permessi per accedere ad alcuna sezione`);
    setTimeout(() => handleSignoutClick(), 2000);
} else if (perms.can_manage_delegations || perms.can_view_kpi || perms.is_superuser) {
    setActiveTab('dashboard');
} else if (perms.has_scrutinio_access) {
    setActiveTab('sections');
}
```

### 3. Menu Navigation - Mappatura Permessi

| Voce Menu | PRIMA | DOPO |
|-----------|-------|------|
| **HOME** | `permissions.referenti \|\| permissions.kpi` | `permissions.can_manage_delegations \|\| permissions.can_view_kpi \|\| permissions.is_superuser` |
| **TERRITORIO** | `user.is_superuser` | `permissions.is_superuser \|\| permissions.can_manage_territory` |
| **CONSULTAZIONE** | `permissions.referenti` | `permissions.can_manage_elections` |
| **DELEGATI** (dropdown) | `permissions.referenti \|\| pdf` | `permissions.can_manage_delegations \|\| permissions.can_generate_documents` |
| - Catena Deleghe | `permissions.referenti` | `permissions.can_manage_delegations` |
| - Designazioni | `permissions.referenti` | `permissions.can_manage_delegations` |
| - Template PDF | `permissions.referenti` | `permissions.can_generate_documents` |
| - Genera Moduli | `pdf` (hardcoded email) | `permissions.can_generate_documents` |
| **RDL** (dropdown) | `permissions.referenti \|\| permissions.gestione_rdl` | `permissions.can_manage_rdl \|\| permissions.can_manage_territory \|\| permissions.can_manage_delegations` |
| - Campagne | `permissions.referenti` | `permissions.can_manage_rdl` |
| - Gestione RDL | `permissions.gestione_rdl` | `permissions.can_manage_rdl` |
| - Gestione Sezioni | `permissions.referenti` | `permissions.can_manage_territory` |
| - Mappatura | `permissions.referenti` | `permissions.can_manage_delegations` |
| **SCRUTINIO** | `permissions.sections` | `permissions.has_scrutinio_access` |
| **DIRETTA (KPI)** | `permissions.kpi` | `permissions.can_view_kpi` |
| **RISORSE** | (tutti autenticati) | (tutti autenticati) |

### 4. Consultation Switcher

**PRIMA:**
```javascript
{permissions.referenti ? (
```

**DOPO:**
```javascript
{(permissions.can_manage_elections || permissions.can_manage_delegations || permissions.is_superuser) ? (
```

---

## Modifiche Client.js

### 1. Gestione Errori 403 - fetchWithCacheAndRetry

**AGGIUNTO:**
```javascript
// Handle permission errors (403) without retry
if (response.status === 403) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.error || errorData.detail || 'Non hai i permessi necessari per questa operazione');
    error.status = 403;
    error.isPermissionError = true;
    throw error;
}
```

**LOGICA RETRY:**
```javascript
// Don't retry permission errors
if (error.isPermissionError) {
    throw error;
}
```

### 2. Gestione Errori 403 - fetchAndInvalidate

**AGGIUNTO:**
```javascript
// Handle permission errors (403)
if (response.status === 403) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.error || errorData.detail || 'Non hai i permessi necessari per questa operazione');
    error.status = 403;
    error.isPermissionError = true;
    throw error;
}
```

### Vantaggi della Gestione 403

1. **Nessun retry inutile**: Gli errori di permesso non vengono ritentati (sono definitivi)
2. **Messaggi chiari**: Mostra il messaggio del backend o un default comprensibile
3. **Flag isPermissionError**: Permette ai componenti di gestire i 403 in modo speciale
4. **Parse messaggio backend**: Estrae `error` o `detail` dalla risposta JSON

---

## Backwards Compatibility

### Backend (`core/views.py`)

Il backend ritorna **ENTRAMBI** i set di flag:

```python
permissions = {
    # Nuovi flag granulari
    'is_superuser': False,
    'can_manage_territory': user.has_perm('core.can_manage_territory'),
    'can_view_kpi': user.has_perm('core.can_view_kpi'),
    # ... tutti i 10 permessi

    # Backwards compatibility (deprecare in futuro)
    'sections': user.has_perm('core.has_scrutinio_access'),
    'referenti': user.has_perm('core.can_manage_delegations'),
    'kpi': user.has_perm('core.can_view_kpi'),
    'upload_sezioni': user.has_perm('core.can_manage_territory'),
    'gestione_rdl': user.has_perm('core.can_manage_rdl'),

    # Info catena deleghe
    'is_delegato': is_delegato,
    'is_sub_delegato': is_sub_delegato,
    'is_rdl': is_rdl,
}
```

### Frontend (`App.js`)

Lo stato include **ENTRAMBI** i set:
- Nuovi flag specifici usati nel menu
- Vecchi flag mantenuti per eventuale compatibilità con codice esistente

---

## Test Checklist

### Test Menu Visibility

| Ruolo | HOME | TERRITORIO | CONSULTAZIONE | DELEGATI | RDL | SCRUTINIO | KPI | RISORSE |
|-------|------|------------|---------------|----------|-----|-----------|-----|---------|
| **Superuser** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Delegato** | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **SubDelegato (FIRMA_AUTENTICATA)** | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **SubDelegato (MAPPATURA)** | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **RDL** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| **KPI_VIEWER** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |

### Test Errori 403

1. **RDL prova ad accedere a KPI**
   - ❌ 403: "Non hai i permessi necessari per questa operazione"
   - ✓ Nessun retry (errore immediato)

2. **KPI_VIEWER prova a creare delega**
   - ❌ 403: Messaggio specifico dal backend
   - ✓ Componente riceve `error.isPermissionError = true`

3. **SubDelegato MAPPATURA prova a gestire elezioni**
   - ❌ 403: Permission denied
   - ✓ Menu Consultazione non visibile (prevenzione UI)

### Test Backwards Compatibility

1. **Backend ritorna vecchi flag**
   - ✓ `permissions.sections` popolato correttamente
   - ✓ `permissions.referenti` popolato correttamente
   - ✓ Nessun breaking change per componenti non aggiornati

2. **Frontend legge nuovi flag**
   - ✓ Menu usa `permissions.can_view_kpi` invece di `permissions.kpi`
   - ✓ Logica caricamento usa nuovi flag
   - ✓ Vecchi flag ancora disponibili nello stato

---

## Migrazioni Future

### Step 1: Rimuovere vecchi flag dal frontend (Fase 5)

1. Aggiornare tutti i componenti per usare solo nuovi flag
2. Rimuovere vecchi flag dallo stato `permissions` in `App.js`
3. Cercare e sostituire:
   - `permissions.sections` → `permissions.has_scrutinio_access`
   - `permissions.referenti` → `permissions.can_manage_delegations`
   - `permissions.kpi` → `permissions.can_view_kpi`
   - `permissions.gestione_rdl` → `permissions.can_manage_rdl`

### Step 2: Rimuovere vecchi flag dal backend (Fase 6)

1. Rimuovere backwards compatibility da `core/views.py`
2. Rimuovere test che verificano vecchi flag
3. Aggiornare documentazione

---

## Files Modificati

| File | Modifiche |
|------|-----------|
| `src/App.js` | Stato permissions, menu navigation, logica caricamento |
| `src/Client.js` | Gestione errori 403 senza retry |
| `PHASE_4_FRONTEND_PERMISSIONS.md` | Documentazione (questo file) |

---

## Commit

```
Feat: Phase 4 - Frontend permission system implementation

MODIFICHE APP.JS:
- Aggiornato stato permissions con tutti i nuovi flag Django
- Modificato caricamento permessi per usare nuovi flag granulari
- Aggiornato tutti i menu per usare permessi specifici
- Consultation switcher usa can_manage_elections

MODIFICHE CLIENT.JS:
- Gestione errori 403 senza retry
- Errori 403 mostrano messaggio backend o default chiaro
- Flag isPermissionError per handling speciale

BACKWARDS COMPATIBILITY:
- Mantenuti vecchi flag nello stato
- Backend ritorna entrambi i set
- Migrazione graduale senza breaking changes
```

---

## Prossimi Step: Phase 5 - Testing E2E

1. **Setup ambiente di test**
   - Creare utenti di test per ogni ruolo
   - Popolare database con dati di test

2. **Test manuali**
   - Login con ogni ruolo
   - Verificare visibilità menu corretta
   - Testare errori 403 per azioni non permesse

3. **Test automatici** (opzionale)
   - Jest tests per logica permessi
   - Cypress E2E per workflow completi

4. **Performance testing**
   - Verificare cache funziona correttamente
   - Monitorare chiamate API duplicate

5. **Security audit finale**
   - Verificare nessun bypass possibile
   - Test penetration per endpoint protetti
   - Audit logs per azioni sensibili
