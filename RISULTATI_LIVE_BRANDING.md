# Risultati Live - Branding Update

## Cambio Nome

La funzionalità precedentemente chiamata "Scrutinio Aggregato" è stata rinominata in **"Risultati Live"** per enfatizzare la natura real-time dei dati.

## Modifiche UI

### Menu Item
```jsx
// Prima
<i className="fas fa-chart-bar me-1"></i>
Scrutinio Aggregato

// Dopo
<i className="fas fa-chart-line me-1"></i>
Risultati Live 🟢
```

### Visual Identity

| Elemento | Valore | Descrizione |
|----------|--------|-------------|
| **Nome** | Risultati Live | Enfatizza aspetto real-time |
| **Icona** | fa-chart-line | Line chart (dinamico, live) |
| **Indicatore** | 🟢 Pallino verde animato | Indica aggiornamento real-time |
| **Animazione** | pulse 1.5s infinite | Opacità 1 → 0.4 → 1 |
| **Colore badge** | #28a745 (verde Bootstrap success) | Positivo, live, attivo |

### Confronto con "Diretta"

| Feature | Diretta | Risultati Live |
|---------|---------|----------------|
| Target | RDL (inserimento dati) | Delegati/SubDelegati (supervisione) |
| Badge | 🔴 Rosso (#dc3545) | 🟢 Verde (#28a745) |
| Icona | fa-chart-line | fa-chart-line |
| Permesso | has_scrutinio_access | can_view_kpi |
| Azione | Write (data entry) | Read (monitoring) |

## Motivo del Cambio

1. **"Risultati Live"** è più user-friendly e immediato
2. Enfatizza l'aspetto **real-time** dei dati aggregati
3. Differenzia chiaramente da "Scrutinio" (data entry) e "Diretta" (RDL)
4. Il pallino verde animato 🟢 comunica "sistema attivo, dati aggiornati"

## File Modificati

### Frontend
- `src/App.js` - Menu item label, icon, animated badge

### Documentazione
- `SCRUTINIO_AGGREGATO.md` - Titolo e riferimenti
- `SCRUTINIO_AGGREGATO_UX_IMPROVEMENTS.md` - Titolo e riferimenti

### File Tecnici (invariati)
- `backend_django/data/views_scrutinio_aggregato.py` - Nome tecnico mantenuto
- `backend_django/data/urls.py` - Route `/api/scrutinio/aggregato` invariato
- `src/ScrutinioAggregato.js` - Nome componente invariato

**Nota**: I nomi tecnici (file, funzioni, URL) rimangono invariati per compatibilità. Solo le stringhe visibili all'utente sono cambiate.

## User Flow

**Prima:**
1. Login → Menu → "Scrutinio Aggregato"

**Dopo:**
1. Login → Menu → "Risultati Live 🟢"

Il pallino verde animato attira l'attenzione e comunica immediatamente che i dati sono aggiornati in tempo reale.

---

**Implementato**: 2026-02-07
**Impact**: Migliore UX, naming più chiaro per gli utenti finali
