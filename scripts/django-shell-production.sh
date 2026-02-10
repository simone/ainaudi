#!/bin/bash
# Django management commands su database Cloud SQL produzione
# Usage: ./scripts/django-shell-production.sh [command]
#   ./scripts/django-shell-production.sh shell
#   ./scripts/django-shell-production.sh "cleanup_generic_denominazioni --dry-run"
#   ./scripts/django-shell-production.sh dbshell

set -e

# Default values
PROJECT="ainaudi-prod"
REGION="europe-west1"
INSTANCE="ainaudi-db"
DB_NAME="ainaudi_db"
DB_USER="postgres"
PROXY_PORT=5433

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Django Shell - Cloud SQL Produzione               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Cloud SQL Proxy is installed
PROXY_CMD=""
if command -v cloud-sql-proxy &> /dev/null; then
    PROXY_CMD="cloud-sql-proxy"
elif command -v cloud_sql_proxy &> /dev/null; then
    PROXY_CMD="cloud_sql_proxy"
elif [ -f "./cloud-sql-proxy" ]; then
    PROXY_CMD="./cloud-sql-proxy"
else
    echo -e "${YELLOW}⚠️  Cloud SQL Proxy non trovato. Download...${NC}"

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
        exit 1
    fi

    curl -o cloud-sql-proxy "$PROXY_URL"
    chmod +x cloud-sql-proxy
    PROXY_CMD="./cloud-sql-proxy"
    echo -e "${GREEN}✅ Cloud SQL Proxy scaricato${NC}"
fi

# Get DB password from Secret Manager
echo -e "${YELLOW}🔐 Recupero password database...${NC}"
DB_PASSWORD=$(gcloud secrets versions access latest --secret=db-password --project=${PROJECT} 2>/dev/null || echo "")

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  Password non trovata in Secret Manager${NC}"
    read -sp "DB Password: " DB_PASSWORD
    echo ""

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}❌ Password non fornita${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Password recuperata${NC}"

# Start Cloud SQL Proxy in background
echo ""
echo -e "${YELLOW}🚀 Avvio Cloud SQL Proxy...${NC}"
CONNECTION_NAME="${PROJECT}:${REGION}:${INSTANCE}"

# Kill existing proxy if running
lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true

# Start proxy in background
$PROXY_CMD "$CONNECTION_NAME" --port ${PROXY_PORT} > /tmp/cloud-sql-proxy.log 2>&1 &
PROXY_PID=$!

# Trap to kill proxy on exit
trap "echo -e '\n${YELLOW}🛑 Chiusura Cloud SQL Proxy...${NC}'; kill $PROXY_PID 2>/dev/null; exit" INT TERM EXIT

echo -e "${GREEN}✅ Cloud SQL Proxy avviato (PID: $PROXY_PID)${NC}"
sleep 2

# Export database connection variables
export DB_HOST="127.0.0.1"
export DB_PORT="${PROXY_PORT}"
export DB_NAME="${DB_NAME}"
export DB_USER="${DB_USER}"
export DB_PASSWORD="${DB_PASSWORD}"
export DEBUG="False"
export GOOGLE_CLOUD_PROJECT="${PROJECT}"

cd backend_django

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              CONNESSO AL DATABASE PRODUZIONE              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse command argument
COMMAND="${1:-shell}"

if [ "$COMMAND" = "shell" ]; then
    echo -e "${GREEN}🐍 Avvio Django shell interattiva...${NC}"
    echo -e "${YELLOW}   (Sei connesso al DB di PRODUZIONE! Fai attenzione!)${NC}"
    echo ""
    python3 manage.py shell --settings=config.settings
elif [ "$COMMAND" = "dbshell" ]; then
    echo -e "${GREEN}🗄️  Avvio PostgreSQL shell...${NC}"
    echo -e "${YELLOW}   (Sei connesso al DB di PRODUZIONE! Fai attenzione!)${NC}"
    echo ""
    python3 manage.py dbshell --settings=config.settings
else
    echo -e "${GREEN}⚙️  Esecuzione comando: ${COMMAND}${NC}"
    echo ""
    python3 manage.py $COMMAND --settings=config.settings
fi

# Cleanup
cd ..
kill $PROXY_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Sessione terminata${NC}"
