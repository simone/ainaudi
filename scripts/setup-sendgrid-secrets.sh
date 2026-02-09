#!/bin/bash
# Script per configurare SendGrid e Secret Manager su GCP
# Uso: ./scripts/setup-sendgrid-secrets.sh

set -e  # Exit on error

PROJECT_ID="ainaudi-prod"
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup SendGrid + Secret Manager per AInaudi"
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

# Chiedi SendGrid API Key
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: SendGrid API Key"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📧 Vai su SendGrid per ottenere la API Key:"
echo "   1. https://app.sendgrid.com/settings/api_keys"
echo "   2. Create API Key → Nome: 'ainaudi-prod' → Full Access"
echo "   3. Copia la chiave (inizia con SG.xxx...)"
echo ""
echo "Inserisci la SendGrid API Key:"
read -sp "SendGrid API Key: " SENDGRID_KEY
echo ""

if [ -z "$SENDGRID_KEY" ]; then
    echo "❌ SendGrid API Key obbligatoria!"
    exit 1
fi

# Valida formato SendGrid key
if [[ ! "$SENDGRID_KEY" =~ ^SG\. ]]; then
    echo "⚠️  Warning: La chiave non inizia con 'SG.' - sei sicuro sia corretta?"
    read -p "Continuo comunque? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Crea secret sendgrid
echo ""
echo "🔐 Creo secret 'sendgrid-api-key'..."
echo -n "$SENDGRID_KEY" | gcloud secrets create sendgrid-api-key \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
    echo -n "$SENDGRID_KEY" | gcloud secrets versions add sendgrid-api-key --data-file=-

# Assegna permessi al Service Account
echo ""
echo "🔑 Assegno permessi al Service Account..."
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

gcloud secrets add-iam-policy-binding sendgrid-api-key \
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
echo "     DB_PASSWORD: secret://projects/${PROJECT_ID}/secrets/db-password/versions/latest"
echo "     EMAIL_HOST_PASSWORD: secret://projects/${PROJECT_ID}/secrets/sendgrid-api-key/versions/latest"
echo ""
echo "2. Deploy backend:"
echo "   cd backend_django"
echo "   gcloud app deploy app.yaml"
echo ""
echo "3. Testa invio email:"
echo "   python manage.py shell"
echo "   >>> from django.core.mail import send_mail"
echo "   >>> send_mail('Test', 'Messaggio', 'noreply@m5s.it', ['tua@email.com'])"
echo ""
