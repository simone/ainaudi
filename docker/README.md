# Docker Setup per RDL Referendum

Setup Docker Compose per sviluppo e produzione.

## Quick Start (Sviluppo)

```bash
# 1. Copia il file di environment
cp .env.docker .env

# 2. Avvia tutti i servizi
docker-compose up -d

# 3. Crea le migrazioni Django (prima volta)
docker-compose exec backend python manage.py makemigrations

# 4. Esegui le migrazioni
docker-compose exec backend python manage.py migrate

# 5. Crea un superuser
docker-compose exec backend python manage.py createsuperuser
```

## Servizi

| Servizio | URL | Descrizione |
|----------|-----|-------------|
| Frontend | http://localhost:3000 | React dev server |
| Backend | http://localhost:3001 | Django API |
| Admin | http://localhost:3001/admin/ | Django Admin |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

## Comandi Utili

### Usando lo script helper

```bash
# Avvia
./docker/scripts/docker-dev.sh up

# Stop
./docker/scripts/docker-dev.sh down

# Logs
./docker/scripts/docker-dev.sh logs

# Solo backend logs
./docker/scripts/docker-dev.sh logs-back

# Django shell
./docker/scripts/docker-dev.sh shell

# Bash nel container
./docker/scripts/docker-dev.sh bash

# Migrazioni
./docker/scripts/docker-dev.sh migrate
./docker/scripts/docker-dev.sh makemig

# Crea superuser
./docker/scripts/docker-dev.sh superuser

# Tests
./docker/scripts/docker-dev.sh test

# PostgreSQL shell
./docker/scripts/docker-dev.sh psql

# Pulizia completa
./docker/scripts/docker-dev.sh clean

# Rebuild
./docker/scripts/docker-dev.sh rebuild
```

### Comandi Docker Compose diretti

```bash
# Avvia in background
docker-compose up -d

# Avvia con logs visibili
docker-compose up

# Stop
docker-compose down

# Stop e rimuovi volumi
docker-compose down -v

# Rebuild
docker-compose build --no-cache

# Logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f frontend

# Esegui comando in container
docker-compose exec backend python manage.py <command>
docker-compose exec db psql -U postgres -d rdl_referendum
```

## Struttura File

```
rdleu2024/
├── docker-compose.yml          # Sviluppo
├── docker-compose.prod.yml     # Produzione
├── .env.docker                 # Template environment
├── .env                        # Environment (da .env.docker)
├── docker/
│   ├── frontend.Dockerfile     # Frontend dev
│   ├── frontend.prod.Dockerfile # Frontend prod
│   ├── nginx.conf              # Nginx dev
│   ├── nginx.prod.conf         # Nginx prod
│   ├── init-db.sql             # DB initialization
│   ├── README.md               # Questa guida
│   └── scripts/
│       └── docker-dev.sh       # Script utility
└── backend_django/
    ├── Dockerfile              # Backend prod
    └── Dockerfile.dev          # Backend dev
```

## Configurazione Environment

Copia `.env.docker` in `.env` e configura:

```bash
# Obbligatori per sviluppo
DB_PASSWORD=postgres

# Per Google OAuth (opzionale in dev)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

## Hot Reload

- **Frontend**: Le modifiche in `src/` sono automaticamente rilevate
- **Backend**: Le modifiche in `backend_django/` sono automaticamente rilevate

## Database

### Accesso via CLI

```bash
docker-compose exec db psql -U postgres -d rdl_referendum
```

### Backup e Restore

```bash
# Backup
docker-compose exec db pg_dump -U postgres rdl_referendum > backup.sql

# Restore
docker-compose exec -T db psql -U postgres rdl_referendum < backup.sql
```

## Produzione

```bash
# Build e avvia in produzione
docker-compose -f docker-compose.prod.yml up -d --build

# Configura SSL in docker/nginx.prod.conf
# Metti certificati in docker/ssl/
```

## Troubleshooting

### Container non si avvia

```bash
# Controlla i logs
docker-compose logs backend

# Verifica che le porte non siano occupate
lsof -i :3000
lsof -i :3001
lsof -i :5432
```

### Database connection refused

```bash
# Aspetta che PostgreSQL sia pronto
docker-compose exec backend python -c "import django; django.setup()"

# Verifica health check
docker-compose ps
```

### Permessi su volume

```bash
# Se hai problemi di permessi sui file
sudo chown -R $(whoami) backend_django/
```

### Reset completo

```bash
# Rimuovi tutto e ricomincia
docker-compose down -v --remove-orphans
docker system prune -f
docker-compose up -d --build
```
