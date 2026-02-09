# Setup Produzione - Azioni Manuali Richieste

## ✅ Completato Automaticamente

Tutti i riferimenti "rdl" sono stati sostituiti con "ainaudi" in:
- ✅ docker-compose.yml (16 sostituzioni)
- ✅ docker-compose.prod.yml (14 sostituzioni)
- ✅ app.yaml (2 sostituzioni)
- ✅ backend_django/app.yaml (4 sostituzioni)
- ✅ backend_django/.env.example (6 sostituzioni)
- ✅ .env.docker (2 sostituzioni)
- ✅ docker/init-db.sql (6 sostituzioni)
- ✅ cloudrun/service.yaml (2 sostituzioni)
- ✅ cloudrun/backup-job.yaml (4 sostituzioni)
- ✅ DEPLOYMENT.md (14 sostituzioni)

**Totale: 70 sostituzioni in 10 file**

---

## 🚀 Azioni Manuali da Completare su Google Cloud Platform

### 1. Crea Progetto GCP

```bash
# Crea nuovo progetto
gcloud projects create ainaudi-prod --name="AInaudi Production"

# Imposta come progetto attivo
gcloud config set project ainaudi-prod

# Abilita billing (RICHIESTO)
# Vai su: https://console.cloud.google.com/billing/linkedaccount?project=ainaudi-prod
```

### 2. Abilita API Necessarie

```bash
# Abilita le API
gcloud services enable \
    appengine.googleapis.com \
    sqladmin.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    cloudrun.googleapis.com \
    compute.googleapis.com \
    cloudscheduler.googleapis.com

# Verifica API abilitate
gcloud services list --enabled
```

### 3. Crea Service Account

```bash
# Crea service account
gcloud iam service-accounts create ainaudi-prod \
    --display-name="AInaudi Production Service Account"

# Assegna ruoli necessari
gcloud projects add-iam-policy-binding ainaudi-prod \
    --member="serviceAccount:ainaudi-prod@appspot.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding ainaudi-prod \
    --member="serviceAccount:ainaudi-prod@appspot.gserviceaccount.com" \
    --role="roles/storage.admin"

# Verifica service account
gcloud iam service-accounts list
```

### 4. Crea Cloud SQL Instance (PostgreSQL)

```bash
# Crea istanza PostgreSQL
gcloud sql instances create ainaudi-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=europe-west1 \
    --root-password="CHANGE_ME_STRONG_PASSWORD" \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00

# Crea database
gcloud sql databases create ainaudi_db \
    --instance=ainaudi-db

# Crea utente postgres (se necessario)
gcloud sql users set-password postgres \
    --instance=ainaudi-db \
    --password="CHANGE_ME_STRONG_PASSWORD"

# Abilita accesso da Cloud Run/App Engine
gcloud sql instances patch ainaudi-db \
    --authorized-networks=0.0.0.0/0

# Verifica istanza
gcloud sql instances describe ainaudi-db
```

**⚠️ IMPORTANTE**: Salva la password in un posto sicuro!

### 5. Crea Google Cloud Storage Bucket

```bash
# Crea bucket per media files
gsutil mb -p ainaudi-prod -c STANDARD -l europe-west1 gs://ainaudi-documents

# Imposta permessi pubblici (se necessario per download PDF)
gsutil iam ch allUsers:objectViewer gs://ainaudi-documents

# Abilita CORS (se necessario)
cat > cors.json << 'CORS'
[
  {
    "origin": ["https://ainaudi-prod.ew.r.appspot.com", "https://yourdomain.com"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
CORS

gsutil cors set cors.json gs://ainaudi-documents

# Verifica bucket
gsutil ls -L -b gs://ainaudi-documents
```

### 6. Configura Variabili d'Ambiente Locali

```bash
# Copia template
cp backend_django/.env.example backend_django/.env

# Edita .env con i tuoi valori reali:
nano backend_django/.env
```

**Valori OBBLIGATORI da configurare:**
```bash
# Database (usa i valori creati sopra)
DB_NAME=ainaudi_db
DB_HOST=127.0.0.1  # o Cloud SQL Proxy
DB_PASSWORD=<la-password-che-hai-creato>

# Django
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=ainaudi-prod.ew.r.appspot.com,yourdomain.com
CORS_ALLOWED_ORIGINS=https://ainaudi-prod.ew.r.appspot.com,https://yourdomain.com

# Google Cloud
GOOGLE_CLOUD_PROJECT=ainaudi-prod
GCS_BUCKET_NAME=ainaudi-documents
GOOGLE_CLIENT_ID=<your-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-oauth-client-secret>

# Email SMTP
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=<app-password>
```

### 7. Inizializza App Engine

```bash
# Inizializza App Engine nella regione europe-west
gcloud app create --region=europe-west

# Verifica
gcloud app describe
```

### 8. Deploy Iniziale (Test)

#### Opzione A: Google App Engine

```bash
# Frontend
npm run build
gcloud app deploy app.yaml --project=ainaudi-prod --no-promote

# Backend
cd backend_django
python manage.py collectstatic --noinput
gcloud app deploy app.yaml --project=ainaudi-prod --no-promote

# Se tutto OK, promuovi a produzione
gcloud app versions list
gcloud app services set-traffic default --splits=<version>=1
```

#### Opzione B: Docker Compose (VPS/VM)

```bash
# Su server di produzione

# 1. Clona repository
git clone <your-repo> /opt/ainaudi
cd /opt/ainaudi

# 2. Configura .env
cp backend_django/.env.example .env
nano .env  # Edita con valori reali

# 3. Build e avvia
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 5. Crea superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 6. Verifica
docker-compose -f docker-compose.prod.yml ps
curl http://localhost/api/health/
```

#### Opzione C: Cloud Run

```bash
# Build immagine
gcloud builds submit --tag gcr.io/ainaudi-prod/backend

# Deploy
gcloud run services replace cloudrun/service.yaml --region=europe-west1

# Verifica
gcloud run services describe ainaudi-backend --region=europe-west1
```

### 9. Setup DNS e SSL (se dominio custom)

```bash
# Map custom domain to App Engine
gcloud app domain-mappings create yourdomain.com

# Verifica DNS records necessari
gcloud app domain-mappings describe yourdomain.com

# SSL certificate (automatico con App Engine)
# Oppure usa Let's Encrypt se Docker Compose
```

### 10. Monitoring e Logging

```bash
# Setup monitoring
gcloud logging read "resource.type=gae_app" --limit 50 --format json

# Setup alerts (Cloud Console)
# Vai su: https://console.cloud.google.com/monitoring/alerting

# Cloud SQL monitoring
gcloud sql operations list --instance=ainaudi-db
```

---

## 📋 Checklist Finale

Verifica che tutto sia configurato:

- [ ] Progetto GCP `ainaudi-prod` creato e billing abilitato
- [ ] API necessarie abilitate (App Engine, Cloud SQL, Storage)
- [ ] Service Account `ainaudi-prod@appspot.gserviceaccount.com` creato
- [ ] Cloud SQL instance `ainaudi-db` creato e database `ainaudi_db` configurato
- [ ] GCS Bucket `ainaudi-documents` creato con CORS configurato
- [ ] File `.env` configurato con valori reali (segreti, passwords)
- [ ] App Engine inizializzato in `europe-west`
- [ ] Deploy effettuato (GAE / Docker / Cloud Run)
- [ ] Migrations eseguite sul database di produzione
- [ ] Superuser Django creato
- [ ] DNS configurato (se dominio custom)
- [ ] SSL attivo (HTTPS)
- [ ] Monitoring e alerting configurati
- [ ] Backup automatici configurati per Cloud SQL

---

## 🔐 Security Checklist

- [ ] Password database sicure (> 20 caratteri, random)
- [ ] DJANGO_SECRET_KEY unico e segreto
- [ ] DEBUG=False in produzione
- [ ] ALLOWED_HOSTS configurato correttamente
- [ ] CORS policy restrittive
- [ ] Service Account con minimal permissions
- [ ] Cloud SQL non esposto pubblicamente (usa Cloud SQL Proxy)
- [ ] Secrets non committati in Git (usa Secret Manager)
- [ ] Backup automatici abilitati
- [ ] Logs e monitoring attivi

---

## 📞 Support

Documentazione ufficiale:
- Google Cloud: https://cloud.google.com/docs
- App Engine: https://cloud.google.com/appengine/docs
- Cloud SQL: https://cloud.google.com/sql/docs
- Cloud Run: https://cloud.google.com/run/docs

Per problemi o domande:
- Repository: https://github.com/yourusername/ainaudi
- Email: support@yourdomain.com
