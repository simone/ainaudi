# Deployment in Produzione

## Architettura Semplificata

Dopo il refactoring della generazione PDF (da asincrona a sincrona), il deployment di produzione richiede solo **3 servizi**:

```
┌─────────────┐
│  Frontend   │  React build servito da Nginx
│  (Nginx)    │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Backend   │  Django REST API + PDF generation
│  (Python)   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Database   │  PostgreSQL 15
│ (Postgres)  │
└─────────────┘
```

### Servizi Rimossi

- ❌ **Redis**: Era usato solo per event bus PDF asincrono (deprecato)
- ❌ **PDF Worker**: Generazione PDF ora sincrona nel backend Django

## Docker Compose Production

### Quick Start

```bash
# 1. Configura variabili d'ambiente
cp .env.example .env
# Edita .env con le tue credenziali

# 2. Build e avvia servizi
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Verifica health
docker-compose -f docker-compose.prod.yml ps
```

### Servizi Attivi

1. **db** (postgres:15-alpine)
   - Porta: 5432 (interna)
   - Volume: `postgres_data_prod`
   - Security: read-only filesystem, non-root user

2. **backend** (Django distroless)
   - Porta: 8000 (interna)
   - Volumes: `backend_static_prod`, `backend_media_prod`
   - Security: distroless image, non-root (uid 65532), read-only filesystem

3. **frontend** (nginx-unprivileged)
   - Porta: interna
   - Build React statico
   - Security: read-only filesystem, non-root user

4. **nginx** (reverse proxy)
   - Porte: 80 (HTTP), 443 (HTTPS)
   - Gestisce SSL/TLS
   - Serve file statici e media
   - Proxy verso backend

### Variabili d'Ambiente Richieste

```bash
# Database
DB_NAME=rdl_referendum
DB_USER=postgres
DB_PASSWORD=<strong-password>

# Django
DJANGO_SECRET_KEY=<generate-with-django-generate-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com

# Google OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=<app-password>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### SSL/TLS Setup

```bash
# Genera certificati (o usa Let's Encrypt)
mkdir -p docker/ssl
# Copia i tuoi certificati:
# - docker/ssl/cert.pem
# - docker/ssl/key.pem
```

### Gestione

```bash
# Logs
docker-compose -f docker-compose.prod.yml logs -f [service]

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres rdl_referendum > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres rdl_referendum < backup.sql

# Update e restart
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build

# Stop
docker-compose -f docker-compose.prod.yml down
```

## Google App Engine (Alternativa)

Se preferisci GAE invece di Docker:

### Servizi Attivi

1. **default** (Frontend - Node.js)
   - File: `app.yaml`
   - Serve build React statico
   - Auto-scaling: 0-50 istanze

2. **backend** (Django - Python 3.11)
   - File: `backend_django/app.yaml`
   - Cloud SQL connection automatica
   - Auto-scaling: 0-5 istanze

### Deploy

```bash
# Frontend
npm run build
gcloud app deploy app.yaml --project=rdl-europee-2024

# Backend
cd backend_django
python manage.py collectstatic --noinput
gcloud app deploy app.yaml --project=rdl-europee-2024
```

### Servizi Deprecati

- ❌ **pdf** service: `pdf/app.yaml` è stato deprecato
- ❌ dispatch per `/api/generate/*`: rimosso da `dispatch.yaml`

## Cloud Run (Alternativa)

File disponibili in `cloudrun/`:

- `service.yaml` - Configurazione service
- `persistent-volume.yaml` - Volume per media files
- `backup-job.yaml` - Backup automatico database

```bash
# Deploy
gcloud run services replace cloudrun/service.yaml --region=europe-west1
```

## Monitoring e Health Checks

### Endpoints

- **Frontend**: `https://yourdomain.com/`
- **Backend Health**: `https://yourdomain.com/api/health/`
- **Backend Admin**: `https://yourdomain.com/admin/`

### Metrics

```bash
# Docker stats
docker stats rdl_postgres_prod rdl_backend_prod rdl_frontend_prod rdl_nginx_prod

# Database size
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('rdl_referendum'));"
```

## Troubleshooting

### Backend non raggiungibile

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Verifica migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Frontend 502 Bad Gateway

```bash
# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Verifica proxy_pass in nginx.prod.conf
```

### Database connection refused

```bash
# Check database health
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Check network
docker network inspect rdl_network
```

## Security Checklist

- ✅ All services run as non-root users
- ✅ Read-only filesystems where possible
- ✅ Distroless images (backend)
- ✅ no-new-privileges security opt
- ✅ Dropped all capabilities
- ✅ HTTPS only (secure: always)
- ✅ Strong database password
- ✅ Django SECRET_KEY in environment
- ✅ ALLOWED_HOSTS configured
- ✅ CORS properly configured

## Performance

### Recommended Resources

**Produzione piccola/media (< 1000 utenti simultanei)**:
- Backend: 1-2 CPU, 2-4 GB RAM
- Database: 1-2 CPU, 4-8 GB RAM
- Frontend: 0.5 CPU, 512 MB RAM
- Nginx: 0.5 CPU, 512 MB RAM

**Produzione grande (> 1000 utenti simultanei)**:
- Backend: 2-4 CPU, 4-8 GB RAM (scalabile orizzontalmente)
- Database: 2-4 CPU, 8-16 GB RAM
- Frontend: 1 CPU, 1 GB RAM
- Nginx: 1 CPU, 1 GB RAM

### Database Tuning

```sql
-- Ottimizzazioni PostgreSQL per produzione
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET max_connections = 100;
```

## Backup Strategy

1. **Database**: Backup automatico giornaliero
2. **Media files**: Sync su Google Cloud Storage
3. **Configurazione**: Repository Git

```bash
# Script backup giornaliero (crontab)
0 3 * * * /path/to/backup-script.sh
```

## Support

Per problemi o domande:
- Issues: https://github.com/m5s/rdleu2024/issues
- Email: support@m5s.it
