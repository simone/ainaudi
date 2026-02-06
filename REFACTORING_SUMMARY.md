# Refactoring Summary: DesignazioneRDL "1 per Seggio"

## Overview

Successfully refactored `DesignazioneRDL` model from **"1 record per RDL"** (separate records for effettivo and supplente) to **"1 record per seggio"** (one record containing both effettivo and supplente).

## Changes Made

### 1. Backend Models (`backend_django/delegations/models.py`)

#### DesignazioneRDL Model
**BEFORE:**
- Had `ruolo` field ('EFFETTIVO' | 'SUPPLENTE')
- Had individual RDL fields: cognome, nome, email, telefono, luogo_nascita, data_nascita, domicilio
- Unique constraint: `['sezione', 'ruolo']` per stato CONFERMATA

**AFTER:**
- Removed `ruolo` field
- Removed individual RDL fields
- Added two FK relationships:
  - `effettivo_rdl` → FK to `campaign.RdlRegistration` (nullable)
  - `supplente_rdl` → FK to `campaign.RdlRegistration` (nullable)
- Added `batch_pdf` → FK to `BatchGenerazioneDocumenti` (nullable)
- Unique constraint: `['sezione']` per stato CONFERMATA (1 designazione per seggio)
- New constraint: At least one between `effettivo_rdl` and `supplente_rdl` must be set

#### BatchGenerazioneDocumenti Model
**BEFORE:**
- Had FK to `SubDelega`
- States: BOZZA, GENERATO, INVIATO

**AFTER:**
- Has FK to `ConsultazioneElettorale` (replaced sub_delega)
- States: BOZZA, GENERATO, **APPROVATO**, INVIATO
- Added `approva(user_email)` method that:
  - Sets batch stato to APPROVATO
  - Updates all linked designazioni from BOZZA to CONFERMATA

### 2. Migration (`backend_django/delegations/migrations/0012_refactor_designazione_rdl_to_per_station.py`)

- **DeleteModel**: Drops old DesignazioneRDL table
- **CreateModel**: Creates new DesignazioneRDL with new structure
- **AddConstraints**: Adds unique + check constraints
- **AlterField**: Updates BatchGenerazioneDocumenti.stato to include APPROVATO
- **AddField**: Adds consultazione FK to BatchGenerazioneDocumenti

**⚠️ IMPORTANT:** This is a destructive migration that **drops all existing designazioni**. Per user request: "Cancella tutto e riparte da zero".

### 3. Serializers (`backend_django/delegations/serializers.py`)

#### DesignazioneRDLSerializer (Read)
```python
# Nested RDL data
effettivo = SerializerMethodField()  # Returns {id, cognome, nome, email, telefono} or None
supplente = SerializerMethodField()  # Returns {id, cognome, nome, email, telefono} or None

# Removed fields: ruolo, ruolo_display, cognome, nome, email, telefono, etc.
```

#### DesignazioneRDLCreateSerializer (Write)
```python
# Input fields
effettivo_email = EmailField(required=False)
supplente_email = EmailField(required=False)

# Validates both emails
# Looks up RdlRegistration with status='APPROVED'
# Creates DesignazioneRDL with FK relationships
```

#### BatchGenerazioneDocumentiSerializer
- Changed from `sub_delegato_nome` to `consultazione_nome`
- Now references consultazione instead of sub_delega

### 4. Views (`backend_django/delegations/views.py`)

#### carica_mappatura Endpoint (MAJOR CHANGE)
**BEFORE:**
- Processed each SectionAssignment individually
- Created 1 DesignazioneRDL per assignment (effettivo or supplente)
- Simple duplicate check by (sezione, ruolo, email)

**AFTER:**
- Groups SectionAssignments by sezione: `{sezione_id: {'effettivo': rdl, 'supplente': rdl}}`
- Creates 1 DesignazioneRDL per seggio with both roles
- Smart handling:
  - **BOZZE**: Always overwrite
  - **CONFERMATE**:
    - If identical → skip
    - If different → warning (user must delete manually)
- Returns: `{created, updated, skipped, warnings[], errors[], total}`

#### sezioni_disponibili Endpoint
- Now checks `designazione.effettivo_rdl` and `designazione.supplente_rdl`
- Instead of filtering by ruolo

#### rdl_disponibili Endpoint
- Queries `DesignazioneRDL.objects.filter(effettivo_rdl=reg)`
- Instead of filtering by email + ruolo

#### BatchGenerazioneDocumentiViewSet
**NEW Endpoints:**
- `POST /api/deleghe/batch/` - Create batch, link designazioni, update `batch_pdf` FK
- `POST /api/deleghe/batch/{id}/genera/` - Generate PDF (placeholder for documents app integration)
- `POST /api/deleghe/batch/{id}/approva/` - Approve batch → calls `batch.approva()` → confirms all designazioni

### 5. Signals (`backend_django/delegations/signals.py`)

**BEFORE:**
- `provision_rdl_user()` - Provisioned user based on `instance.email` (one RDL)

**AFTER:**
- `provision_rdl_users()` - Provisions users for BOTH:
  - `instance.effettivo_rdl.email` (if present)
  - `instance.supplente_rdl.email` (if present)
- Removes pre_save hook (no longer tracking email changes on DesignazioneRDL)

### 6. Admin (`backend_django/delegations/admin.py`)

#### DesignazioneRDLInline
- Changed columns from `['sezione', 'ruolo', 'cognome', 'nome', 'email', 'stato']`
- To: `['sezione', 'effettivo_display', 'supplente_display', 'stato']`

#### DesignazioneRDLAdmin
- **list_display**: Now shows `effettivo_display` and `supplente_display` columns
- **search_fields**: Searches in `effettivo_rdl__*` and `supplente_rdl__*`
- **autocomplete_fields**: Added `effettivo_rdl`, `supplente_rdl`, `batch_pdf`
- **fieldsets**: Replaced individual RDL fields with FK fields
- **Removed**: `ruolo`, `cognome`, `nome`, `email`, `telefono`, etc.

#### BatchGenerazioneDocumentiAdmin
- Changed from `sub_delega` to `consultazione`
- Added `consultazione` to autocomplete_fields

### 7. Frontend (Minimal Changes Required)

The serializer already returns nested objects:
```json
{
  "id": 123,
  "sezione": {...},
  "effettivo": {
    "id": 45,
    "cognome": "Rossi",
    "nome": "Mario",
    "email": "mario@example.com",
    "telefono": "123456"
  },
  "supplente": {
    "id": 67,
    "cognome": "Verdi",
    "nome": "Luigi",
    "email": "luigi@example.com",
    "telefono": "789012"
  },
  "stato": "BOZZA",
  ...
}
```

**Frontend Changes Needed (in `src/GestioneDesignazioni.js`):**

1. Update table to show effettivo and supplente side-by-side (instead of separate rows)
2. Remove `ruolo_rdl` filtering logic
3. Add multi-select functionality with "same comune" validation
4. Add "Genera PDF Batch" button that:
   - Collects selected designazione IDs
   - Calls `POST /api/deleghe/batch/` with `{consultazione_id, designazione_ids, tipo}`
   - Shows success/error message
5. Update carica_mappatura result display to show `updated` and `warnings` fields

## Workflow: Batch PDF → Conferma

1. **User selects multiple designazioni BOZZA** (same comune)
2. **Click "Genera PDF"** → Creates BatchGenerazioneDocumenti
   - Links designazioni via `batch_pdf` FK
   - State: BOZZA
3. **System generates PDF** → State: GENERATO
   - Email sent to user with approval link
4. **User clicks approval link** → `POST /api/deleghe/batch/{id}/approva/`
   - Batch state: APPROVATO
   - All linked designazioni: BOZZA → CONFERMATA
   - `data_approvazione` and `approvata_da_email` populated

## Testing Checklist

### Backend
- [ ] Run migration: `python manage.py migrate`
- [ ] Verify model structure in Django admin
- [ ] Test carica_mappatura:
  - [ ] Creates new designazioni
  - [ ] Updates BOZZE
  - [ ] Skips identical CONFERMATE
  - [ ] Warns on CONFERMATE discrepancies
- [ ] Test batch creation
- [ ] Test batch approval workflow
- [ ] Verify signals provision both effettivo and supplente users

### Frontend
- [ ] Table displays 1 row per seggio
- [ ] Effettivo and supplente shown side-by-side
- [ ] Multi-select works (same comune validation)
- [ ] Batch PDF generation UI works
- [ ] carica_mappatura results display correctly

## Migration Rollback

If something goes wrong:

```bash
# Rollback migration
cd backend_django
python manage.py migrate delegations 0011_delete_campagnareclutamento

# Restart services
docker-compose restart
```

## Key Files Modified

| File | Changes |
|------|---------|
| `backend_django/delegations/models.py` | Refactored DesignazioneRDL + BatchGenerazioneDocumenti |
| `backend_django/delegations/migrations/0012_*.py` | Drop + recreate migration |
| `backend_django/delegations/serializers.py` | New nested serializers |
| `backend_django/delegations/views.py` | Refactored carica_mappatura, batch endpoints |
| `backend_django/delegations/signals.py` | Provision both RDLs |
| `backend_django/delegations/admin.py` | Updated list_display, fieldsets |
| `src/GestioneDesignazioni.js` | Needs table + multi-select updates |

## Benefits of Refactoring

1. **Simpler Data Model**: 1 record per seggio = easier to reason about
2. **Atomic Operations**: Effettivo + Supplente managed together
3. **Batch PDF Workflow**: Natural fit for "select multiple seggi → generate PDF"
4. **Better UI/UX**: Table shows complete seggio info in one row
5. **Cleaner carica_mappatura Logic**: Groups by sezione, handles BOZZA/CONFERMATA intelligently

## Next Steps

1. Run migration in development: `python manage.py migrate`
2. Test carica_mappatura endpoint with real data
3. Update frontend GestioneDesignazioni component (table + multi-select)
4. Integrate batch PDF generation with documents app
5. Test end-to-end workflow: mappatura → select → batch → approve
6. Deploy to production (coordinate with team for data migration)
