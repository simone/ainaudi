#!/bin/bash
# Script per eseguire migrations Django su Cloud SQL (produzione)
# Usage: ./scripts/migrate-production.sh [--project PROJECT_ID]

set -e  # Exit on error

# Default values
PROJECT="ainaudi-prod"
REGION="europe-west1"
INSTANCE="ainaudi-db"
DB_NAME="ainaudi_db"
DB_USER="postgres"
PROXY_PORT=5433  # Usa porta diversa da 5432 per evitare conflitti

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Esegue migrations Django su Cloud SQL di produzione usando Cloud SQL Proxy"
      echo ""
      echo "Options:"
      echo "  --project PROJECT   Specifica il project ID GCP (default: ainaudi-prod)"
      echo "  --help, -h          Mostra questo messaggio"
      echo ""
      exit 0
      ;;
    *)
      echo -e "${RED}❌ Opzione sconosciuta: $1${NC}"
      echo "Usa --help per vedere le opzioni disponibili"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Migrations Django su Cloud SQL (Produzione)          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📋 Configurazione:${NC}"
echo -e "   Project ID: ${GREEN}${PROJECT}${NC}"
echo -e "   Instance: ${GREEN}${INSTANCE}${NC}"
echo -e "   Database: ${GREEN}${DB_NAME}${NC}"
echo -e "   Proxy Port: ${GREEN}${PROXY_PORT}${NC}"
echo ""

# Verify gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI non trovato. Installalo da: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Verify Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 non trovato${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}🔧 Configurazione progetto GCP...${NC}"
gcloud config set project ${PROJECT}

# Check if Cloud SQL Proxy is installed
PROXY_CMD=""
if command -v cloud-sql-proxy &> /dev/null; then
    PROXY_CMD="cloud-sql-proxy"
    echo -e "${GREEN}✅ Cloud SQL Proxy trovato${NC}"
elif command -v cloud_sql_proxy &> /dev/null; then
    PROXY_CMD="cloud_sql_proxy"
    echo -e "${GREEN}✅ Cloud SQL Proxy trovato${NC}"
elif [ -f "./cloud-sql-proxy" ]; then
    PROXY_CMD="./cloud-sql-proxy"
    echo -e "${GREEN}✅ Cloud SQL Proxy trovato (local)${NC}"
else
    echo -e "${YELLOW}⚠️  Cloud SQL Proxy non trovato. Download in corso...${NC}"

    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [[ $(uname -m) == "arm64" ]]; then
            PROXY_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.2/cloud-sql-proxy.darwin.arm64"
        else
            PROXY_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.2/cloud-sql-proxy.darwin.amd64"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PROXY_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.2/cloud-sql-proxy.linux.amd64"
    else
        echo -e "${RED}❌ OS non supportato: $OSTYPE${NC}"
        echo -e "${YELLOW}Scarica manualmente Cloud SQL Proxy da:${NC}"
        echo "https://cloud.google.com/sql/docs/postgres/sql-proxy"
        exit 1
    fi

    curl -o cloud-sql-proxy "$PROXY_URL"
    chmod +x cloud-sql-proxy
    PROXY_CMD="./cloud-sql-proxy"
    echo -e "${GREEN}✅ Cloud SQL Proxy scaricato${NC}"
fi

# Get DB password from Secret Manager
echo ""
echo -e "${YELLOW}🔐 Recupero password database da Secret Manager...${NC}"
DB_PASSWORD=$(gcloud secrets versions access latest --secret=db-password --project=${PROJECT} 2>/dev/null || echo "")

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  Password non trovata in Secret Manager (secret: db-password)${NC}"
    echo -e "${YELLOW}Inserisci la password del database manualmente:${NC}"
    read -sp "DB Password: " DB_PASSWORD
    echo ""

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}❌ Password non fornita. Uscita.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Password recuperata${NC}"

# Start Cloud SQL Proxy in background
echo ""
echo -e "${YELLOW}🚀 Avvio Cloud SQL Proxy...${NC}"
CONNECTION_NAME="${PROJECT}:${REGION}:${INSTANCE}"

# Kill existing proxy if running on same port
lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true

# Start proxy in background
$PROXY_CMD "$CONNECTION_NAME" --port ${PROXY_PORT} &
PROXY_PID=$!

# Trap to kill proxy on script exit
trap "echo -e '\n${YELLOW}🛑 Chiusura Cloud SQL Proxy...${NC}'; kill $PROXY_PID 2>/dev/null; exit" INT TERM EXIT

echo -e "${GREEN}✅ Cloud SQL Proxy avviato (PID: $PROXY_PID)${NC}"
echo -e "${YELLOW}⏳ Attendo connessione...${NC}"
sleep 3

# Export database connection variables
export DB_HOST="127.0.0.1"
export DB_PORT="${PROXY_PORT}"
export DB_NAME="${DB_NAME}"
export DB_USER="${DB_USER}"
export DB_PASSWORD="${DB_PASSWORD}"
export DEBUG="False"
export GOOGLE_CLOUD_PROJECT="${PROJECT}"

# Test database connection
echo ""
echo -e "${YELLOW}🔍 Test connessione database...${NC}"
cd backend_django

if python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port=${DB_PORT},
        dbname='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}'
    )
    conn.close()
    print('✅ Connessione OK')
except Exception as e:
    print(f'❌ Errore: {e}')
    exit(1)
" 2>&1; then
    echo -e "${GREEN}✅ Connessione al database riuscita${NC}"
else
    echo -e "${RED}❌ Impossibile connettersi al database${NC}"
    kill $PROXY_PID 2>/dev/null
    exit 1
fi

# Show migrations status
echo ""
echo -e "${YELLOW}📊 Stato migrations attuali:${NC}"
python3 manage.py showmigrations --settings=config.settings || true

# Run migrations
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 ESECUZIONE MIGRATIONS                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

python3 manage.py migrate --settings=config.settings

echo ""
echo -e "${GREEN}✅ Migrations completate${NC}"

# Ask if user wants to create superuser
echo ""
echo -e "${YELLOW}👤 Vuoi creare un superuser admin? (y/n)${NC}"
read -r CREATE_SUPERUSER

if [[ "$CREATE_SUPERUSER" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}📝 Creazione superuser...${NC}"
    python3 manage.py createsuperuser --settings=config.settings
    echo -e "${GREEN}✅ Superuser creato${NC}"
fi

# Show final status
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 📊 STATO FINALE                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

python3 manage.py showmigrations --settings=config.settings | grep -E "\[X\]" | wc -l | xargs -I {} echo -e "${GREEN}✅ {} migrations applicate${NC}"

# Cleanup
cd ..
kill $PROXY_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅ MIGRATIONS COMPLETATE CON SUCCESSO           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Ora puoi accedere all'admin:${NC}"
echo -e "   ${GREEN}https://${PROJECT}.appspot.com/admin/${NC}"
echo ""
