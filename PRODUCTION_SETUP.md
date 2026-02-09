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

### 6. Configura SMTP per Email (Magic Link)

Hai **2 opzioni** per inviare email (Magic Link, notifiche). Scegli quella più adatta:

---

#### ✅ Opzione A: Gmail SMTP (Raccomandato per iniziare)

**Pro:** Semplice, gratuito, affidabile
**Contro:** Limite 500 email/giorno
**Usa quando:** Hai un account Gmail e vuoi partire subito

##### Step 1: Abilita Autenticazione a 2 Fattori

1. Vai su [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. **Sicurezza** → **Verifica in due passaggi** → Attiva

##### Step 2: Genera App Password

1. Vai su [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Seleziona:
   - **App:** Mail
   - **Dispositivo:** Altro (nome personalizzato) → scrivi "AInaudi Django"
3. Clicca **Genera**
4. Google ti darà una **password di 16 caratteri** (es: `abcd efgh ijkl mnop`)
5. **Copia subito** (appare una sola volta!)

**⚠️ IMPORTANTE**: Salva la password App in un posto sicuro!

---

#### Opzione B: SendGrid SMTP (Per volumi alti)

**Pro:** Scalabile, deliverability ottima, 100 email/giorno gratis
**Contro:** Richiede account separato e configurazione dominio
**Usa quando:** Hai bisogno di >500 email/giorno o analytics avanzate

<details>
<summary><b>📖 Click per vedere istruzioni SendGrid</b></summary>

##### Step 1: Crea Account SendGrid

1. Vai su [https://signup.sendgrid.com/](https://signup.sendgrid.com/)
2. Registrati (piano free: 100 email/giorno)
3. Verifica email e completa onboarding

##### Step 2: Crea API Key

1. Dashboard SendGrid → **Settings** → **API Keys**
2. **Create API Key**
   - Nome: "ainaudi-prod-django"
   - Permessi: **Full Access** (o "Mail Send" solo)
3. Clicca **Create & View**
4. COPIA la chiave (inizia con `SG.xxx...`)

**⚠️ IMPORTANTE**: La API key appare UNA SOLA VOLTA!

##### Step 3: Verifica Sender

- **Settings** → **Sender Authentication** → **Verify a Single Sender**
- Inserisci `noreply@m5s.it` (o la tua email) e verifica

</details>

---

### 7. Configura Secret Manager (Password Sicure)

**Secret Manager** permette di salvare password/chiavi in modo sicuro su GCP invece che in file .env

#### 🚀 Metodo AUTOMATICO (Raccomandato)

**Usa lo script** per configurare tutto interattivamente:

```bash
# Per Gmail SMTP (Opzione A)
./scripts/setup-gmail-secrets.sh

# Oppure per SendGrid SMTP (Opzione B)
./scripts/setup-sendgrid-secrets.sh
```

Lo script ti chiederà:
1. ✅ Password database PostgreSQL
2. ✅ Gmail App Password (o SendGrid API Key)
3. ✅ Configurerà automaticamente Secret Manager e permessi

---

#### 📖 Metodo MANUALE (Alternativo)

<details>
<summary><b>Click per vedere comandi manuali</b></summary>

```bash
# Abilita Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Crea secret per DB password
echo -n "LA_TUA_PASSWORD_DATABASE" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic"

# Per Gmail: Crea secret per App Password
echo -n "abcdefghijklmnop" | gcloud secrets create gmail-app-password \
    --data-file=- \
    --replication-policy="automatic"

# OPPURE per SendGrid: Crea secret per API Key
echo -n "SG.xxxxxxxxxxxxxxxxxxxxxxxx" | gcloud secrets create sendgrid-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Dai accesso al Service Account
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:ainaudi-prod@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gmail-app-password \
    --member="serviceAccount:ainaudi-prod@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Verifica secrets
gcloud secrets list
```

</details>

---

**⚠️ IMPORTANTE**: Verifica che `backend_django/app.yaml` usi i secrets:

```yaml
env_variables:
  # Database
  DB_PASSWORD: "secret://projects/ainaudi-prod/secrets/db-password/versions/latest"

  # Email (Gmail)
  EMAIL_HOST_PASSWORD: "secret://projects/ainaudi-prod/secrets/gmail-app-password/versions/latest"

  # Oppure Email (SendGrid)
  # EMAIL_HOST_PASSWORD: "secret://projects/ainaudi-prod/secrets/sendgrid-api-key/versions/latest"
```

### 8. Configura Variabili d'Ambiente Locali

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

# Email SMTP (Gmail - Opzione A)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=s.federici@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop  # Gmail App Password (16 caratteri)
DEFAULT_FROM_EMAIL=s.federici@gmail.com

# Oppure Email SMTP (SendGrid - Opzione B)
# EMAIL_HOST=smtp.sendgrid.net
# EMAIL_HOST_USER=apikey
# EMAIL_HOST_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxx
# DEFAULT_FROM_EMAIL=noreply@m5s.it
```

### 9. Testa Configurazione Email (Locale)

**Prima di deployare**, testa che l'invio email funzioni in locale:

#### Con Docker (Raccomandato)

```bash
# 1. Configura .env.docker con i valori reali (vedi Step 8)
nano .env.docker

# 2. Riavvia Docker per applicare modifiche
docker-compose down
docker-compose up -d

# 3. Test invio email (script automatico)
./scripts/test-email.sh tua@email.com

# Oppure manualmente:
docker-compose exec backend python test_email.py tua@email.com
```

#### Senza Docker

```bash
# 1. Configura .env con i valori reali (vedi Step 8)
nano backend_django/.env

# 2. Test invio email
cd backend_django
python test_email.py tua@email.com
```

**Output atteso:**
```
✅ Email inviata con successo!
📬 Controlla la casella di posta di: tua@email.com
   (Controlla anche spam/promozioni)
```

**Se fallisce:**
- Verifica che `EMAIL_HOST_PASSWORD` sia corretto (App Password Gmail a 16 caratteri, senza spazi)
- Verifica che autenticazione 2FA sia attiva su Gmail
- Controlla firewall (porta 587 deve essere aperta)
- Con Docker: verifica che `.env.docker` sia configurato correttamente

---

### 10. Inizializza App Engine

```bash
# Inizializza App Engine nella regione europe-west
gcloud app create --region=europe-west

# Verifica
gcloud app describe
```

### 10. Deploy Iniziale (Test)

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

### 11. Setup DNS e SSL (se dominio custom)

```bash
# Map custom domain to App Engine
gcloud app domain-mappings create yourdomain.com

# Verifica DNS records necessari
gcloud app domain-mappings describe yourdomain.com

# SSL certificate (automatico con App Engine)
# Oppure usa Let's Encrypt se Docker Compose
```

### 12. Monitoring e Logging

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
