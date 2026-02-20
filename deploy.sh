#!/bin/bash
# Deploy script per Google App Engine con promozione automatica
# Usage: ./deploy.sh [--no-promote] [--project PROJECT_ID]

set -e  # Exit on error

# Default values
PROMOTE="--promote"
PROJECT="ainaudi-prod"
SKIP_BUILD=false
SKIP_FRONTEND=false
SKIP_BACKEND=false
SKIP_PDF=false
SKIP_AI=false
SKIP_ADMIN=false
SKIP_RDL=false
SKIP_DISPATCH=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-promote)
      PROMOTE="--no-promote"
      shift
      ;;
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --frontend-only)
      SKIP_BACKEND=true
      SKIP_PDF=true
      SKIP_AI=true
      SKIP_ADMIN=true
      SKIP_RDL=true
      SKIP_DISPATCH=true
      shift
      ;;
    --backend-only)
      SKIP_FRONTEND=true
      SKIP_PDF=true
      SKIP_AI=true
      SKIP_ADMIN=true
      SKIP_RDL=true
      SKIP_DISPATCH=true
      shift
      ;;
    --pdf-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_AI=true
      SKIP_ADMIN=true
      SKIP_RDL=true
      SKIP_DISPATCH=true
      shift
      ;;
    --ai-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_PDF=true
      SKIP_ADMIN=true
      SKIP_RDL=true
      SKIP_DISPATCH=true
      shift
      ;;
    --admin-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_PDF=true
      SKIP_AI=true
      SKIP_RDL=true
      SKIP_DISPATCH=true
      shift
      ;;
    --rdl-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_PDF=true
      SKIP_AI=true
      SKIP_ADMIN=true
      SKIP_DISPATCH=true
      shift
      ;;
    --dispatch-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_PDF=true
      SKIP_AI=true
      SKIP_ADMIN=true
      SKIP_RDL=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --no-promote        Deploy senza promuovere la versione (default: con promote)"
      echo "  --project PROJECT   Specifica il project ID GCP (default: ainaudi-prod)"
      echo "  --skip-build        Salta la build del frontend (usa build esistente)"
      echo "  --frontend-only     Deploya solo il frontend React"
      echo "  --backend-only      Deploya solo il backend Django (api)"
      echo "  --pdf-only          Deploya solo il servizio PDF"
      echo "  --ai-only           Deploya solo il servizio AI assistant"
      echo "  --admin-only        Deploya solo il servizio Admin Django"
      echo "  --rdl-only          Deploya solo il servizio RDL (scrutinio + risorse)"
      echo "  --dispatch-only     Aggiorna solo dispatch.yaml"
      echo "  --help, -h          Mostra questo messaggio"
      echo ""
      echo "Esempi:"
      echo "  $0                                    # Deploy completo con promote"
      echo "  $0 --no-promote                       # Deploy senza promote (test)"
      echo "  $0 --frontend-only                    # Solo frontend"
      echo "  $0 --backend-only --no-promote        # Solo backend, no promote"
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
echo -e "${BLUE}║         Deploy AInaudi su Google App Engine              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📋 Configurazione:${NC}"
echo -e "   Project ID: ${GREEN}${PROJECT}${NC}"
echo -e "   Promote: ${GREEN}${PROMOTE}${NC}"
echo -e "   Skip Frontend: ${SKIP_FRONTEND}"
echo -e "   Skip Backend: ${SKIP_BACKEND}"
echo -e "   Skip PDF Service: ${SKIP_PDF}"
echo -e "   Skip AI Service: ${SKIP_AI}"
echo -e "   Skip Admin Service: ${SKIP_ADMIN}"
echo -e "   Skip RDL Service: ${SKIP_RDL}"
echo -e "   Skip Dispatch: ${SKIP_DISPATCH}"
echo ""

# Verify gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI non trovato. Installalo da: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}🔧 Configurazione progetto GCP...${NC}"
gcloud config set project ${PROJECT}

# Deploy Frontend (React)
if [ "$SKIP_FRONTEND" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                  1. FRONTEND REACT                        ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    if [ "$SKIP_BUILD" = false ]; then
        echo -e "${YELLOW}📦 Build frontend React...${NC}"
        npm install
        npm run build
        echo -e "${GREEN}✅ Build frontend completata${NC}"
    else
        echo -e "${YELLOW}⏩ Skip build frontend (usando build esistente)${NC}"
        if [ ! -d "build" ]; then
            echo -e "${RED}❌ Directory build/ non trovata. Rimuovi --skip-build${NC}"
            exit 1
        fi
    fi

    # Collect Django admin/DRF static files into frontend build
    echo -e "${YELLOW}📦 Collect static Django (admin, rest_framework)...${NC}"
    (cd backend_django && python3 manage.py collectstatic --noinput --clear)
    mkdir -p build/static
    cp -r backend_django/staticfiles/admin build/static/admin
    cp -r backend_django/staticfiles/rest_framework build/static/rest_framework
    echo -e "${GREEN}✅ Static Django copiati in build/static/${NC}"

    echo -e "${YELLOW}🚀 Deploy frontend su App Engine (service: default)...${NC}"
    gcloud app deploy app.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    echo -e "${GREEN}✅ Frontend deployato con successo${NC}"
fi

# Deploy Backend (Django)
if [ "$SKIP_BACKEND" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                  2. BACKEND DJANGO                        ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    cd backend_django

    echo -e "${YELLOW}📦 Collect static files Django...${NC}"
    python3 manage.py collectstatic --noinput --clear
    echo -e "${GREEN}✅ Static files collected${NC}"

    # Migrazioni su Cloud SQL via proxy
    echo -e "${YELLOW}🗄️  Migrazioni database Cloud SQL...${NC}"

    REGION="europe-west1"
    INSTANCE="ainaudi-db"
    DB_NAME_PROD="ainaudi_db"
    DB_USER_PROD="postgres"
    PROXY_PORT=5433
    CONNECTION_NAME="${PROJECT}:${REGION}:${INSTANCE}"

    # Trova o scarica Cloud SQL Proxy
    PROXY_CMD=""
    if command -v cloud-sql-proxy &> /dev/null; then
        PROXY_CMD="cloud-sql-proxy"
    elif command -v cloud_sql_proxy &> /dev/null; then
        PROXY_CMD="cloud_sql_proxy"
    elif [ -f "../cloud-sql-proxy" ]; then
        PROXY_CMD="../cloud-sql-proxy"
    else
        echo -e "${RED}❌ Cloud SQL Proxy non trovato. Installalo o usa scripts/django-shell-production.sh migrate${NC}"
        echo -e "${YELLOW}⏩ Salto migrazioni (eseguile manualmente prima del deploy)${NC}"
        PROXY_CMD=""
    fi

    if [ -n "$PROXY_CMD" ]; then
        # Password da Secret Manager
        DB_PASSWORD_PROD=$(timeout 5 gcloud secrets versions access latest --secret=db-password --project=${PROJECT} 2>/dev/null || echo "")
        if [ -z "$DB_PASSWORD_PROD" ]; then
            echo -e "${YELLOW}⚠️  Password non trovata in Secret Manager${NC}"
            read -sp "DB Password: " DB_PASSWORD_PROD
            echo ""
        fi

        # Avvia proxy
        lsof -ti:${PROXY_PORT} | xargs kill -9 2>/dev/null || true
        $PROXY_CMD "$CONNECTION_NAME" --port ${PROXY_PORT} > /tmp/cloud-sql-proxy-deploy.log 2>&1 &
        PROXY_PID=$!
        sleep 2

        # Migrate via proxy
        DB_HOST="127.0.0.1" DB_PORT="${PROXY_PORT}" DB_NAME="${DB_NAME_PROD}" \
        DB_USER="${DB_USER_PROD}" DB_PASSWORD="${DB_PASSWORD_PROD}" \
        python3 manage.py migrate --noinput

        # Chiudi proxy
        kill $PROXY_PID 2>/dev/null || true
        wait $PROXY_PID 2>/dev/null || true

        echo -e "${GREEN}✅ Migrazioni completate su Cloud SQL${NC}"
    fi

    echo -e "${YELLOW}🚀 Deploy backend su App Engine (service: api)...${NC}"
    gcloud app deploy app.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    cd ..
    echo -e "${GREEN}✅ Backend deployato con successo${NC}"
fi

# Deploy PDF Service (Django - heavy PDF generation)
if [ "$SKIP_PDF" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              3. PDF SERVICE (1GB RAM)                     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    cd backend_django

    echo -e "${YELLOW}🚀 Deploy PDF service su App Engine (service: pdf)...${NC}"
    gcloud app deploy app-pdf.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    cd ..
    echo -e "${GREEN}✅ PDF service deployato con successo${NC}"
fi

# Deploy AI Service (Django - AI assistant with Vertex AI)
if [ "$SKIP_AI" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              4. AI SERVICE (Vertex AI + pgvector)         ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    cd backend_django

    echo -e "${YELLOW}🚀 Deploy AI service su App Engine (service: ai)...${NC}"
    gcloud app deploy app_ai.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    cd ..
    echo -e "${GREEN}✅ AI service deployato con successo${NC}"
fi

# Deploy Admin Service (Django - full admin interface)
if [ "$SKIP_ADMIN" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              5. ADMIN SERVICE (Django Admin)              ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    cd backend_django

    echo -e "${YELLOW}📦 Collect static files Django (admin CSS/JS)...${NC}"
    python3 manage.py collectstatic --noinput --clear
    echo -e "${GREEN}✅ Static files collected${NC}"

    echo -e "${YELLOW}🚀 Deploy Admin service su App Engine (service: admin)...${NC}"
    gcloud app deploy app_admin.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    cd ..
    echo -e "${GREEN}✅ Admin service deployato con successo${NC}"
fi

# Deploy RDL Service (Django - scrutinio + risorse, high traffic)
if [ "$SKIP_RDL" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              6. RDL SERVICE (scrutinio + risorse)         ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    cd backend_django

    echo -e "${YELLOW}🚀 Deploy RDL service su App Engine (service: rdl)...${NC}"
    gcloud app deploy app_rdl.yaml \
        --project=${PROJECT} \
        ${PROMOTE} \
        --quiet

    cd ..
    echo -e "${GREEN}✅ RDL service deployato con successo${NC}"
fi

# Deploy Dispatch Rules
if [ "$SKIP_DISPATCH" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              7. DISPATCH ROUTING RULES                    ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

    echo -e "${YELLOW}🔀 Deploy dispatch.yaml (routing rules)...${NC}"
    gcloud app deploy dispatch.yaml \
        --project=${PROJECT} \
        --quiet

    echo -e "${GREEN}✅ Dispatch rules deployate${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ DEPLOY COMPLETATO CON SUCCESSO            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get deployed versions
echo -e "${YELLOW}📊 Versioni deployate:${NC}"
gcloud app versions list --project=${PROJECT} --service=default --sort-by=~version.createTime --limit=3
gcloud app versions list --project=${PROJECT} --service=api --sort-by=~version.createTime --limit=3
gcloud app versions list --project=${PROJECT} --service=ai --sort-by=~version.createTime --limit=3 2>/dev/null || true
gcloud app versions list --project=${PROJECT} --service=admin --sort-by=~version.createTime --limit=3 2>/dev/null || true
gcloud app versions list --project=${PROJECT} --service=rdl --sort-by=~version.createTime --limit=3 2>/dev/null || true

echo ""
echo -e "${BLUE}🌐 URL Applicazione:${NC}"
DEFAULT_URL="https://${PROJECT}.appspot.com"
API_URL="https://api-dot-${PROJECT}.appspot.com"
echo -e "   Frontend: ${GREEN}${DEFAULT_URL}${NC}"
echo -e "   Backend:  ${GREEN}${API_URL}${NC}"
echo -e "   Admin:    ${GREEN}${DEFAULT_URL}/admin/${NC}"

echo ""
echo -e "${YELLOW}💡 Comandi utili:${NC}"
echo -e "   Logs frontend:     gcloud app logs tail --service=default"
echo -e "   Logs backend:      gcloud app logs tail --service=api"
echo -e "   Logs AI:           gcloud app logs tail --service=ai"
echo -e "   Logs Admin:        gcloud app logs tail --service=admin"
echo -e "   Logs RDL:          gcloud app logs tail --service=rdl"
echo -e "   Browse app:        gcloud app browse"
echo -e "   Lista versioni:    gcloud app versions list"
echo -e "   Traffico servizi:  gcloud app services list"
echo ""

if [ "$PROMOTE" = "--no-promote" ]; then
    echo -e "${YELLOW}⚠️  Deploy effettuato senza promozione${NC}"
    echo -e "${YELLOW}   Per promuovere manualmente:${NC}"
    echo ""
    echo -e "   ${BLUE}# Lista versioni${NC}"
    echo -e "   gcloud app versions list --project=${PROJECT}"
    echo ""
    echo -e "   ${BLUE}# Promuovi versione specifica${NC}"
    echo -e "   gcloud app services set-traffic default --splits=<VERSION_ID>=1"
    echo -e "   gcloud app services set-traffic api --splits=<VERSION_ID>=1"
    echo ""
fi

echo -e "${GREEN}🎉 Deploy completato!${NC}"
