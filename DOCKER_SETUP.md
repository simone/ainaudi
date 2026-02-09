# 🐳 Docker Setup - Sviluppo Locale

Guida rapida per avviare AInaudi in locale con Docker.

---

## 🚀 Quick Start (5 minuti)

### 1. Copia configurazione esempio

```bash
cp .env.docker.example .env.docker
```

**Variabili importanti da configurare (opzionale):**
- `VITE_RDL_REGISTRATION_URL`: URL form registrazione RDL (default: Google Form)
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: SMTP per invio email (vedi sezione Email)
- `DEFAULT_FROM_EMAIL`: Mittente email con display name

### 2. Avvia tutto

```bash
docker-compose up -d
```

**Servizi avviati:**
- **Frontend**: http://localhost:3000 (React)
- **Backend API**: http://localhost:3001 (Django)
- **Database**: PostgreSQL su porta 5432

### 3. Esegui migrations

```bash
docker-compose exec backend python manage.py migrate
```

### 4. Crea superuser

```bash
docker-compose exec backend python manage.py createsuperuser
```

### 5. Accedi

Vai su http://localhost:3000 e usa Magic Link con la tua email.

**FATTO!** 🎉

---

## 📧 Configurare Email (Opzionale)

Di default, le email vengono **stampate nel log** invece di essere inviate.

Per **inviare email reali** (necessario per testare Magic Link):

### Opzione A: Gmail (Semplice)

1. **Genera App Password Gmail**:
   - https://myaccount.google.com/apppasswords
   - App: Mail
   - Dispositivo: "AInaudi Django"
   - Copia password (16 caratteri)

2. **Modifica `.env.docker`**:

```bash
# Decommenta e configura
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tuo@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop  # App Password
DEFAULT_FROM_EMAIL=tuo@gmail.com
```

3. **Riavvia Docker**:

```bash
docker-compose down
docker-compose up -d
```

4. **Testa invio**:

```bash
./scripts/test-email.sh tuo@email.com
```

### Opzione B: SendGrid

Vedi `GMAIL_SETUP.md` sezione SendGrid.

---

## 🛠️ Comandi Utili

### Gestione servizi

```bash
# Avvia servizi
docker-compose up -d

# Ferma servizi
docker-compose down

# Riavvia servizi
docker-compose restart

# Vedi logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Vedi status
docker-compose ps
```

### Database

```bash
# Esegui migrations
docker-compose exec backend python manage.py migrate

# Crea migrations
docker-compose exec backend python manage.py makemigrations

# Shell Django
docker-compose exec backend python manage.py shell

# Accesso PostgreSQL
docker-compose exec postgres psql -U postgres ainaudi_db
```

### Backend Django

```bash
# Shell Django
docker-compose exec backend python manage.py shell

# Crea superuser
docker-compose exec backend python manage.py createsuperuser

# Collectstatic
docker-compose exec backend python manage.py collectstatic --noinput

# Test
docker-compose exec backend python manage.py test

# Test invio email
docker-compose exec backend python test_email.py tuo@email.com
```

### Frontend React

```bash
# Shell frontend
docker-compose exec frontend sh

# Rebuild frontend (se modifichi package.json)
docker-compose down
docker-compose up -d --build frontend
```

### Reset completo

```bash
# ATTENZIONE: Elimina TUTTI i dati
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

---

## 🐛 Troubleshooting

### Port 3000/3001 già in uso

```bash
# Trova processo che usa porta 3000
lsof -ti:3000

# Kill processo
kill -9 $(lsof -ti:3000)
```

### Database connection refused

```bash
# Verifica che postgres sia up
docker-compose ps

# Riavvia postgres
docker-compose restart postgres

# Vedi logs
docker-compose logs postgres
```

### Email non parte

1. Verifica configurazione `.env.docker`
2. Verifica che Gmail App Password sia corretta (16 caratteri, senza spazi)
3. Verifica logs: `docker-compose logs backend`
4. Testa con: `./scripts/test-email.sh tuo@email.com`

### Cambio configurazione non applicato

Devi riavviare i container:

```bash
docker-compose down
docker-compose up -d
```

---

## 📁 Struttura File Importanti

```
.env.docker          # Configurazione Docker (gitignored)
.env.docker.example  # Template configurazione
docker-compose.yml   # Configurazione servizi Docker
```

---

## 🔒 Sicurezza

**NON committare mai `.env.docker` su Git!**

Il file è già in `.gitignore`, ma verifica sempre prima di fare commit:

```bash
git status  # .env.docker NON deve apparire
```

---

## 📖 Documentazione

- **Setup Gmail**: `GMAIL_SETUP.md`
- **Setup Produzione GCP**: `PRODUCTION_SETUP.md`
- **Architettura**: `CLAUDE.md`
