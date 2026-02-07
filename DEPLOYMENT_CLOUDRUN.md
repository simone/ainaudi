# Deployment Cloud Run - AInaudi RDL System

## ✅ Implementazione Completata

Migrazione completa da App Engine a **Cloud Run con PostgreSQL in container** (OPZIONE A).

### Funzionalità Implementate

#### Backend
- ✅ **Optimistic Locking**: Gestione conflitti concorrenti con versioning
- ✅ **Endpoint ottimizzati**: Preload leggero + dettaglio on-demand
- ✅ **Sub-deleghe per referendum**: Nascoste automaticamente per consultazioni referendum-only
- ✅ **PostgreSQL in container**: Elimina necessità di Cloud SQL

#### Frontend
- ✅ **Preload al login**: Lista seggi caricata in background (localStorage cache)
- ✅ **Gestione conflitti**: Alert + reload automatico su conflitto 409
- ✅ **Cache intelligente**: Invalidazione automatica su save

#### Infrastructure
- ✅ **Dockerfile multi-stage**: Django + PostgreSQL 15 nello stesso container
- ✅ **Persistent Disk**: 20GB SSD regional per dati PostgreSQL
- ✅ **Scaling scripts**: Boost evento e scale-down normale
- ✅ **Backup automatico**: Cloud Run Job + Cloud Scheduler (retention 30 giorni)

---

## 📦 File Creati

### Backend Django
```
backend_django/
├── Dockerfile.cloudrun                          # Multi-stage con PostgreSQL
├── docker/cloudrun-entrypoint.sh                # Startup script
├── data/
│   ├── models.py                                 # + optimistic locking fields
│   ├── views_scrutinio_optimized.py             # Nuovi endpoint
│   └── migrations/
│       └── 0012_add_optimistic_locking.py
├── elections/
│   ├── models.py                                 # + has_subdelegations()
│   └── migrations/
│       └── 0004_add_data_version_and_has_subdelegations.py
└── config/settings.py                            # + PostgreSQL pooling
```

### Frontend React
```
src/
├── Client.js                    # + mieiSeggiLight, sezioneDetail, saveSezione
├── App.js                       # + preload al login
├── SectionList.js               # + gestione conflitti 409
└── GestioneDeleghe.js           # + conditional rendering sub-deleghe
```

### Infrastructure
```
cloudrun/
├── service.yaml                 # Cloud Run service definition
├── persistent-volume.yaml       # 20GB SSD persistent disk
└── backup-job.yaml              # Backup PostgreSQL job

scripts/
├── cloudrun-scaling.sh          # Boost evento / scale-down
├── backup-postgres.sh           # Trigger backup manuale
├── deploy-frontend.sh           # Deploy React su Cloud Storage
└── test-optimized-endpoints.sh  # Test endpoint API
```

---

## 🚀 Deployment Step-by-Step

### 1. Preparazione Ambiente

```bash
# Set project variables
export PROJECT_ID="your-project-id"
export REGION="europe-west1"
export BUCKET_BACKUPS="rdl-backups-prod"
export BUCKET_FRONTEND="rdl-frontend-prod"
export DOMAIN="your-domain.com"

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    storage-api.googleapis.com \
    cloudscheduler.googleapis.com

# Create Artifact Registry repository
gcloud artifacts repositories create rdl \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID
```

### 2. Secrets Management

```bash
# Create database password secret
echo -n "your-secure-password" | \
    gcloud secrets create db-password \
    --data-file=- \
    --project=$PROJECT_ID

# Create email credentials secret
gcloud secrets create email-credentials \
    --data-file=email-credentials.json \
    --project=$PROJECT_ID

# Example email-credentials.json:
# {
#   "username": "noreply@your-domain.com",
#   "password": "app-specific-password",
#   "from_email": "AInaudi <noreply@your-domain.com>"
# }
```

### 3. Build & Push Docker Image

```bash
cd backend_django

# Build image locally (test)
docker build -f Dockerfile.cloudrun -t rdl-backend:test .

# Test locally
docker run -p 8080:8080 \
    -e DB_PASSWORD=test \
    -e DEBUG=True \
    rdl-backend:test

# Build & push to Artifact Registry
gcloud builds submit . \
    --tag=$REGION-docker.pkg.dev/$PROJECT_ID/rdl/backend:latest \
    --project=$PROJECT_ID

# Tag as specific version
gcloud builds submit . \
    --tag=$REGION-docker.pkg.dev/$PROJECT_ID/rdl/backend:v1.0.0 \
    --project=$PROJECT_ID
```

### 4. Deploy Cloud Run Service

```bash
# Create Persistent Disk for PostgreSQL
# Note: Cloud Run gen2 supporta Persistent Disk (preview)
gcloud compute disks create rdl-postgres-disk \
    --size=20GB \
    --type=pd-ssd \
    --region=$REGION \
    --project=$PROJECT_ID

# Deploy Cloud Run service
gcloud run deploy rdl-backend \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/rdl/backend:latest \
    --platform=managed \
    --region=$REGION \
    --project=$PROJECT_ID \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=5 \
    --cpu=1 \
    --memory=1Gi \
    --set-env-vars="DB_HOST=localhost,DB_PORT=5432,DB_NAME=rdl_referendum,DB_USER=postgres,POSTGRES_MAX_CONNECTIONS=100,GUNICORN_WORKERS=2,GUNICORN_THREADS=4,FRONTEND_URL=https://$DOMAIN,ALLOWED_HOSTS=$DOMAIN,DEBUG=False" \
    --set-secrets="DB_PASSWORD=db-password:latest,EMAIL_HOST_USER=email-credentials:latest.username,EMAIL_HOST_PASSWORD=email-credentials:latest.password,DEFAULT_FROM_EMAIL=email-credentials:latest.from_email" \
    --execution-environment=gen2 \
    --no-cpu-throttling

# Note: Persistent Disk mount richiede configurazione aggiuntiva via YAML
# Per ora usa volume mount temporaneo, poi migrare a Persistent Disk
```

**IMPORTANTE**: Cloud Run gen2 con Persistent Disk è ancora in preview. Alternative:
- **Opzione A (attuale)**: Usare volume temporaneo + backup giornaliero
- **Opzione B**: Migrare a GKE Autopilot per supporto completo Persistent Volumes
- **Opzione C**: Usare Cloud SQL Managed PostgreSQL (costo maggiore)

### 5. Setup Backup Automatico

```bash
# Create Cloud Storage bucket per backup
gcloud storage buckets create gs://$BUCKET_BACKUPS \
    --location=$REGION \
    --project=$PROJECT_ID

# Create Cloud Run Job per backup
gcloud run jobs create postgres-backup \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/rdl/backend:latest \
    --region=$REGION \
    --project=$PROJECT_ID \
    --command="/bin/bash" \
    --args="-c,/app/scripts/backup-script.sh" \
    --set-env-vars="BACKUP_BUCKET=gs://$BUCKET_BACKUPS" \
    --set-secrets="DB_PASSWORD=db-password:latest" \
    --max-retries=2 \
    --task-timeout=10m

# Schedule backup giornaliero (2 AM)
gcloud scheduler jobs create http postgres-daily-backup \
    --location=$REGION \
    --schedule="0 2 * * *" \
    --time-zone="Europe/Rome" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/postgres-backup:run" \
    --http-method=POST \
    --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com
```

### 6. Deploy Frontend Statico

```bash
# Create Cloud Storage bucket
gcloud storage buckets create gs://$BUCKET_FRONTEND \
    --location=$REGION \
    --project=$PROJECT_ID

# Enable website configuration
gcloud storage buckets update gs://$BUCKET_FRONTEND \
    --web-main-page-suffix=index.html \
    --web-error-page=index.html

# Make bucket public
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_FRONTEND \
    --member=allUsers \
    --role=roles/storage.objectViewer

# Deploy frontend
cd ..  # Back to project root
REACT_APP_API_URL=https://api.$DOMAIN npm run build
gsutil -m rsync -r -d build/ gs://$BUCKET_FRONTEND/

# Set cache headers
gsutil -m setmeta -h "Cache-Control:public,max-age=31536000,immutable" "gs://$BUCKET_FRONTEND/static/**"
gsutil -m setmeta -h "Cache-Control:no-cache" "gs://$BUCKET_FRONTEND/index.html"

# Setup Cloud CDN (optional)
gcloud compute backend-buckets create rdl-frontend-backend \
    --gcs-bucket-name=$BUCKET_FRONTEND \
    --enable-cdn

gcloud compute url-maps create rdl-frontend-lb \
    --default-backend-bucket=rdl-frontend-backend

gcloud compute target-http-proxies create rdl-frontend-proxy \
    --url-map=rdl-frontend-lb

gcloud compute forwarding-rules create rdl-frontend-http \
    --global \
    --target-http-proxy=rdl-frontend-proxy \
    --ports=80
```

### 7. DNS Configuration

```bash
# Get Cloud Run service URL
BACKEND_URL=$(gcloud run services describe rdl-backend \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"

# Get Load Balancer IP
FRONTEND_IP=$(gcloud compute forwarding-rules describe rdl-frontend-http \
    --global \
    --format='value(IPAddress)')

echo "Frontend IP: $FRONTEND_IP"

# Configure DNS:
# - api.$DOMAIN CNAME → $BACKEND_URL (Cloud Run)
# - $DOMAIN A → $FRONTEND_IP (Load Balancer)
```

---

## 🎯 Scaling per Evento

### 1 Mese Prima dello Scrutinio (~27 Febbraio)

```bash
# Scale UP per gestire carico evento
./scripts/cloudrun-scaling.sh evento
```

**Configurazione Evento:**
- Min instances: 1 → **2** (sempre calde)
- Max instances: 5 → **10**
- CPU: 1 → **2 vCPU** per instance
- Memory: 1Gi → **2Gi** per instance
- PostgreSQL max_connections: 100 → **200**
- Gunicorn workers: 2 → **4** per instance

**Capacità Totale:**
- Max concurrent requests: 10 instances × 80 = **800 req/s**
- Max database connections: 10 instances × 20 = **200 connessioni**
- **Sufficiente per 200-300 RDL simultanei** durante scrutinio

**Costo Stimato (1 settimana):** ~$20-30

### 1 Settimana Dopo lo Scrutinio (~3 Aprile)

```bash
# Scale DOWN al normale
./scripts/cloudrun-scaling.sh normale
```

**Costo Normale:** ~$9-16/mese

---

## 📊 Monitoring & Troubleshooting

### Logs

```bash
# View backend logs
gcloud run services logs read rdl-backend \
    --region=$REGION \
    --project=$PROJECT_ID \
    --limit=100

# Follow logs in real-time
gcloud run services logs tail rdl-backend \
    --region=$REGION \
    --project=$PROJECT_ID

# Filter by error
gcloud run services logs read rdl-backend \
    --region=$REGION \
    --log-filter='severity>=ERROR'
```

### Metrics

```bash
# View metrics in Cloud Console
echo "https://console.cloud.google.com/run/detail/$REGION/rdl-backend/metrics?project=$PROJECT_ID"

# Key metrics to monitor:
# - Request count & latency
# - Instance count (min/current/max)
# - CPU & Memory utilization
# - Container startup time
# - Error rate
```

### Database Health

```bash
# Connect to PostgreSQL (inside container)
gcloud run services proxy rdl-backend --region=$REGION &
# In another terminal:
docker exec -it <container_id> psql -U postgres -d rdl_referendum

# Check active connections
SELECT count(*) AS active,
       (SELECT setting::int FROM pg_settings WHERE name='max_connections') AS max
FROM pg_stat_activity;

# Check cache hit ratio (should be >95%)
SELECT blks_hit::float / (blks_hit + blks_read) * 100 AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = 'rdl_referendum';

# Check database size
SELECT pg_size_pretty(pg_database_size('rdl_referendum'));
```

### Backup Verification

```bash
# List backups
gsutil ls gs://$BUCKET_BACKUPS/

# Restore from backup (example)
BACKUP_FILE="postgres_backup_20260207_120000.sql.gz"
gsutil cp gs://$BUCKET_BACKUPS/$BACKUP_FILE /tmp/
gunzip /tmp/$BACKUP_FILE
psql -U postgres -d rdl_referendum < /tmp/postgres_backup_20260207_120000.sql
```

---

## 🔧 Troubleshooting Comune

### Errore "column does not exist"

```bash
# Verificare migrations
docker exec rdl_backend python manage.py showmigrations

# Eseguire migrations mancanti
docker exec rdl_backend python manage.py migrate

# Riavviare container
docker restart rdl_backend
```

### Performance Issues

```bash
# Check database connections
docker exec rdl_backend python manage.py shell -c "
from django.db import connection
print('Connections:', connection.queries)
"

# Increase resources
./scripts/cloudrun-scaling.sh evento  # Even if not event day
```

### Out of Memory

```bash
# Increase memory per instance
gcloud run services update rdl-backend \
    --memory=2Gi \
    --region=$REGION
```

---

## 💰 Costi Stimati (OPZIONE A)

### Configurazione Normale (11 mesi/anno)
- **Cloud Run**: 1-5 instances × 1 vCPU × 1Gi
  - Request processing: ~$5-10/mese
  - Always-allocated CPU (per PostgreSQL): ~$3/mese
- **Persistent Disk**: 20GB SSD
  - $0.17/GB/mese = ~$3.40/mese
- **Cloud Storage**: Backup 20GB × $0.026/GB = ~$0.50/mese
- **Frontend CDN**: ~$1-2/mese

**Totale Normale: $12-18/mese**

### Configurazione Evento (1 settimana/anno)
- **Cloud Run**: 2-10 instances × 2 vCPU × 2Gi
  - Request processing: ~$15-25/settimana
  - Always-allocated CPU: ~$5/settimana

**Totale Evento: $20-30/settimana**

### Risparmio vs Cloud SQL (OPZIONE B)
- Cloud SQL db-custom-1-3840: **$60/mese**
- Cloud SQL db-custom-2-7680 (evento): **$120/mese**
- **Risparmio OPZIONE A: $50-100/mese**

---

## 📚 Risorse Utili

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)
- [Django Database Optimization](https://docs.djangoproject.com/en/5.2/topics/db/optimization/)
- [Cloud Storage Static Website](https://cloud.google.com/storage/docs/hosting-static-website)

---

## ✅ Checklist Pre-Go-Live

- [ ] Migrations database eseguite e verificate
- [ ] Secrets configurati (DB_PASSWORD, email)
- [ ] Backend deployato su Cloud Run
- [ ] Frontend deployato su Cloud Storage
- [ ] DNS configurato correttamente
- [ ] SSL/TLS certificates attivi
- [ ] Backup automatico schedulato e testato
- [ ] Monitoring alerts configurati
- [ ] Load testing eseguito (200 RDL simultanei)
- [ ] Rollback plan documentato
- [ ] Team training su scaling script

---

**Implementazione completata il**: 7 Febbraio 2026
**Prossimo milestone**: Scale-up evento (~27 Febbraio 2026)
**Scrutinio previsto**: 27 Marzo 2026
