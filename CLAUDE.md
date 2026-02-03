# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RDL (Responsabile Di Lista) is an election data collection system for Movimento 5 Stelle. It manages the Italian electoral delegation hierarchy (Delegato → SubDelegato → RDL), collects voting data from electoral sections, handles RDL registrations/approvals, displays KPI dashboards, and generates PDF nomination forms.

## Development Commands

```bash
# Install dependencies
npm install                           # Frontend dependencies
cd backend_django && pip install -r requirements.txt  # Django dependencies

# Run services (development)
npm run frontend                      # React dev server (port 3000)
cd backend_django && python manage.py runserver 3001  # Django API (port 3001)

# Docker development (recommended)
docker-compose up                     # All services (frontend:3000, backend:3001, postgres:5432)

# Django migrations
cd backend_django
python manage.py makemigrations
python manage.py migrate

# Tests
npm test                              # React tests (jest)
cd backend_django && python manage.py test  # Django tests

# Production build
npm run build                         # Build React for production
docker-compose -f docker-compose.prod.yml up  # Production deployment
```

## Architecture

**Django + React full-stack application:**

```
React Frontend (src/)
       ↓
    Nginx
       ↓
Django REST API (backend_django/)
       ↓
PostgreSQL / Redis
```

### Backend Django Apps (`backend_django/`)

| App | Purpose |
|-----|---------|
| `core` | User model (email-based), RoleAssignment, AuditLog |
| `territorio` | Italian hierarchy: Regione → Provincia → Comune → Municipio → SezioneElettorale + Partizioni territoriali (circoscrizioni, collegi) |
| `elections` | ConsultazioneElettorale, TipoElezione, SchedaElettorale, ListaElettorale, Candidato + Binding partizioni |
| `delegations` | DelegatoDiLista, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti |
| `sections` | RdlRegistration, SectionAssignment, DatiSezione, DatiScheda |
| `incidents` | Incident reporting during elections |
| `documents` | PDF template generation |
| `resources` | Educational materials for RDLs |
| `kpi` | Dashboard data aggregation |

### Territorial Partitions (Circoscrizioni, Collegi)

Electoral partitions model how the territory is divided for voting purposes:

```
TerritorialPartitionSet (es. "Circoscrizioni Europee")
    └── TerritorialPartitionUnit (es. "Nord-Ovest", "Centro", etc.)
            └── TerritorialPartitionMembership (es. Lazio → Centro)
```

**Partition Types:**
- `EU_CIRCOSCRIZIONE`: 5 European Parliament circumscriptions
- `CAMERA_CIRCOSCRIZIONE`: 26 Chamber circumscriptions
- `SENATO_CIRCOSCRIZIONE`: 20 Senate circumscriptions (= regions)
- `COLLEGIO_UNINOMINALE_*`: Single-member constituencies (~200 for Chamber)
- `COLLEGIO_PLURINOMINALE_*`: Multi-member constituencies (~60 for Chamber)

**Election Bindings:**
- `ElectionPartitionBinding`: Links election to partition set (which version to use)
- `BallotActivation`: Which ballots are active in which partitions
- `CandidatePartitionEligibility`: Which candidates are eligible in which partitions

**Automatic Section→Partition lookup:**
```python
sezione.get_partition_unit('EU_CIRCOSCRIZIONE')  # Returns "Centro" for Rome
```

### Delegation Hierarchy

```
PARTITO (M5S)
    ↓ nomina
DELEGATO DI LISTA (deputati, senatori, consiglieri regionali)
    ↓ sub-delega (firma autenticata)
SUB-DELEGATO (per territorio: comuni/municipi)
    ↓ designa
RDL (Effettivo + Supplente) per sezione elettorale
```

**SubDelega types:**
- `FIRMA_AUTENTICATA`: Can designate RDLs directly
- `MAPPATURA`: Creates drafts (stato=BOZZA), Delegato must approve

**SubDelega territory (hierarchy, from broader to specific):**
- `regioni`: Access to all sections in the region
- `province`: Access to all sections in the province
- `comuni`: Access to all sections in the municipality
- `municipi`: Access only to specified districts (optional, for large cities)

### Multi-Election Consultations

When a consultation includes multiple election types (e.g., Referendum + Europee + Comunali):

```
ConsultazioneElettorale: "Elezioni 17 Giugno 2025"
    ├── TipoElezione: REFERENDUM (nazionale) → 5 SchedaElettorale
    ├── TipoElezione: EUROPEE (nazionale) → 1 SchedaElettorale
    ├── TipoElezione: POLITICHE_CAMERA (suppletiva) → 1 SchedaElettorale
    └── TipoElezione: COMUNALI (specifici comuni) → 1 SchedaElettorale
```

**Unified delegation model:**
- **One Delega** covers all election types in the consultation
- **One SubDelega** covers all election types in the consultation
- **One Mappatura** (SectionAssignment) per RDL per section
- **Document generation** produces N documents (one per TipoElezione)

This simplifies administration while generating legally-required separate documents.

### Frontend Components (`src/`)

| Component | Purpose |
|-----------|---------|
| `App.js` | Main router, auth context, navigation |
| `AuthContext.js` | JWT management, Magic Link |
| `Client.js` | API client with caching |
| `GestioneDeleghe.js` | Delegation chain management |
| `GestioneRdl.js` | RDL registration approvals |
| `GestioneSezioni.js` | Electoral section CRUD |
| `SectionForm.js` | Voting data entry form |
| `Kpi.js` | Dashboard charts |

### Authentication

Authentication via **Magic Link**:
- Request: `POST /api/auth/magic-link/request/` with email
- Verify: `POST /api/auth/magic-link/verify/` with token from email
- M5S SSO: (feature flagged, not active)

JWT tokens: Access (1h) + Refresh (7d) stored in localStorage.

### Role-Based Permissions

| Role | Capabilities |
|------|--------------|
| `ADMIN` | Full system access |
| `DELEGATE` | Create sub-deleghe, designate RDLs directly |
| `SUBDELEGATE` | Designate RDLs or prepare mappature (based on tipo_delega) |
| `RDL` | Enter section voting data |
| `KPI_VIEWER` | View dashboards |

## Environment Variables

```bash
# Django
DJANGO_SECRET_KEY=
DEBUG=True
DB_HOST=localhost
DB_NAME=rdl_db
DB_USER=rdl_user
DB_PASSWORD=
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
FRONTEND_URL=http://localhost:3000

# React
REACT_APP_API_URL=http://localhost:3001
```

## Key API Endpoints

```
# Auth
POST /api/auth/magic-link/request/      - Request magic link
POST /api/auth/magic-link/verify/       - Verify magic link

# Delegations
GET  /api/deleghe/mia-catena/           - User's delegation chain
GET  /api/deleghe/sub-deleghe/          - List sub-deleghe
POST /api/deleghe/sub-deleghe/          - Create sub-delega
GET  /api/deleghe/designazioni/         - List designazioni RDL
POST /api/deleghe/designazioni/         - Create designazione

# RDL Management
GET  /api/rdl/registrations             - List RDL registrations
POST /api/rdl/registrations/{id}/approve - Approve registration

# Territory
GET  /api/territorio/regioni/           - Regions
GET  /api/territorio/province/?regione= - Provinces (cascading filter)
GET  /api/territorio/comuni/?provincia= - Municipalities
```

## Signals (Auto-provisioning)

When entities are created/updated, signals in `delegations/signals.py` and `sections/signals.py` automatically:
- Create User accounts based on email
- Assign appropriate roles (DELEGATE, SUBDELEGATE, RDL)
- Link users to domain entities

## Deployment

- **Development**: `docker-compose.yml` (PostgreSQL 15, Django, React, Redis, Adminer)
- **Production**: `docker-compose.prod.yml` (distroless images, Nginx, non-root users, read-only filesystems)
- **Legacy GAE**: `app.yaml`, `dispatch.yaml` (Node.js backend - deprecated)
