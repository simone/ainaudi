# Fix KPI is_active Field Error

## Problema

Errore 500 quando si accede a `/api/kpi/sezioni`:

```
django.core.exceptions.FieldError: Cannot resolve keyword 'is_active' into field.
Choices are: assigned_at, assigned_by_email, consultazione, consultazione_id, id,
notes, rdl_registration, rdl_registration_id, role, sezione, sezione_id
```

## Root Cause

Il codice in `kpi/views.py` stava filtrando `SectionAssignment` con `is_active=True`, ma questo campo **non esiste più** nel modello.

Il campo `is_active` è stato rimosso dalla migrazione `0007_fix_assignment_fk_to_rdl.py`:

```python
# Step 5: Remove is_active field
migrations.RemoveField(
    model_name='sectionassignment',
    name='is_active',
),
```

## Fix Applicato

### 1. kpi/views.py linea 48-51 (KpiStatsView)

**Prima:**
```python
assigned_sections = SectionAssignment.objects.filter(
    consultazione=consultazione,
    is_active=True  # ❌ Campo non esiste
).values('sezione').distinct().count()
```

**Dopo:**
```python
assigned_sections = SectionAssignment.objects.filter(
    consultazione=consultazione  # ✅ Rimosso is_active
).values('sezione').distinct().count()
```

### 2. kpi/views.py linea 106-110 (KpiSezioniView)

**Prima:**
```python
assignment = SectionAssignment.objects.filter(
    sezione=sezione,
    consultazione=consultazione,
    is_active=True  # ❌ Campo non esiste
).select_related('rdl_registration').first()
```

**Dopo:**
```python
assignment = SectionAssignment.objects.filter(
    sezione=sezione,
    consultazione=consultazione  # ✅ Rimosso is_active
).select_related('rdl_registration').first()
```

## Impatto

### Prima del Fix
- ❌ `/api/kpi/sezioni` → 500 Internal Server Error
- ❌ `/api/kpi/stats` → 500 Internal Server Error (se usava assigned_sections)
- ❌ KPI dashboard non caricava

### Dopo il Fix
- ✅ `/api/kpi/sezioni` → 200 OK
- ✅ `/api/kpi/stats` → 200 OK
- ✅ KPI dashboard funziona correttamente

## Note

Il campo `is_active` non è più necessario perché:
1. Le assignment sono sempre "attive" per definizione
2. Se un'assignment non è più valida, viene eliminata dal database
3. Il modello `SectionAssignment` ora usa una unique constraint su `(sezione, consultazione, rdl_registration)` per prevenire duplicati

Se in futuro c'è bisogno di distinguere assignment attive da inattive, si dovrebbe:
- Aggiungere un nuovo campo booleano con migrazione
- Aggiornare i segnali che creano/eliminano assignment
- NON riutilizzare il nome `is_active` per evitare confusione con il campo rimosso

## File Modificati

- `backend_django/kpi/views.py` - Rimosso `is_active=True` da 2 query

## Testing

```bash
# Test endpoint KPI
curl -H "Authorization: Bearer TOKEN" http://localhost:3001/api/kpi/sezioni
→ 200 OK ✅

curl -H "Authorization: Bearer TOKEN" http://localhost:3001/api/kpi/stats
→ 200 OK ✅

# Test frontend
# Login come delegato → Menu "Diretta" → Verifica che la pagina carichi
```

---

**Fixed**: 2026-02-07
**Impact**: KPI dashboard ora funziona correttamente senza errori 500
