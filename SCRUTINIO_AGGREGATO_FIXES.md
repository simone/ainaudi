# Scrutinio Aggregato - Issue Resolution

## Problem

The `/api/scrutinio/aggregato` endpoint was returning 403 Forbidden errors even for authenticated users with Delegato roles.

## Root Cause

The endpoint was using the wrong permission class. Initially used `HasScrutinioAccess` which is meant for RDL users entering data, but scrutinio aggregato is for **supervision** (viewing aggregated data), not data entry.

## Permission Semantics

- **`has_scrutinio_access`**: For RDL users who **enter** section data (data entry)
- **`can_view_kpi`**: For Delegati/SubDelegati who **view** aggregated data (supervision/monitoring)

Scrutinio aggregato is a **read-only supervision tool**, similar to KPI dashboards, so it should use `can_view_kpi`.

## Fixes Applied

### 1. Changed Permission Class (data/views_scrutinio_aggregato.py:15,44)

**Before:**
```python
from core.permissions import HasScrutinioAccess

class ScrutinioAggregatoView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]
```

**After:**
```python
from core.permissions import CanViewKPI

class ScrutinioAggregatoView(APIView):
    permission_classes = [permissions.IsAuthenticated, CanViewKPI]
```

### 2. Updated Role Permissions (delegations/signals.py:145-154)

Added `can_view_kpi` to DELEGATE and SUBDELEGATE roles (kept `has_scrutinio_access` only for RDL):

```python
role_permissions = {
    RoleAssignment.Role.DELEGATE: [
        'can_manage_delegations',
        'can_manage_rdl',
        'can_view_resources',
        'can_generate_documents',
        'can_view_kpi',  # ← ADDED: Accesso KPI e scrutinio aggregato
    ],
    RoleAssignment.Role.SUBDELEGATE: [
        'can_manage_rdl',
        'can_view_resources',
        'can_view_kpi',  # ← ADDED: Accesso KPI e scrutinio aggregato
    ],
    RoleAssignment.Role.RDL: [
        'has_scrutinio_access',  # ← UNCHANGED: Data entry only
        'can_view_resources',
    ],
}
```

### 3. Fixed TypeError in Aggregation Logic (data/views_scrutinio_aggregato.py:403-404)

**Problem:** Some DatiScheda records have `voti={'si': None, 'no': None}` (explicitly set to None), causing `TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'`.

**Before:**
```python
totale_si += ds.voti.get('si', 0)
totale_no += ds.voti.get('no', 0)
```

**After:**
```python
# Handle None values explicitly (some records may have voti={'si': None})
totale_si += ds.voti.get('si', 0) or 0
totale_no += ds.voti.get('no', 0) or 0
```

## Testing

### Test User Updated

Updated test delegato permissions:
- Email: `test.delegato@example.com`
- Role: DELEGATE (Rappresentante del Partito)
- Territory: Regione Lazio (5314 sezioni)
- Permissions: **`can_view_kpi: True`**, `has_scrutinio_access: False` ✓

### Endpoint Verification

```bash
GET /api/scrutinio/aggregato?consultazione_id=1
Authorization: Bearer <JWT_TOKEN>

Response: 200 OK
{
  "level": "province",
  "consultazione_id": 1,
  "regione_id": 12,
  "breadcrumbs": [
    {"tipo": "root", "nome": "Italia"},
    {"tipo": "regione", "id": 12, "nome": "Lazio"}
  ],
  "items": [
    {
      "id": 69,
      "tipo": "provincia",
      "nome": "Frosinone",
      "sigla": "FR",
      "totale_sezioni": 504,
      "sezioni_complete": 0,
      "totale_elettori": 0,
      "totale_votanti": 0,
      "affluenza_percentuale": 0,
      "schede": [...]
    },
    ...
  ]
}
```

**Note:** The endpoint correctly auto-skipped the "regioni" level because the test user only has access to 1 region (Lazio), jumping directly to the "province" level.

## Migration Impact

### For Existing Users

Check if DELEGATE and SUBDELEGATE roles already have `can_view_kpi` in production. If not:

**Option A: Trigger signal manually (recommended for dev/test)**
```python
# Update the Delegato/SubDelega records to re-trigger signals
from delegations.models import Delegato, SubDelega

for delegato in Delegato.objects.all():
    delegato.save()  # Re-trigger post_save signal

for subdelega in SubDelega.objects.filter(is_attiva=True):
    subdelega.save()  # Re-trigger post_save signal
```

**Option B: Manual permission assignment (for production)**
```python
from core.models import User
from django.contrib.auth.models import Permission
from delegations.models import Delegato, SubDelega

permission = Permission.objects.get(codename='can_view_kpi', content_type__app_label='core')

# Grant to all delegati
for delegato in Delegato.objects.all():
    if delegato.user:
        delegato.user.user_permissions.add(permission)

# Grant to all sub-delegati
for subdelega in SubDelega.objects.filter(is_attiva=True):
    if subdelega.sub_delegato:
        subdelega.sub_delegato.user_permissions.add(permission)
```

### For New Users

All new Delegato and SubDelegato users will automatically receive `can_view_kpi` permission via signals when their records are created.

## Permission Summary Table

| Role | has_scrutinio_access | can_view_kpi | Purpose |
|------|---------------------|--------------|---------|
| **RDL** | ✅ Yes | ❌ No | Enter section data (form input) |
| **DELEGATE** | ❌ No | ✅ Yes | View aggregated data + KPI |
| **SUBDELEGATE** | ❌ No | ✅ Yes | View aggregated data + KPI |

## Related Files

- `backend_django/data/views_scrutinio_aggregato.py` - Changed permission from HasScrutinioAccess to CanViewKPI
- `backend_django/delegations/signals.py` - Added can_view_kpi to DELEGATE/SUBDELEGATE roles
- `backend_django/core/permissions.py` - CanViewKPI permission class definition
- `scripts/create-test-delegato.sh` - Helper script to create test delegato
- `scripts/test-aggregato-with-token.sh` - Helper script to test endpoint with JWT

## Next Steps

1. ✅ Test frontend integration (ScrutinioAggregato component)
2. ✅ Verify drill-down navigation works (Provincia → Comune → Municipio → Sezione)
3. ✅ Test auto-skip logic for single entities
4. ⬜ Update existing production users with can_view_kpi permission (if needed)
5. ⬜ Add aggregation logic for liste/candidati (currently only SI/NO referendum works)

---

**Fixed:** 2026-02-07
**Status:** ✅ Ready for testing
**Impact:** All Delegati and SubDelegati with `can_view_kpi` can now access hierarchical scrutinio aggregato
