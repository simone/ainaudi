#!/bin/bash
# Deploy di emergenza: usa servizi con nomi nuovi (fe, api2)
# per bypassare le operazioni PENDING bloccate su default e api.
# Gli altri servizi (pdf, ai, admin, rdl) non hanno pending e
# vengono deployati normalmente.
#
# Dopo che le pending si sbloccano, tornare ai nomi originali con:
#   ./deploy.sh
#   gcloud app services delete fe api2 --project=ainaudi-prod --quiet

set -e

PROJECT="ainaudi-prod"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Deploy EMERGENZA (nuovi servizi fe + api2)          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

gcloud config set project ${PROJECT}

# ═══════════════════════════════════════════════════════════
# 1. BUILD FRONTEND
# ═══════════════════════════════════════════════════════════
echo -e "${BLUE}═══ 1/7. BUILD FRONTEND ═══${NC}"
npm install
npm run build

# Collect Django static into build
(cd backend_django && python3 manage.py collectstatic --noinput --clear 2>/dev/null)
mkdir -p build/static
cp -r backend_django/staticfiles/admin build/static/admin 2>/dev/null || true
cp -r backend_django/staticfiles/rest_framework build/static/rest_framework 2>/dev/null || true
echo -e "${GREEN}Build completata${NC}"

# ═══════════════════════════════════════════════════════════
# 2. MIGRAZIONI DATABASE
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══ 2/7. MIGRAZIONI DATABASE ═══${NC}"

REGION="europe-west1"
INSTANCE="ainaudi-db"
DB_NAME_PROD="ainaudi_db"
DB_USER_PROD="postgres"
PROXY_PORT=5433
CONNECTION_NAME="${PROJECT}:${REGION}:${INSTANCE}"

PROXY_CMD=""
if command -v cloud-sql-proxy &> /dev/null; then
    PROXY_CMD="cloud-sql-proxy"
elif command -v cloud_sql_proxy &> /dev/null; then
    PROXY_CMD="cloud_sql_proxy"
elif [ -f "./cloud-sql-proxy" ]; then
    PROXY_CMD="./cloud-sql-proxy"
fi

if [ -n "$PROXY_CMD" ]; then
    DB_PASSWORD_PROD=$(gcloud secrets versions access latest --secret=db-password --project=${PROJECT} 2>/dev/null || echo "")
    if [ -z "$DB_PASSWORD_PROD" ]; then
        echo -e "${YELLOW}Password non trovata in Secret Manager${NC}"
        read -sp "DB Password: " DB_PASSWORD_PROD
        echo ""
    fi

    lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true
    $PROXY_CMD "$CONNECTION_NAME" --port ${PROXY_PORT} > /tmp/cloud-sql-proxy-deploy.log 2>&1 &
    PROXY_PID=$!
    sleep 2

    cd backend_django
    DB_HOST="127.0.0.1" DB_PORT="${PROXY_PORT}" DB_NAME="${DB_NAME_PROD}" \
    DB_USER="${DB_USER_PROD}" DB_PASSWORD="${DB_PASSWORD_PROD}" \
    python3 manage.py migrate --noinput
    cd ..

    kill $PROXY_PID 2>/dev/null || true
    wait $PROXY_PID 2>/dev/null || true
    echo -e "${GREEN}Migrazioni completate${NC}"
else
    echo -e "${YELLOW}Cloud SQL Proxy non trovato, salto migrazioni${NC}"
fi

# ═══════════════════════════════════════════════════════════
# 3. DEPLOY FRONTEND (service: fe) - NUOVO, bypassa pending su default
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══ 3/7. DEPLOY FRONTEND (service: fe) ═══${NC}"
gcloud app deploy app-fe.yaml --project=${PROJECT} --promote --quiet
echo -e "${GREEN}Frontend (fe) deployato${NC}"

# ═══════════════════════════════════════════════════════════
# 4. DEPLOY BACKEND (service: api2) - NUOVO, bypassa pending su api
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══ 4/7. DEPLOY BACKEND (service: api2) ═══${NC}"
cd backend_django
gcloud app deploy app-api2.yaml --project=${PROJECT} --promote --quiet
cd ..
echo -e "${GREEN}Backend (api2) deployato${NC}"

# ═══════════════════════════════════════════════════════════
# 5. DEPLOY PDF + ADMIN + RDL + AI (nomi originali, nessuna pending)
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══ 5/7. DEPLOY PDF SERVICE ═══${NC}"
cd backend_django
gcloud app deploy app-pdf.yaml --project=${PROJECT} --promote --quiet
echo -e "${GREEN}PDF service deployato${NC}"

echo ""
echo -e "${BLUE}═══ 5/7. DEPLOY ADMIN SERVICE ═══${NC}"
gcloud app deploy app_admin.yaml --project=${PROJECT} --promote --quiet
echo -e "${GREEN}Admin service deployato${NC}"

echo ""
echo -e "${BLUE}═══ 5/7. DEPLOY RDL SERVICE ═══${NC}"
gcloud app deploy app_rdl.yaml --project=${PROJECT} --promote --quiet
echo -e "${GREEN}RDL service deployato${NC}"

echo ""
echo -e "${BLUE}═══ 5/7. DEPLOY AI SERVICE ═══${NC}"
gcloud app deploy app_ai.yaml --project=${PROJECT} --promote --quiet
cd ..
echo -e "${GREEN}AI service deployato${NC}"

# ═══════════════════════════════════════════════════════════
# 6. DEPLOY DISPATCH (routing verso fe + api2)
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══ 6/7. DEPLOY DISPATCH ═══${NC}"
gcloud app deploy dispatch-fix.yaml --project=${PROJECT} --quiet
echo -e "${GREEN}Dispatch aggiornato (api -> api2, default -> fe)${NC}"

# ═══════════════════════════════════════════════════════════
# 7. RIEPILOGO
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DEPLOY COMPLETATO                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
gcloud app versions list --project=${PROJECT}
echo ""
echo -e "${YELLOW}Per tornare ai nomi originali (quando le pending scadono):${NC}"
echo -e "  1. ./deploy.sh"
echo -e "  2. gcloud app deploy dispatch.yaml --project=${PROJECT} --quiet"
echo -e "  3. gcloud app services delete fe api2 --project=${PROJECT} --quiet"
