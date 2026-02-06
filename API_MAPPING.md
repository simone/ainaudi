# API Mapping - Frontend Components → Backend Endpoints

**Data**: 2026-02-06
**Scopo**: Mappare quali componenti frontend chiamano quali endpoint backend

---

## Indice
1. [Per Componente Frontend](#per-componente-frontend)
2. [Per Endpoint Backend](#per-endpoint-backend)
3. [Dependency Graph](#dependency-graph)

---

## Per Componente Frontend

### App.js (Main Router & Auth)
**Endpoint chiamati:**
- `GET /api/permissions` → `client.permissions()`
- `GET /api/elections/` → `client.election.list()`
- `GET /api/elections/active/` → `client.election.active()`
- `GET /api/elections/{id}/` → `client.election.get(id)`
- `GET /api/kpi/dati` → `client.kpi.dati()`
- `GET /api/auth/users/search/?q={query}` → `client.users.search(query)` (Impersonation)

**Funzionalità:**
- Carica permessi utente all'avvio
- Gestisce consultazione attiva
- Impersonation (admin only)

---

### GestioneRdl.js (Gestione RDL Registrations)
**Endpoint chiamati:**
- `GET /api/delegations/mia-catena/?consultazione={id}` → `client.deleghe.miaCatena(consultazioneId)`
- `GET /api/rdl/registrations?filters` → `client.rdlRegistrations.list(filters)`
- `POST /api/rdl/registrations/{id}/approve` → `client.rdlRegistrations.approve(id)`
- `POST /api/rdl/registrations/{id}/reject` → `client.rdlRegistrations.reject(id, reason)`
- `PUT /api/rdl/registrations/{id}` → `client.rdlRegistrations.update(id, data)`
- `DELETE /api/rdl/registrations/{id}` → `client.rdlRegistrations.delete(id)`
- `POST /api/rdl/registrations/import?analyze=true` → `client.rdlRegistrations.analyzeCSV(file)`
- `POST /api/rdl/registrations/import` → `client.rdlRegistrations.import(file, mapping)`
- `POST /api/rdl/registrations/retry` → `client.rdlRegistrations.retry(records)`
- `GET /api/rdl/comuni/search?q={query}` → `client.rdlRegistrations.searchComuni(query)`

**Funzionalità:**
- Lista, approva, rifiuta RDL registrations
- Import CSV con mappatura colonne
- Correzione errori import
- Filtri territorio (regione, provincia, comune, municipio)

---

### GestioneDesignazioni.js (Designazioni RDL → Sezioni)
**Endpoint chiamati:**
- `GET /api/delegations/mia-catena/?consultazione={id}` → `client.deleghe.miaCatena(consultazioneId)`
- `POST /api/delegations/designazioni/upload_csv/` → `client.deleghe.designazioni.uploadCsv(file)`
- `POST /api/delegations/designazioni/carica_mappatura/` → `client.deleghe.designazioni.caricaMappatura(consultazioneId)`
- `GET /api/sections/stats` → `client.sections.stats()`

**Funzionalità:**
- Carica mappatura RDL → Sezioni da CSV
- Fotografa SectionAssignment in DesignazioneRDL
- Statistiche sezioni

---

### GestioneDeleghe.js (Catena Deleghe)
**Endpoint chiamati:**
- `GET /api/delegations/mia-catena/?consultazione={id}` → `client.deleghe.miaCatena(consultazioneId)`
- `POST /api/delegations/sub-deleghe/` → `client.deleghe.subDeleghe.create(data)`
- `DELETE /api/delegations/sub-deleghe/{id}/` → `client.deleghe.subDeleghe.revoke(id)`

**Funzionalità:**
- Visualizza catena deleghe (Delegato → SubDelegato → RDL)
- Crea/revoca sub-deleghe
- Gestisce territorio (regioni, province, comuni, municipi)

---

### GestioneCampagne.js (Campagne Reclutamento)
**Endpoint chiamati:**
- `GET /api/delegations/campagne/?consultazione={id}` → `client.deleghe.campagne.list(consultazioneId)`
- `POST /api/delegations/campagne/` → `client.deleghe.campagne.create(data)`
- `PUT /api/delegations/campagne/{id}/` → `client.deleghe.campagne.update(id, data)`
- `DELETE /api/delegations/campagne/{id}/` → `client.deleghe.campagne.delete(id)`
- `POST /api/delegations/campagne/{id}/attiva/` → `client.deleghe.campagne.attiva(id)`
- `POST /api/delegations/campagne/{id}/chiudi/` → `client.deleghe.campagne.chiudi(id)`
- `GET /api/territory/regioni/` → `client.territorio.regioni()`
- `GET /api/territory/province/?regione={id}` → `client.territorio.province(regioneId)`
- `GET /api/territory/comuni/?provincia={id}` → `client.territorio.comuni(provinciaId)`

**Funzionalità:**
- CRUD campagne
- Attiva/chiudi campagne
- Territorio scope (regioni, province, comuni)

---

### Mappatura.js (Assegnazione RDL → Sezioni Operative)
**Endpoint chiamati:**
- `GET /api/mapping/sezioni/?filters` → `client.mappatura.sezioni(filters)` (cached 30s)
- `GET /api/mapping/rdl/?filters` → `client.mappatura.rdl(filters)` (cached 30s)
- `POST /api/mapping/assegna/` → `client.mappatura.assegna(sezioneId, rdlId, ruolo)`
- `DELETE /api/mapping/assegna/{id}/` → `client.mappatura.rimuovi(assignmentId)`
- `POST /api/mapping/assegna-bulk/` → `client.mappatura.assegnaBulk(rdlId, sezioniIds, ruolo)`
- `GET /api/territory/comuni/{id}/` → `client.territorio.municipi(comuneId)`

**Funzionalità:**
- Drag & drop RDL su sezioni
- Assegnazione bulk
- Visualizza sezioni libere/assegnate
- Filtra per comune/municipio

---

### GestioneSezioni.js (CRUD Sezioni Elettorali)
**Endpoint chiamati:**
- `GET /api/sections/stats` → `client.sections.stats()`
- `POST /api/sections/upload` → `client.sections.upload(file)`
- `PATCH /api/sections/{id}/` → `client.sections.update(id, data)`
- `GET /api/sections/list/?comune_id&page&page_size` → `client.sections.list(comuneId, page, pageSize)`

**Funzionalità:**
- Statistiche sezioni
- Upload CSV sezioni
- Modifica singola sezione (indirizzo, denominazione)
- Lista paginata per comune

---

### SectionList.js (Scrutinio - Data Entry)
**Endpoint chiamati:**
- `GET /api/scrutinio/info` → `client.scrutinio.info()` (cached 300s)
- `GET /api/scrutinio/sezioni?page&page_size` → `client.scrutinio.sezioni(page, pageSize)` (page 1 cached 30s)
- `POST /api/scrutinio/save` → `client.scrutinio.save(data)`

**Funzionalità:**
- Form data entry voti per sezione
- Multi-turno, multi-scheda
- Validazione strutturata con JSON schema
- Paginazione sezioni

---

### Kpi.js (Dashboard KPI)
**Endpoint chiamati:**
- `GET /api/kpi/dati` → `client.kpi.dati()`
- `GET /api/kpi/sezioni` → `client.kpi.sezioni()`
- `GET /api/election/lists` → `client.election.lists()` (cached 600s)
- `GET /api/election/candidates` → `client.election.candidates()` (cached 600s)

**Funzionalità:**
- Dashboard con grafici (Recharts)
- KPI affluenza, scrutinio
- Statistiche per lista/candidato

---

### SchedaElettorale.js (Edit Scheda)
**Endpoint chiamati:**
- `PATCH /api/elections/ballots/{id}/` → `client.election.updateBallot(id, data)`

**Funzionalità:**
- Modifica scheda elettorale (solo Delegato/SubDelegato)

---

### RdlSelfRegistration.js (Auto-registrazione RDL)
**Endpoint chiamati:**
- `POST /api/rdl/register` → `client.rdlRegistrations.register(data)`

**Funzionalità:**
- Form auto-registrazione RDL pubblico
- Validazione email, telefono, dati anagrafici

---

### UploadSezioni.js (Upload CSV Sezioni)
**Endpoint chiamati:**
- `POST /api/sections/upload` → `client.sections.upload(file)`

**Funzionalità:**
- Upload CSV con sezioni elettorali

---

### Risorse.js (Documenti/FAQ)
**Endpoint chiamati:**
- `GET /api/risorse/?consultazione={id}` → `client.risorse.list(consultazioneId)`
- `POST /api/risorse/faqs/{id}/vota/` → `client.risorse.faqs.vota(id, utile)`

**Funzionalità:**
- Lista documenti pubblici/privati
- FAQ con voto utilità

---

### TemplateList.js (Template PDF)
**Endpoint chiamati:**
- `GET /api/elections/active/` → `client.election.active()` (cached 300s)

**Funzionalità:**
- Lista template PDF disponibili

---

### GeneraModuli.js (Generazione PDF)
**Endpoint chiamati:**
- `POST {pdfServer}/api/generate/{type}` → `client.pdf.generate(formData, type)`

**Funzionalità:**
- Generazione PDF deleghe/designazioni
- Form con dati delegato/sub/RDL

---

### GestioneRegioni.js (Admin Territorio)
**Endpoint chiamati:**
- `GET /api/territory/regioni/` → `client.territorio.admin.regioni.list()`
- `POST /api/territory/regioni/` → `client.territorio.admin.regioni.create(data)`
- `PUT /api/territory/regioni/{id}/` → `client.territorio.admin.regioni.update(id, data)`
- `DELETE /api/territory/regioni/{id}/` → `client.territorio.admin.regioni.delete(id)`
- `POST /api/territory/regioni/import_csv/` → `client.territorio.admin.regioni.import(file)`

**Funzionalità:**
- CRUD regioni (admin only)
- Import CSV regioni

---

### GestioneProvince.js (Admin Territorio)
**Endpoint chiamati:**
- `GET /api/territory/regioni/` → `client.territorio.admin.regioni.list()`
- `GET /api/territory/province/?filters` → `client.territorio.admin.province.list(filters)`
- `POST /api/territory/province/` → `client.territorio.admin.province.create(data)`
- `PUT /api/territory/province/{id}/` → `client.territorio.admin.province.update(id, data)`
- `DELETE /api/territory/province/{id}/` → `client.territorio.admin.province.delete(id)`
- `POST /api/territory/province/import_csv/` → `client.territorio.admin.province.import(file)`

**Funzionalità:**
- CRUD province (admin only)
- Import CSV province

---

### GestioneComuni.js (Admin Territorio)
**Endpoint chiamati:**
- `GET /api/territory/regioni/` → `client.territorio.admin.regioni.list()`
- `GET /api/territory/province/?filters` → `client.territorio.admin.province.list(filters)`
- `GET /api/territory/province/{id}/` → `client.territorio.admin.province.get(id)`
- `GET /api/territory/comuni/?filters` → `client.territorio.admin.comuni.list(filters)`
- `POST /api/territory/comuni/` → `client.territorio.admin.comuni.create(data)`
- `PUT /api/territory/comuni/{id}/` → `client.territorio.admin.comuni.update(id, data)`
- `DELETE /api/territory/comuni/{id}/` → `client.territorio.admin.comuni.delete(id)`
- `POST /api/territory/comuni/import_csv/` → `client.territorio.admin.comuni.import(file)`
- `GET /api/territory/municipi/?filters` → `client.territorio.admin.municipi.list(filters)`
- `POST /api/territory/municipi/` → `client.territorio.admin.municipi.create(data)`
- `DELETE /api/territory/municipi/{id}/` → `client.territorio.admin.municipi.delete(id)`

**Funzionalità:**
- CRUD comuni (admin only)
- CRUD municipi (admin only)
- Import CSV comuni

---

### GestioneSezioniTerritoriali.js (Admin Territorio)
**Endpoint chiamati:**
- `GET /api/territory/regioni/` → `client.territorio.admin.regioni.list()`
- `GET /api/territory/province/?filters` → `client.territorio.admin.province.list(filters)`
- `GET /api/territory/province/{id}/` → `client.territorio.admin.province.get(id)`
- `GET /api/territory/comuni/?filters` → `client.territorio.admin.comuni.list(filters)`
- `GET /api/territory/comuni/{id}/` → `client.territorio.admin.comuni.get(id)`
- `GET /api/territory/municipi/?filters` → `client.territorio.admin.municipi.list(filters)`
- `GET /api/territory/sezioni/?filters` → `client.territorio.admin.sezioni.list(filters)`
- `POST /api/territory/sezioni/` → `client.territorio.admin.sezioni.create(data)`
- `PUT /api/territory/sezioni/{id}/` → `client.territorio.admin.sezioni.update(id, data)`
- `DELETE /api/territory/sezioni/{id}/` → `client.territorio.admin.sezioni.delete(id)`
- `POST /api/territory/sezioni/import_csv/` → `client.territorio.admin.sezioni.import(file)`
- `PUT /api/territory/municipi/{id}/` → `client.territorio.admin.municipi.update(id, data)`
- `DELETE /api/territory/municipi/{id}/` → `client.territorio.admin.municipi.delete(id)`

**Funzionalità:**
- CRUD sezioni elettorali (admin only)
- Import CSV sezioni
- Modifica municipi

---

### GestioneTerritorio.js (Admin Territorio - Overview)
**Endpoint chiamati:**
- `GET /api/territory/regioni/` → `client.territorio.admin.regioni.list()`
- `GET /api/territory/province/?filters` → `client.territorio.admin.province.list(filters)`
- `GET /api/territory/comuni/?filters` → `client.territorio.admin.comuni.list(filters)`
- `GET /api/territory/sezioni/?filters` → `client.territorio.admin.sezioni.list(filters)`

**Funzionalità:**
- Dashboard overview territorio
- Statistiche regioni/province/comuni/sezioni

---

### RdlList.js (Legacy RDL Assignment)
**Endpoint chiamati:**
- `GET /api/rdl/emails` → `client.rdl.emails()` (cached 120s)
- `GET /api/rdl/sections` → `client.rdl.sections()` (cached 120s)
- `POST /api/rdl/assign` → `client.rdl.assign({comune, sezione, email})`
- `POST /api/rdl/unassign` → `client.rdl.unassign({comune, sezione})`

**Funzionalità:**
- Assegnazione RDL → Sezioni (legacy, sostituito da Mappatura.js)

---

## Per Endpoint Backend

### Authentication & Authorization

| Endpoint | Componenti | Metodo | Auth |
|----------|-----------|--------|------|
| `POST /api/auth/magic-link/request/` | - | POST | AllowAny |
| `POST /api/auth/magic-link/verify/` | - | POST | AllowAny |
| `GET /api/permissions` | App.js | GET | IsAuthenticated |
| `GET /api/auth/users/search/` | App.js | GET | IsAuthenticated (superuser) |

---

### Elections

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/elections/` | App.js | GET | IsAuthenticated | ❌ NO |
| `GET /api/elections/active/` | App.js, TemplateList.js | GET | IsAuthenticated | ❌ NO |
| `GET /api/elections/{id}/` | App.js | GET | IsAuthenticated | ❌ NO |
| `GET /api/elections/ballots/{id}/` | - | GET | IsAuthenticated | ❌ NO |
| `PATCH /api/elections/ballots/{id}/` | SchedaElettorale.js | PATCH | IsAuthenticated | ⚠️ Ruolo check |
| `GET /api/election/lists` | Kpi.js | GET | IsAuthenticated | ❌ NO |
| `GET /api/election/candidates` | Kpi.js | GET | IsAuthenticated | ❌ NO |

---

### Sections (Sezioni Elettorali)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/sections/stats` | GestioneDesignazioni.js, GestioneSezioni.js | GET | IsAuthenticated | ✅ SÌ |
| `GET /api/sections/list/` | GestioneSezioni.js | GET | IsAuthenticated | ✅ SÌ |
| `GET /api/sections/own` | - | GET | IsAuthenticated | ✅ SÌ (RDL) |
| `GET /api/sections/assigned` | - | GET | IsAuthenticated | ✅ SÌ |
| `PATCH /api/sections/{id}/` | GestioneSezioni.js | PATCH | IsAuthenticated | ✅ SÌ |
| `POST /api/sections/` | - | POST | IsAuthenticated | ✅ SÌ |
| `POST /api/sections/upload` | UploadSezioni.js, GestioneSezioni.js | POST | IsAuthenticated | ✅ SÌ |

---

### Scrutinio (Data Entry)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/scrutinio/info` | SectionList.js | GET | IsAuthenticated | N/A |
| `GET /api/scrutinio/sezioni` | SectionList.js | GET | IsAuthenticated | ✅ SÌ |
| `POST /api/scrutinio/save` | SectionList.js | POST | IsAuthenticated | ✅ SÌ |

---

### RDL Registrations

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `POST /api/rdl/register` | RdlSelfRegistration.js | POST | AllowAny | N/A |
| `GET /api/rdl/registrations` | GestioneRdl.js | GET | IsAuthenticated | ✅ SÌ |
| `PUT /api/rdl/registrations/{id}` | GestioneRdl.js | PUT | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/registrations/{id}/approve` | GestioneRdl.js | POST | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/registrations/{id}/reject` | GestioneRdl.js | POST | IsAuthenticated | ✅ SÌ |
| `DELETE /api/rdl/registrations/{id}` | GestioneRdl.js | DELETE | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/registrations/import` | GestioneRdl.js | POST | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/registrations/retry` | GestioneRdl.js | POST | IsAuthenticated | ✅ SÌ |
| `GET /api/rdl/comuni/search` | GestioneRdl.js | GET | IsAuthenticated | ✅ SÌ |

---

### Delegations (Deleghe e Designazioni)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/delegations/mia-catena/` | GestioneDeleghe.js, GestioneDesignazioni.js, GestioneRdl.js | GET | IsAuthenticated | ✅ SÌ |
| `GET /api/delegations/sub-deleghe/` | - | GET | IsAuthenticated | ✅ SÌ |
| `POST /api/delegations/sub-deleghe/` | GestioneDeleghe.js | POST | IsAuthenticated | ✅ SÌ |
| `DELETE /api/delegations/sub-deleghe/{id}/` | GestioneDeleghe.js | DELETE | IsAuthenticated | ✅ SÌ |
| `GET /api/delegations/designazioni/` | - | GET | IsAuthenticated | ✅ SÌ |
| `POST /api/delegations/designazioni/upload_csv/` | GestioneDesignazioni.js | POST | IsAuthenticated | ✅ SÌ |
| `POST /api/delegations/designazioni/carica_mappatura/` | GestioneDesignazioni.js | POST | IsAuthenticated | ✅ SÌ |
| `GET /api/delegations/campagne/` | GestioneCampagne.js | GET | IsAuthenticated | ⚠️ NO FILTRO |
| `POST /api/delegations/campagne/` | GestioneCampagne.js | POST | IsAuthenticated | ⚠️ NO FILTRO |
| `PUT /api/delegations/campagne/{id}/` | GestioneCampagne.js | PUT | IsAuthenticated | ⚠️ NO FILTRO |
| `DELETE /api/delegations/campagne/{id}/` | GestioneCampagne.js | DELETE | IsAuthenticated | ⚠️ NO FILTRO |
| `POST /api/delegations/campagne/{id}/attiva/` | GestioneCampagne.js | POST | IsAuthenticated | ⚠️ NO FILTRO |
| `POST /api/delegations/campagne/{id}/chiudi/` | GestioneCampagne.js | POST | IsAuthenticated | ⚠️ NO FILTRO |

---

### Mappatura (RDL → Sezioni Operative)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/mapping/sezioni/` | Mappatura.js | GET | IsAuthenticated | ✅ SÌ |
| `GET /api/mapping/rdl/` | Mappatura.js | GET | IsAuthenticated | ✅ SÌ |
| `POST /api/mapping/assegna/` | Mappatura.js | POST | IsAuthenticated | ✅ SÌ |
| `DELETE /api/mapping/assegna/{id}/` | Mappatura.js | DELETE | IsAuthenticated | ✅ SÌ |
| `POST /api/mapping/assegna-bulk/` | Mappatura.js | POST | IsAuthenticated | ✅ SÌ |

---

### KPI (Dashboard)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/kpi/dati` | Kpi.js, App.js | GET | IsAuthenticated | ❌ NO |
| `GET /api/kpi/sezioni` | Kpi.js | GET | IsAuthenticated | ❌ NO |

---

### Territory (Territorio Amministrativo)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/territory/regioni/` | Molti componenti | GET | IsAuthenticated | ❌ NO |
| `GET /api/territory/province/` | Molti componenti | GET | IsAuthenticated | ❌ NO |
| `GET /api/territory/comuni/` | Molti componenti | GET | IsAuthenticated | ❌ NO |
| `GET /api/territory/municipi/` | Molti componenti | GET | IsAuthenticated | ❌ NO |
| `GET /api/territory/sezioni/` | GestioneSezioniTerritoriali.js | GET | IsAuthenticated | ❌ NO |
| `POST /api/territory/*/` | Admin components | POST | IsAdminUser | ✅ SÌ |
| `PUT /api/territory/*/{id}/` | Admin components | PUT | IsAdminUser | ✅ SÌ |
| `DELETE /api/territory/*/{id}/` | Admin components | DELETE | IsAdminUser | ✅ SÌ |
| `POST /api/territory/*/import_csv/` | Admin components | POST | IsAdminUser | ✅ SÌ |

---

### Resources (Documenti/FAQ)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/risorse/` | Risorse.js | GET | AllowAny* | N/A |
| `GET /api/risorse/documenti/` | - | GET | AllowAny* | N/A |
| `GET /api/risorse/faqs/` | - | GET | AllowAny* | N/A |
| `POST /api/risorse/faqs/{id}/vota/` | Risorse.js | POST | IsAuthenticated | N/A |
| `GET /api/risorse/pdf-proxy/` | - | GET | AllowAny | N/A |

\* Filtra per `is_pubblico` se non autenticato

---

### PDF Generation

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `POST {pdfServer}/api/generate/{type}` | GeneraModuli.js | POST | IsAuthenticated | N/A |

---

### RDL Assignment (Legacy)

| Endpoint | Componenti | Metodo | Auth | Territorio |
|----------|-----------|--------|------|-----------|
| `GET /api/rdl/emails` | RdlList.js | GET | IsAuthenticated | ✅ SÌ |
| `GET /api/rdl/sections` | RdlList.js | GET | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/assign` | RdlList.js | POST | IsAuthenticated | ✅ SÌ |
| `POST /api/rdl/unassign` | RdlList.js | POST | IsAuthenticated | ✅ SÌ |

---

## Dependency Graph

### High-Level Flow

```
User Login (Magic Link)
    ↓
App.js: Load Permissions (/api/permissions)
    ↓
App.js: Load Active Election (/api/elections/active/)
    ↓
    ├─→ Delegato/SubDelegato
    │       ├─→ GestioneDeleghe.js (Sub-deleghe)
    │       ├─→ GestioneRdl.js (Approva RDL)
    │       ├─→ GestioneDesignazioni.js (Designa RDL → Sezioni)
    │       ├─→ Mappatura.js (Assegna RDL operativo)
    │       ├─→ GestioneCampagne.js (Campagne reclutamento)
    │       ├─→ GestioneSezioni.js (Gestione sezioni)
    │       └─→ Kpi.js (Dashboard)
    │
    ├─→ RDL
    │       ├─→ SectionList.js (Scrutinio)
    │       └─→ Kpi.js (Dashboard)
    │
    └─→ Admin
            ├─→ GestioneTerritorio.js (Overview)
            ├─→ GestioneRegioni.js
            ├─→ GestioneProvince.js
            ├─→ GestioneComuni.js
            └─→ GestioneSezioniTerritoriali.js
```

---

### Cache Invalidation Flow

```
User Actions → Invalidate Cache
    │
    ├─ sections.save() → Invalida: ['assigned', 'own', 'scrutinio.sezioni']
    ├─ scrutinio.save() → Invalida: ['scrutinio.sezioni.1', 'assigned', 'own']
    ├─ rdl.assign() → Invalida: ['rdl.sections']
    └─ mappatura.assegna() → Invalida: ['mappatura.sezioni.*', 'mappatura.rdl.*']
```

---

## Componenti Critici per Territorio

### Con Controllo Territorio ✅
- GestioneRdl.js
- GestioneDesignazioni.js
- GestioneDeleghe.js
- Mappatura.js
- GestioneSezioni.js
- SectionList.js

### Senza Controllo Territorio ❌ (Criticità)
- Kpi.js → Dati globali
- GestioneTerritorio.js → Lista tutto territorio
- GestioneSezioniTerritoriali.js → Lista tutte sezioni
- App.js (elections) → Lista tutte consultazioni

---

**Fine Mapping**
