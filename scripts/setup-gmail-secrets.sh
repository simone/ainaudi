#!/bin/bash
# Script per configurare Gmail SMTP e Secret Manager su GCP
# Uso: ./scripts/setup-gmail-secrets.sh

set -e  # Exit on error

PROJECT_ID="ainaudi-prod"
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
GMAIL_USER="s.federici@gmail.com"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup Gmail SMTP + Secret Manager per AInaudi"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verifica progetto attivo
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠️  Progetto attivo: $CURRENT_PROJECT"
    echo "📝 Imposto progetto a: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
fi

# Abilita Secret Manager API
echo ""
echo "📦 Abilito Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Chiedi password database
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1: Database Password"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Inserisci la password del database PostgreSQL (Cloud SQL):"
read -sp "DB Password: " DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Password database obbligatoria!"
    exit 1
fi

# Crea secret database
echo ""
echo "🔐 Creo secret 'db-password'..."
echo -n "$DB_PASSWORD" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
    echo -n "$DB_PASSWORD" | gcloud secrets versions add db-password --data-file=-

# Chiedi Gmail App Password
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Gmail App Password"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📧 Per generare una App Password Gmail:"
echo ""
echo "   1. Vai su: https://myaccount.google.com/security"
echo "   2. Abilita 'Verifica in due passaggi' se non l'hai già fatto"
echo "   3. Vai su: https://myaccount.google.com/apppasswords"
echo "   4. Seleziona:"
echo "      - App: Mail"
echo "      - Dispositivo: Altro → scrivi 'AInaudi Django'"
echo "   5. Clicca 'Genera'"
echo "   6. Copia la password di 16 caratteri (es: abcd efgh ijkl mnop)"
echo ""
echo "📝 Account Gmail: ${GMAIL_USER}"
echo ""
echo "Inserisci la Gmail App Password (16 caratteri, senza spazi):"
read -sp "Gmail App Password: " GMAIL_PASSWORD
echo ""

if [ -z "$GMAIL_PASSWORD" ]; then
    echo "❌ Gmail App Password obbligatoria!"
    exit 1
fi

# Rimuovi spazi dalla password
GMAIL_PASSWORD=$(echo "$GMAIL_PASSWORD" | tr -d ' ')

# Valida lunghezza
if [ ${#GMAIL_PASSWORD} -ne 16 ]; then
    echo "⚠️  Warning: La password dovrebbe essere di 16 caratteri (trovati: ${#GMAIL_PASSWORD})"
    echo "   Formato corretto: abcdefghijklmnop (senza spazi)"
    read -p "Continuo comunque? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Crea secret gmail
echo ""
echo "🔐 Creo secret 'gmail-app-password'..."
echo -n "$GMAIL_PASSWORD" | gcloud secrets create gmail-app-password \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
    echo -n "$GMAIL_PASSWORD" | gcloud secrets versions add gmail-app-password --data-file=-

# Assegna permessi al Service Account
echo ""
echo "🔑 Assegno permessi al Service Account..."
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

gcloud secrets add-iam-policy-binding gmail-app-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

# Verifica secrets
echo ""
echo "✅ Secrets creati con successo!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Lista Secrets:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
gcloud secrets list

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ SETUP COMPLETATO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Prossimi passi:"
echo ""
echo "1. Verifica che backend_django/app.yaml usi i secrets:"
echo "   env_variables:"
echo "     EMAIL_HOST: smtp.gmail.com"
echo "     EMAIL_HOST_USER: ${GMAIL_USER}"
echo "     DB_PASSWORD: secret://projects/${PROJECT_ID}/secrets/db-password/versions/latest"
echo "     EMAIL_HOST_PASSWORD: secret://projects/${PROJECT_ID}/secrets/gmail-app-password/versions/latest"
echo ""
echo "2. Aggiorna .env locale per test:"
echo "   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend"
echo "   EMAIL_HOST=smtp.gmail.com"
echo "   EMAIL_HOST_USER=${GMAIL_USER}"
echo "   EMAIL_HOST_PASSWORD=<la-tua-app-password>"
echo ""
echo "3. Testa invio email in locale:"
echo "   cd backend_django"
echo "   python test_email.py tua@email.com"
echo ""
echo "4. Deploy su App Engine:"
echo "   python manage.py collectstatic --noinput"
echo "   gcloud app deploy app.yaml"
echo ""
echo "⚠️  IMPORTANTE: Gmail ha limite di 500 email/giorno"
echo "   Per volumi maggiori, considera SendGrid o altro provider SMTP"
echo ""
