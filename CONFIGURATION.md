# ⚙️ Configurazione Variabili d'Ambiente

Guida alle variabili d'ambiente configurabili in AInaudi.

---

## 🎨 Frontend (React/Vite)

Le variabili frontend iniziano con `VITE_` e vengono lette da Vite durante il build.

### VITE_API_URL

**Descrizione:** URL del backend API Django
**Default:** `http://localhost:3001`
**Produzione:** `https://ainaudi-prod.ew.r.appspot.com`

```bash
# Locale
VITE_API_URL=http://localhost:3001

# Produzione
VITE_API_URL=https://ainaudi-prod.ew.r.appspot.com
```

### VITE_RDL_REGISTRATION_URL

**Descrizione:** URL del form esterno per registrazione RDL
**Default:** `https://forms.gle/sLzS7fABZNXeUUnC9`
**Uso:** Quando utenti cliccano "Candidati come Rappresentante di Lista" nella login page

```bash
# Google Form M5S
VITE_RDL_REGISTRATION_URL=https://forms.gle/sLzS7fABZNXeUUnC9

# Oppure altro form/pagina
VITE_RDL_REGISTRATION_URL=https://tuosito.it/diventa-rdl
```

**Come modificarlo:**

1. **Locale (senza Docker):**
   - Modifica `.env` nella root
   - Riavvia `npm run dev`

2. **Docker:**
   - Modifica `.env.docker`
   - Riavvia: `docker-compose restart frontend`

3. **Produzione (App Engine):**
   - Modifica `app.yaml` (frontend)
   - Deploy: `gcloud app deploy`

---

## 📧 Email (Django Backend)

### EMAIL_BACKEND

**Descrizione:** Backend email Django
**Opzioni:**
- `django.core.mail.backends.console.EmailBackend` (dev: stampa nel log)
- `django.core.mail.backends.smtp.EmailBackend` (produzione: invia email)

```bash
# Development
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Production
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

### EMAIL_HOST

**Descrizione:** Server SMTP
**Opzioni:**
- `smtp.gmail.com` (Gmail)
- `smtp.sendgrid.net` (SendGrid)

### EMAIL_HOST_USER

**Descrizione:** Username SMTP (email mittente)

```bash
EMAIL_HOST_USER=s.federici@gmail.com
```

### EMAIL_HOST_PASSWORD

**Descrizione:** Password SMTP
- **Gmail:** App Password (16 caratteri)
- **SendGrid:** API Key (inizia con `SG.`)

```bash
# Gmail App Password
EMAIL_HOST_PASSWORD=abcdefghijklmnop

# SendGrid API Key
EMAIL_HOST_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ SICUREZZA:** Non committare mai password su Git! Usa Secret Manager in produzione.

### DEFAULT_FROM_EMAIL

**Descrizione:** Mittente email (con display name)

```bash
# Con display name (raccomandato)
DEFAULT_FROM_EMAIL="AINAUDI (M5S) <noreply@ainaudi.it>"

# Solo email
DEFAULT_FROM_EMAIL=s.federici@gmail.com
```

---

## 🗄️ Database

### DB_HOST

**Descrizione:** Host database PostgreSQL

```bash
# Locale
DB_HOST=localhost

# Docker
DB_HOST=db

# Cloud SQL (App Engine)
DB_HOST=/cloudsql/ainaudi-prod:europe-west1:ainaudi-db
```

### DB_NAME, DB_USER, DB_PASSWORD

**Descrizione:** Credenziali database

```bash
DB_NAME=ainaudi_db
DB_USER=postgres
DB_PASSWORD=<password-sicura>
```

---

## ☁️ Google Cloud

### GOOGLE_CLOUD_PROJECT

**Descrizione:** ID progetto GCP

```bash
GOOGLE_CLOUD_PROJECT=ainaudi-prod
```

### GCS_BUCKET_NAME

**Descrizione:** Bucket Google Cloud Storage per documenti PDF

```bash
GCS_BUCKET_NAME=ainaudi-documents
```

---

## 🚩 Feature Flags

Abilita/disabilita funzionalità specifiche.

```bash
FEATURE_MAGIC_LINK=true          # Login via Magic Link
FEATURE_M5S_SSO=false            # SSO M5S (non attivo)
FEATURE_INCIDENT_REPORTS=true   # Segnalazioni incidenti
FEATURE_SECTION_IMPORT=true     # Import sezioni da CSV
FEATURE_TEMPLATES_ENGINE=true   # Motore template PDF
FEATURE_AI_ASSISTANT=false      # Assistente AI (sperimentale)
```

---

## 📁 File Configurazione

### Locale (senza Docker)

```
.env                          # Variabili frontend (React/Vite)
backend_django/.env           # Variabili backend (Django)
```

### Docker

```
.env.docker                   # Variabili Docker Compose
docker-compose.yml            # Definizione servizi
```

### Produzione

```
app.yaml                      # Frontend (App Engine)
backend_django/app.yaml       # Backend (App Engine)
```

---

## 🔧 Come Modificare Configurazione

### 1. Locale (senza Docker)

```bash
# Modifica file
nano .env
nano backend_django/.env

# Riavvia servizi
npm run dev                    # Frontend
cd backend_django && python manage.py runserver  # Backend
```

### 2. Docker

```bash
# Modifica file
nano .env.docker

# Riavvia servizi
docker-compose down
docker-compose up -d

# Oppure solo un servizio
docker-compose restart backend
docker-compose restart frontend
```

### 3. Produzione (App Engine)

```bash
# Modifica file
nano app.yaml                      # Frontend
nano backend_django/app.yaml       # Backend

# Deploy
gcloud app deploy app.yaml
cd backend_django && gcloud app deploy app.yaml
```

---

## 🔐 Best Practices

1. **MAI committare `.env` su Git** (già in `.gitignore`)
2. **Usa Secret Manager in produzione** per password/chiavi
3. **Usa display name nelle email** per migliore deliverability
4. **Testa sempre in locale prima** di deployare
5. **Documenta modifiche custom** in questo file

---

## 📖 Vedi Anche

- **Setup Docker:** `DOCKER_SETUP.md`
- **Setup Gmail:** `GMAIL_SETUP.md`
- **Setup Produzione:** `PRODUCTION_SETUP.md`
- **Architettura:** `CLAUDE.md`
