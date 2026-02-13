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
      SKIP_DISPATCH=true
      shift
      ;;
    --backend-only)
      SKIP_FRONTEND=true
      SKIP_PDF=true
      SKIP_DISPATCH=true
      shift
      ;;
    --pdf-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_DISPATCH=true
      shift
      ;;
    --dispatch-only)
      SKIP_FRONTEND=true
      SKIP_BACKEND=true
      SKIP_PDF=true
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

    echo -e "${YELLOW}🗄️  Esecuzione migrazioni database...${NC}"
    python3 manage.py migrate --noinput
    echo -e "${GREEN}✅ Migrazioni completate${NC}"

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

# Deploy Dispatch Rules
if [ "$SKIP_DISPATCH" = false ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              3. DISPATCH ROUTING RULES                    ║${NC}"
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
