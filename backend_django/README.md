# RDL Referendum - Backend Django

Nuovo backend Django per l'applicazione RDL Referendum, in sostituzione del backend Node.js.

## Quick Start

```bash
# 1. Crea e attiva virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Copia e configura environment
cp .env.example .env
# Modifica .env con le tue credenziali

# 4. Crea le migrazioni
python manage.py makemigrations

# 5. Esegui le migrazioni
python manage.py migrate

# 6. Crea superuser
python manage.py createsuperuser

# 7. Avvia il server di sviluppo
python manage.py runserver 0.0.0.0:3001
```

## Struttura

```
backend_django/
├── config/              # Django project settings
│   ├── settings.py      # Main configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI entry point
├── core/                # Users, Auth, Roles
├── elections/           # Territory, Elections, Ballots, Lists, Candidates
├── sections/            # Section assignments, Vote data
├── delegations/         # Delegation relationships, Freeze batches
├── incidents/           # Incident reports
├── documents/           # PDF generation
├── kpi/                 # Dashboard KPIs
├── ai_assistant/        # AI chat (feature-flagged)
├── requirements.txt     # Python dependencies
└── app.yaml            # GAE deployment config
```

## API Endpoints

### Autenticazione
- `POST /api/auth/google/` - Login con Google OAuth
- `POST /api/auth/magic-link/request/` - Richiedi magic link
- `POST /api/auth/magic-link/verify/` - Verifica magic link
- `GET /api/auth/profile/` - Profilo utente
- `GET /api/auth/roles/` - Ruoli utente

### Elezioni e Territorio
- `GET /api/elections/regioni/`
- `GET /api/elections/province/`
- `GET /api/elections/comuni/`
- `GET /api/elections/sezioni/`
- `GET /api/elections/consultazioni/`
- `GET /api/elections/consultazioni/attiva/`
- `GET /api/elections/schede/`
- `GET /api/elections/liste/`
- `GET /api/elections/candidati/`

### Sezioni e Dati
- `GET /api/sections/assignments/`
- `GET /api/sections/assignments/my/`
- `POST /api/sections/assignments/`
- `GET /api/sections/dati/`
- `GET /api/sections/dati/my/`
- `PATCH /api/sections/dati/{id}/`
- `POST /api/sections/dati/{id}/verify/`
- `GET /api/sections/schede/`
- `PATCH /api/sections/schede/{id}/`

### Deleghe
- `GET /api/delegations/relationships/`
- `GET /api/delegations/relationships/my-delegations/`
- `GET /api/delegations/relationships/my-received/`
- `GET /api/delegations/relationships/tree/`
- `POST /api/delegations/relationships/`
- `POST /api/delegations/relationships/{id}/revoke/`
- `GET /api/delegations/batches/`
- `POST /api/delegations/batches/{id}/freeze/`
- `POST /api/delegations/batches/{id}/approve/`

### Segnalazioni
- `GET /api/incidents/reports/`
- `GET /api/incidents/reports/my/`
- `GET /api/incidents/reports/assigned/`
- `POST /api/incidents/reports/`
- `POST /api/incidents/reports/{id}/resolve/`
- `POST /api/incidents/reports/{id}/escalate/`

### KPI Dashboard
- `GET /api/kpi/dashboard/`
- `GET /api/kpi/turnout/`
- `GET /api/kpi/sections/`
- `GET /api/kpi/incidents/`

### Documenti
- `GET /api/documents/templates/`
- `POST /api/documents/generate/`

### AI Assistant (feature-flagged)
- `POST /api/ai/chat/`
- `GET /api/ai/sessions/`

## Django Admin

Accedi a `/admin/` con le credenziali del superuser per:
- Gestire utenti e ruoli
- Configurare territori (regioni, province, comuni, sezioni)
- Creare consultazioni elettorali
- Configurare schede, liste, candidati
- Visualizzare log audit

## Database

### Sviluppo
SQLite di default (file `db.sqlite3`).

### Produzione
PostgreSQL su Cloud SQL. Configura in `.env`:
```
DB_HOST=your-host
DB_NAME=rdl_referendum
DB_USER=postgres
DB_PASSWORD=your-password
```

O su GAE usa la connessione socket:
```
CLOUD_SQL_CONNECTION_NAME=project:region:instance
```

## Feature Flags

Configurabili in `.env`:
- `FEATURE_MAGIC_LINK=true` - Auth con magic link
- `FEATURE_M5S_SSO=false` - SSO M5S (TBD)
- `FEATURE_INCIDENT_REPORTS=true` - Segnalazioni
- `FEATURE_AI_ASSISTANT=false` - Chat AI

## Testing

```bash
# Esegui tutti i test
pytest

# Con coverage
pytest --cov=. --cov-report=html
```

## Deploy su GAE

```bash
# 1. Collect static files
python manage.py collectstatic --noinput

# 2. Deploy
gcloud app deploy app.yaml
```

## Note

- Il backend Node.js esistente (`backend/`) rimane disponibile durante la migrazione
- Frontend React (`src/`) deve essere aggiornato per puntare al nuovo backend
- Servizio PDF (`pdf/`) sarà integrato nel modulo `documents/`
