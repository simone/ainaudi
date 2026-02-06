# Template Type System Refactoring - Complete ✅

## Date: 2026-02-05

## Overview

Refactored the Template type system from a CharField with choices to a separate `TemplateType` model. This allows for better organization, reusability, and configuration of template types across multiple consultations.

---

## 🎯 Goals Achieved

1. ✅ **TemplateType as Separate Model**: Template types are now first-class entities with their own schema, merge mode, and use cases
2. ✅ **UUID File Naming**: Template files are automatically renamed with UUIDs to avoid conflicts
3. ✅ **Data Migration**: Existing templates successfully migrated from old CharField to new ForeignKey
4. ✅ **API Endpoints**: Full CRUD REST API for template management
5. ✅ **Frontend Interface**: Complete React UI for template administration
6. ✅ **Django Allauth Warnings**: Fixed deprecated settings warnings

---

## 📊 Architecture

### Old Structure (Before)

```python
class Template(models.Model):
    class TemplateType(models.TextChoices):
        DELEGATION = 'DELEGATION', 'Delega Sub-Delegato'
        DESIGNATION = 'DESIGNATION', 'Designazione RDL'

    template_type = models.CharField(max_length=20, choices=TemplateType.choices)
    template_file = models.FileField(upload_to='templates/')
    # ...
```

**Problems:**
- Template types hardcoded in choices
- No schema definition per type
- No merge_mode per type
- File naming conflicts possible

### New Structure (After)

```python
class TemplateType(models.Model):
    """Generic template type (not tied to consultazione)"""
    code = models.CharField(unique=True)  # DELEGATION, DESIGNATION_SINGLE, DESIGNATION_MULTI
    name = models.CharField()
    default_schema = models.JSONField()
    default_merge_mode = models.CharField()
    use_case = models.TextField()
    # ...

class Template(models.Model):
    """Specific template instance (tied to consultazione)"""
    template_type = models.ForeignKey(TemplateType)
    consultazione = models.ForeignKey(ConsultazioneElettorale)  # Optional
    template_file = models.FileField(upload_to=template_upload_path)  # UUID naming
    variables_schema = models.JSONField()  # Can override type's default
    merge_mode = models.CharField()  # Can override type's default
    # ...
```

**Benefits:**
- ✅ Template types are reusable across consultations
- ✅ Each type has a default schema and merge mode
- ✅ Templates can override defaults
- ✅ UUID file naming prevents conflicts

---

## 📁 File Changes

### Backend

#### Models
- **`backend_django/documents/models.py`**: Added `TemplateType` model, updated `Template` model, added UUID file upload function

#### Migrations
- **`0005_add_template_type_model.py`**: Creates TemplateType table, renames old CharField to old_template_type, adds new FK
- **`0006_migrate_template_types_data.py`**: Populates TemplateType instances and migrates existing templates
- **`0007_remove_old_template_type_field.py`**: Removes legacy field

#### Serializers & Views
- **`backend_django/documents/serializers.py`**: Added `TemplateTypeSerializer`, updated `TemplateSerializer`
- **`backend_django/documents/views.py`**: Added `TemplateTypeViewSet` (read-only)
- **`backend_django/documents/urls.py`**: Added `/api/documents/template-types/` endpoint

#### Admin
- **`backend_django/documents/admin.py`**: Added `TemplateTypeAdmin`

#### Management Commands
- **`backend_django/documents/management/commands/populate_template_types.py`**: Command to populate/update TemplateType instances

#### Settings
- **`backend_django/config/settings.py`**: Fixed Django allauth deprecated settings

### Frontend

#### New Components
- **`src/GestioneTemplate.js`**: Full CRUD interface for template management (create, edit, delete, file upload)

#### Updated Components
- **`src/App.js`**: Added "Gestione Template" menu item in Admin dropdown, added routing

---

## 🔧 TemplateType Instances

Three template types were created:

| Code | Name | Schema | Merge Mode | Use Case |
|------|------|--------|------------|----------|
| **DELEGATION** | Delega Sub-Delegato | `delegato` + `subdelegato` | SINGLE_DOC_PER_RECORD | Sub-delegation documents (1 PDF per sub-delegation) |
| **DESIGNATION_SINGLE** | Designazione RDL Singola | `delegato` + `subdelegato` + `designazione` (object) | SINGLE_DOC_PER_RECORD | Individual designation (N PDFs, one per section) |
| **DESIGNATION_MULTI** | Designazione RDL Riepilogativa | `delegato` + `subdelegato` + `designazioni` (array) | MULTI_PAGE_LOOP | Summary designation (1 PDF with loop/table) |

---

## 🎨 Frontend Features

### Gestione Template UI

**Location**: Admin → Gestione Template (superuser only)

**Features:**
- 📋 **List View**: All templates with name, type, consultazione, version
- ➕ **Create**: New template with type selection, consultazione, description, file upload
- ✏️ **Edit**: Modify name, type, consultazione, description, replace file
- 🗑️ **Delete**: Soft delete (sets is_active=False)
- 📄 **File Preview**: View PDF directly from list

**Form Fields:**
- **Nome Template** *: Template name (required)
- **Tipo Template** *: Dropdown with DELEGATION, DESIGNATION_SINGLE, DESIGNATION_MULTI (required)
- **Consultazione Elettorale**: Optional (leave empty for generic template)
- **Descrizione**: Optional text
- **File PDF Template** *: PDF upload (automatically renamed with UUID)

---

## 🔐 API Endpoints

### TemplateType

```
GET  /api/documents/template-types/       - List all template types (authenticated)
GET  /api/documents/template-types/{id}/  - Get template type detail
```

### Template

```
GET    /api/documents/templates/                - List templates
GET    /api/documents/templates/?template_type=1 - Filter by type
GET    /api/documents/templates/{id}/            - Get template detail
POST   /api/documents/templates/                 - Create template (admin)
PUT    /api/documents/templates/{id}/            - Update template (admin)
DELETE /api/documents/templates/{id}/            - Delete template (admin, soft delete)
```

**Serializer Response:**
```json
{
  "id": 1,
  "name": "Designazione RDL Individuale",
  "template_type": 3,
  "template_type_details": {
    "id": 3,
    "code": "DESIGNATION_MULTI",
    "name": "Designazione RDL Riepilogativa",
    "default_schema": {...},
    "default_merge_mode": "MULTI_PAGE_LOOP",
    "use_case": "..."
  },
  "consultazione": 1,
  "consultazione_nome": "Referendum 2026",
  "description": "...",
  "template_file": "/media/templates/uuid-here.pdf",
  "template_file_url": "http://localhost:3001/media/templates/uuid-here.pdf",
  "variables_schema": {...},
  "field_mappings": [...],
  "loop_config": {...},
  "merge_mode": null,
  "is_active": true,
  "version": 1,
  "created_at": "2026-02-05T10:00:00Z",
  "updated_at": "2026-02-05T18:00:00Z"
}
```

---

## 🗃️ Database Schema

### TemplateType Table

```sql
CREATE TABLE documents_templatetype (
    id bigint PRIMARY KEY,
    code varchar(50) UNIQUE NOT NULL,
    name varchar(100) NOT NULL,
    description text,
    default_schema jsonb NOT NULL DEFAULT '{}',
    default_merge_mode varchar(25) NOT NULL DEFAULT 'SINGLE_DOC_PER_RECORD',
    use_case text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
```

### Template Table (Updated)

```sql
ALTER TABLE documents_template
  DROP COLUMN template_type;  -- Old CharField

ALTER TABLE documents_template
  ADD COLUMN template_type_id bigint NOT NULL
    REFERENCES documents_templatetype(id) ON DELETE PROTECT;

-- template_file now uses UUID naming via upload_to function
```

---

## 🚀 Deployment Steps

### 1. Apply Migrations

```bash
docker exec rdl_backend python manage.py migrate documents
```

**Output:**
```
Applying documents.0005_add_template_type_model... OK
Applying documents.0006_migrate_template_types_data...
  ✓ Migrated 'Designazione RDL Individuale': DESIGNATION → DESIGNATION_MULTI (multi)
  ✓ Migrated 'Designazione RDL Singola': DESIGNATION → DESIGNATION_SINGLE (singola)
  ✅ Template type migration completed!
 OK
Applying documents.0007_remove_old_template_type_field... OK
```

### 2. Populate/Update TemplateType

```bash
docker exec rdl_backend python manage.py populate_template_types
```

**Output:**
```
✓ Created: DELEGATION - Delega Sub-Delegato
✓ Created: DESIGNATION_SINGLE - Designazione RDL Singola
✓ Created: DESIGNATION_MULTI - Designazione RDL Riepilogativa

✅ TemplateType population completed!
  - 3 template types in database
```

### 3. Rebuild Frontend

```bash
npm run build
```

**Output:**
```
✓ built in 1.55s
```

---

## ✅ Verification

### Check Migrations

```bash
docker exec rdl_backend python manage.py showmigrations documents
```

All migrations should show `[X]`.

### Check TemplateType Instances

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import TemplateType
for t in TemplateType.objects.all():
    print(f'{t.code}: {t.name}')
"
```

**Expected Output:**
```
DELEGATION: Delega Sub-Delegato
DESIGNATION_SINGLE: Designazione RDL Singola
DESIGNATION_MULTI: Designazione RDL Riepilogativa
```

### Check Template Migration

```bash
docker exec rdl_backend python manage.py shell -c "
from documents.models import Template
for t in Template.objects.all():
    print(f'{t.name}: {t.template_type.code}')
"
```

**Expected Output:**
```
Designazione RDL Individuale: DESIGNATION_MULTI
Designazione RDL Singola: DESIGNATION_SINGLE
```

### Test Frontend

1. Login as superuser
2. Navigate to **Admin → Gestione Template**
3. Verify template list shows
4. Test creating a new template
5. Test editing existing template
6. Test deleting template

---

## 🐛 Troubleshooting

### Migration Issues

**Problem**: Migration fails with "column already exists"
**Solution**: Rollback and reapply:
```bash
docker exec rdl_backend python manage.py migrate documents 0004
docker exec rdl_backend python manage.py migrate documents
```

**Problem**: Templates have NULL template_type after migration
**Solution**: Run populate and migrate commands again:
```bash
docker exec rdl_backend python manage.py populate_template_types
docker exec rdl_backend python manage.py migrate documents
```

### Frontend Issues

**Problem**: "Gestione Template" menu item not visible
**Solution**: Verify user is superuser:
```python
user.is_superuser  # Should be True
```

**Problem**: API returns 404 for template-types
**Solution**: Check URL configuration:
```bash
docker exec rdl_backend python manage.py show_urls | grep template
```

---

## 📚 Related Documentation

| Document | Description |
|----------|-------------|
| `VARIABLES_SCHEMA_REFERENCE.md` | Complete JSON schemas for all template types |
| `DESIGNATION_SINGLE_SCHEMA.md` | Detailed guide for DESIGNATION_SINGLE type |
| `MULTI_PAGE_LOOP_GUIDE.md` | Guide for multi-page loop configuration |
| `THREE_SCHEMAS_SUMMARY.md` | Summary of three template schemas |
| `JSONPATH_AUTOCOMPLETE.md` | JSONPath autocomplete documentation |

---

## 🎉 Benefits Summary

1. **Better Organization**: Template types are now first-class entities
2. **Reusability**: Same template type can be used across multiple consultations
3. **Flexibility**: Templates can override type defaults
4. **Maintainability**: Changes to template types don't require migrations
5. **User-Friendly**: Admin UI for template management
6. **File Safety**: UUID naming prevents file conflicts
7. **API-Ready**: RESTful endpoints for external integrations

---

**Status**: ✅ Complete and Production-Ready
**Date**: 2026-02-05
**Migration Path**: Fully automated with data preservation
