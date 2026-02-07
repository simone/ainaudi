# Mappatura Gerarchica - Implementation

## Overview

Implemented hierarchical navigation for RDL-to-section assignment (mappatura) to handle complex territorial scenarios with multiple regions, provinces, municipalities, or districts.

## Problem

The existing flat list mappatura works well for small territories (single city or district), but becomes unmanageable for:
- Multiple municipalities
- Multiple districts within a city
- Province-wide or region-wide territories

User request:
> "la mappatura finché hai una sola città va bene o un solo municipio va bene, ma se hai più municipi o una città con i municipi, o una o più provincia, o una o più regioni, allora l'elenco di sezioni diventa complesso. quindi siggerisco una navigazione logica per regione, ma se ne vedi una salta, per provincia, ma se ne vedi una salta, per comune, e se ne vedi uno salta, per municipio e se ne vedi uno salta, per sezione una volta che si vedono le sezioni le assegni..."

## Solution

Hierarchical drill-down navigation with auto-skip logic:

```
Regione → Provincia → Comune → Municipio → Sezione
   ↓          ↓          ↓          ↓          ↓
 Skip if    Skip if    Skip if    Skip if    Assign
 only 1     only 1     only 1     only 1     RDL here
```

## Architecture

### Backend API

**File:** `backend_django/data/views_mappatura_gerarchica.py`

**Endpoint:** `GET /api/mappatura/gerarchica/`

**Query Parameters:**
- `consultazione_id` (required): ID of the consultazione
- `level` (required): Current navigation level
  - `regione` - List regions
  - `provincia` - List provinces in a region
  - `comune` - List municipalities in a province
  - `municipio` - List districts in a municipality
  - `sezione` - List sections in a municipality (leaf level)
- `regione_id` (conditional): Filter by region (required for provincia level)
- `provincia_id` (conditional): Filter by province (required for comune level)
- `comune_id` (conditional): Filter by municipality (required for municipio/sezione level)
- `municipio_id` (optional): Filter by district (optional for sezione level)
- `search` (optional): Search term for filtering

**Response Format:**
```json
{
  "level": "comune",
  "items": [
    {
      "id": 123,
      "nome": "Roma",
      "codice": "058091",
      "has_municipi": true,
      "totale_sezioni": 1200,
      "sezioni_assegnate": 850,
      "sezioni_non_assegnate": 350,
      "percentuale_assegnazione": 70.8
    }
  ],
  "summary": {
    "totale_sezioni": 1200,
    "sezioni_assegnate": 850,
    "sezioni_non_assegnate": 350,
    "percentuale_assegnazione": 70.8
  }
}
```

**For sezione level:**
```json
{
  "level": "sezione",
  "items": [
    {
      "id": 456,
      "numero": 123,
      "denominazione": "Scuola Media Garibaldi",
      "indirizzo": "Via Roma 1",
      "municipio": "Municipio I",
      "is_assegnata": true,
      "rdl_effettivo": {
        "id": 789,
        "nome": "Mario",
        "cognome": "Rossi",
        "email": "mario.rossi@example.com",
        "telefono": "3331234567"
      },
      "rdl_supplente": null
    }
  ],
  "summary": {...}
}
```

**Permission:** `CanManageRDL` (same as existing mappatura endpoints)

**Territory Filtering:** Uses `get_sezioni_filter_for_user()` to respect delegation hierarchy

**Query Optimization:**
- Uses `Exists()` subquery for assignment filtering (efficient for large datasets)
- Aggregate statistics calculated per entity
- Summary totals computed in Python (not SQL) for flexibility

### Frontend Component

**File:** `src/MappaturaGerarchica.js`

**Props:**
- `client` - API client
- `consultazioneId` - ID of active consultazione
- `onSezioneSelect` - Callback when user clicks a sezione to assign RDL
  - Signature: `onSezioneSelect(sezione)` where `sezione` includes:
    - `id`, `numero`, `denominazione`, `indirizzo`
    - `is_assegnata`, `rdl_effettivo`, `rdl_supplente`

**Features:**
- Hierarchical drill-down with breadcrumb navigation
- Auto-skip logic: If only 1 entity at a level, automatically navigate to it
- Search functionality at each level
- Summary card showing assignment statistics
- Visual badges:
  - Green badge: Section assigned (shows RDL name)
  - Yellow badge: Section unassigned
- Mobile-first responsive design
- Loading states and error handling

**State Management:**
```javascript
const [data, setData] = useState(null);
const [path, setPath] = useState([]);  // Navigation path for breadcrumbs
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [searchTerm, setSearchTerm] = useState('');
```

**Navigation Flow:**
1. Start at `regione` level
2. User clicks a region → Navigate to `provincia` level with `regione_id`
3. Auto-skip if only 1 provincia → Navigate to `comune` level
4. User clicks a municipality → Check if it has `has_municipi`
   - Yes: Navigate to `municipio` level
   - No: Navigate directly to `sezione` level
5. At sezione level, clicking a section calls `onSezioneSelect(sezione)`

### Client API

**File:** `src/Client.js`

**Added Method:**
```javascript
mappatura: {
    // ... existing methods

    gerarchica: async (params = {}) => {
        // Builds query string from params
        // Calls GET /api/mappatura/gerarchica/
        // Returns hierarchical data with assignment stats
    }
}
```

**Parameters:**
- `consultazione_id` (required)
- `level` (default: 'regione')
- `regione_id`, `provincia_id`, `comune_id`, `municipio_id` (conditional)
- `search` (optional)

**Caching:** 30 second TTL using `fetchWithCacheAndRetry`

### URL Configuration

**File:** `backend_django/data/urls.py`

**Added Route:**
```python
# Mappatura URLs (mounted at /api/mappatura/ in main urls.py)
mappatura_urlpatterns = [
    # ... existing routes
    path('gerarchica/', MappaturaGerarchicaView.as_view(), name='mappatura-gerarchica'),
]
```

**Full URL:** `http://localhost:3001/api/mappatura/gerarchica/`

## Integration with Existing Mappatura

To integrate MappaturaGerarchica with the existing Mappatura component:

### Option A: Add as Tab (Recommended)

**File:** `src/Mappatura.js`

```javascript
const [activeTab, setActiveTab] = useState('sezioni'); // Add: 'gerarchica'

// In render:
<ul className="nav nav-tabs">
    <li className="nav-item">
        <button
            className={`nav-link ${activeTab === 'sezioni' ? 'active' : ''}`}
            onClick={() => setActiveTab('sezioni')}
        >
            Vista Plessi
        </button>
    </li>
    <li className="nav-item">
        <button
            className={`nav-link ${activeTab === 'gerarchica' ? 'active' : ''}`}
            onClick={() => setActiveTab('gerarchica')}
        >
            Vista Gerarchica
        </button>
    </li>
    <li className="nav-item">
        <button
            className={`nav-link ${activeTab === 'rdl' ? 'active' : ''}`}
            onClick={() => setActiveTab('rdl')}
        >
            Vista RDL
        </button>
    </li>
</ul>

{activeTab === 'sezioni' && (
    // Existing plessi view
)}

{activeTab === 'gerarchica' && (
    <MappaturaGerarchica
        client={client}
        consultazioneId={consultazioneId}
        onSezioneSelect={(sezione) => {
            // Open assignment modal
            openAssignmentModal(sezione, 'EFFETTIVO');
        }}
    />
)}

{activeTab === 'rdl' && (
    // Existing RDL view
)}
```

### Option B: Replace ViewMode (Alternative)

**File:** `src/Mappatura.js`

Change `viewMode` state to include 'gerarchica':

```javascript
const [viewMode, setViewMode] = useState('grouped'); // 'grouped' | 'flat' | 'gerarchica'

// In toolbar:
<div className="btn-group">
    <button
        className={`btn btn-sm ${viewMode === 'grouped' ? 'btn-primary' : 'btn-outline-primary'}`}
        onClick={() => setViewMode('grouped')}
    >
        <i className="fas fa-th-list"></i> Raggruppate
    </button>
    <button
        className={`btn btn-sm ${viewMode === 'flat' ? 'btn-primary' : 'btn-outline-primary'}`}
        onClick={() => setViewMode('flat')}
    >
        <i className="fas fa-list"></i> Lista
    </button>
    <button
        className={`btn btn-sm ${viewMode === 'gerarchica' ? 'btn-primary' : 'btn-outline-primary'}`}
        onClick={() => setViewMode('gerarchica')}
    >
        <i className="fas fa-sitemap"></i> Gerarchica
    </button>
</div>

{viewMode === 'gerarchica' ? (
    <MappaturaGerarchica ... />
) : (
    // Existing plessi/flat view
)}
```

## Performance Considerations

### Backend Query Optimization

**For large territories (province/region-wide):**

The view uses efficient aggregation:
- Single query per level to fetch entities
- Single query to prefetch assignments (dictionary lookup pattern)
- `Exists()` subquery for filtering assigned/unassigned sections
- No N+1 problem

**Expected Performance:**
- Regione level: ~50ms (5-20 regions)
- Provincia level: ~100ms (10-100 provinces)
- Comune level: ~200ms (100-8000 municipalities)
- Municipio level: ~50ms (1-20 districts)
- Sezione level: ~300ms (100-5000 sections per municipality)

**For very large municipalities (>1000 sections):**
- Response may reach 1-2s
- Consider pagination if needed (add `limit`/`offset` params)
- Search functionality helps narrow results

### Frontend Optimization

**Component Performance:**
- Search is client-side filtered (instant)
- Auto-skip reduces number of clicks
- Breadcrumb navigation allows quick backtracking
- Cards are virtualized for large lists (CSS scrolling)

**Cache Strategy:**
- 30s TTL for hierarchical data
- Invalidate on assignment/removal via `mappatura.invalidateCache()`
- Summary stats cached with data

## Auto-Skip Logic

The auto-skip logic is implemented **in the component** (not backend):

```javascript
useEffect(() => {
    if (data && data.items.length === 1 && !isLeafLevel(data.level)) {
        // Auto-navigate to the single item
        handleItemClick(data.items[0]);
    }
}, [data]);

const isLeafLevel = (level) => {
    return level === 'sezione';
};
```

**Rationale:**
- Frontend can decide when to auto-skip (e.g., skip on initial load, but not after search)
- Backend remains stateless and simple
- User can still see breadcrumb trail showing skipped levels

## Testing

### Manual Testing Scenarios

**1. Province-wide delegation (e.g., Roma)**
- Start: See 1 regione (Lazio)
- Auto-skip: Navigate to 1 provincia (Roma)
- See: 121 comuni (list)
- Click: Roma Capitale
- See: 15 municipi
- Click: Municipio I
- See: ~200 sezioni
- Click: Sezione 123
- Modal: Assign RDL

**2. Region-wide delegation (e.g., Toscana)**
- Start: See 1 regione (Toscana)
- Auto-skip: Navigate to 10 province
- Click: Firenze
- See: 42 comuni
- Click: Firenze
- See: 5 municipi (Q1-Q5)
- Click: Q1
- See: ~150 sezioni

**3. Single municipality (e.g., Pisa)**
- Start: See 1 regione (Toscana)
- Auto-skip: Navigate to 1 provincia (Pisa)
- Auto-skip: Navigate to 1 comune (Pisa)
- Auto-skip: Navigate to sezioni (no municipi)
- See: ~100 sezioni
- Click: Assign

**4. Search functionality**
- At comuni level: Search "Fiesole" → Filter list
- At sezioni level: Search "Scuola" → Filter by denominazione

**5. Assignment statistics**
- Summary card shows real-time stats:
  - Total sections
  - Assigned (green badge)
  - Unassigned (yellow badge)
  - Completion percentage
- Stats aggregate up the hierarchy

### Backend API Testing

```bash
# Test regione level
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:3001/api/mappatura/gerarchica/?consultazione_id=1&level=regione"

# Test provincia level
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:3001/api/mappatura/gerarchica/?consultazione_id=1&level=provincia&regione_id=12"

# Test sezione level with search
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:3001/api/mappatura/gerarchica/?consultazione_id=1&level=sezione&comune_id=58091&search=Garibaldi"
```

## Future Enhancements

### Short-term (if needed):
1. **Pagination** for sezione level (if >1000 sections)
2. **Export CSV** of current hierarchy view
3. **Bulk assignment** from gerarchica view
4. **Visual map** integration (show territory on map)

### Long-term:
1. **Smart suggestions**: Recommend RDL based on proximity/availability
2. **Drag-and-drop**: Drag RDL onto section card to assign
3. **Copy assignments**: Clone mappatura from previous consultazione

## Migration Path

**No breaking changes required:**
- Existing `/api/mappatura/sezioni` and `/api/mappatura/rdl` unchanged
- New `/api/mappatura/gerarchica` is additive
- Mappatura component can coexist with MappaturaGerarchica
- Users can choose which view to use

**Rollout:**
1. Deploy backend endpoint (zero risk, not called yet)
2. Deploy Client.js with new method
3. Deploy MappaturaGerarchica component (isolated)
4. Integrate as tab in Mappatura.js
5. Announce to users with tutorial

## Files Modified

**Backend:**
1. `backend_django/data/views_mappatura_gerarchica.py` (NEW)
2. `backend_django/data/urls.py` (added route)

**Frontend:**
3. `src/Client.js` (added `mappatura.gerarchica()` method)
4. `src/MappaturaGerarchica.js` (NEW)

**Next step (to integrate):**
5. `src/Mappatura.js` (add tab or viewMode option)

**Documentation:**
6. `MAPPATURA_GERARCHICA_IMPLEMENTATION.md` (NEW)

---

**Implemented:** 2026-02-07
**Status:** Backend and component ready, integration pending
**User Benefit:** Handles complex multi-municipality/province territories with ease

