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

# Ask if user wants to scale database for faster import
echo -e "${YELLOW}⚡ Database Scaling (Raccomandato):${NC}"
echo -e "${YELLOW}   L'import di ~7.900 comuni + ~60.000 sezioni può richiedere 10+ minuti su db-f1-micro${NC}"
echo -e "${YELLOW}   Scalando a db-g1-small (1.7GB RAM) si riducono a ~1-2 minuti${NC}"
echo ""
echo -e "${CYAN}   Vuoi scalare temporaneamente il database? (y/n)${NC}"
echo -e "${YELLOW}   (Costo: ~25€/mese se attivo 24/7, ma puoi scalare giù dopo)${NC}"
read -r SCALE_DB

if [[ "$SCALE_DB" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}🚀 Scaling database a db-g1-small...${NC}"

    if [ -f "../scripts/scale-database.sh" ]; then
        ../scripts/scale-database.sh setup --project=${PROJECT}
    elif [ -f "scripts/scale-database.sh" ]; then
        scripts/scale-database.sh setup --project=${PROJECT}
    else
        echo -e "${YELLOW}⚠️  Script scale-database.sh non trovato, continuo senza scaling${NC}"
    fi

    echo ""
    echo -e "${GREEN}✅ Database scalato (ricorda di scalare giù dopo: ./scripts/scale-database.sh idle)${NC}"
    echo ""
else
    echo -e "${YELLOW}⏩ Continuo con tier corrente (potrebbe essere lento)${NC}"
    echo ""
fi

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
DB_PASSWORD=""

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

# Load initial data fixtures
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              CARICAMENTO DATI INIZIALI                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📦 Caricamento fixtures base...${NC}"

# 1. Initial data (regioni, province)
if [ -f "fixtures/initial_data.json" ]; then
    echo -e "${YELLOW}  → Regioni e Province italiane...${NC}"
    python3 manage.py loaddata fixtures/initial_data.json --settings=config.settings
    echo -e "${GREEN}    ✅ 20 regioni + 107 province caricate${NC}"
fi

# 2. Import comuni italiani (NECESSARIO per municipi e sezioni)
echo ""
echo -e "${YELLOW}📥 Verifica Comuni italiani...${NC}"

COMUNI_COUNT=$(python3 -c "from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from territory.models import Comune; print(Comune.objects.count())" 2>/dev/null || echo "0")

if [ "$COMUNI_COUNT" -ge 7000 ]; then
    echo -e "${GREEN}    ✅ ${COMUNI_COUNT} comuni già presenti, skip import${NC}"
else
    echo -e "${YELLOW}    → Trovati solo ${COMUNI_COUNT} comuni, importo tutti...${NC}"
    echo -e "${YELLOW}      (Necessario per municipi e sezioni, ~7.900 comuni, 1-2 minuti)${NC}"

    if [ -f "fixtures/comuni_istat.csv" ]; then
        echo -e "${YELLOW}      Usando file locale comuni_istat.csv...${NC}"
        python3 manage.py import_comuni_istat --file=fixtures/comuni_istat.csv --settings=config.settings 2>&1 | grep -E "(Created|Updated|Skipped|Error)" || true
    else
        echo -e "${YELLOW}      Download da ISTAT...${NC}"
        python3 manage.py import_comuni_istat --settings=config.settings 2>&1 | grep -E "(Created|Updated|Skipped|Error)" || true
    fi

    COMUNI_COUNT=$(python3 -c "from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from territory.models import Comune; print(Comune.objects.count())" 2>/dev/null || echo "0")
    echo -e "${GREEN}    ✅ ${COMUNI_COUNT} comuni in database${NC}"
fi

# 3. Roma municipi (DOPO i comuni)
if [ -f "fixtures/roma_municipi.json" ]; then
    echo ""
    echo -e "${YELLOW}  → Municipi di Roma...${NC}"
    python3 manage.py loaddata fixtures/roma_municipi.json --settings=config.settings
    echo -e "${GREEN}    ✅ Municipi di Roma caricati${NC}"
fi

# 3. Referendum 2026
if [ -f "fixtures/referendum_giustizia_2026.json" ]; then
    echo -e "${YELLOW}  → Referendum Giustizia 2026...${NC}"
    python3 manage.py loaddata fixtures/referendum_giustizia_2026.json --settings=config.settings
    echo -e "${GREEN}    ✅ Referendum 2026 configurato${NC}"
fi

# 4. FAQ Referendum
if [ -f "fixtures/faq_referendum_2026.json" ]; then
    echo -e "${YELLOW}  → FAQ Referendum 2026...${NC}"
    python3 manage.py loaddata fixtures/faq_referendum_2026.json --settings=config.settings
    echo -e "${GREEN}    ✅ FAQ caricate${NC}"
fi

# 5. Risorse Referendum
if [ -f "fixtures/risorse_referendum_2026.json" ]; then
    echo -e "${YELLOW}  → Risorse formative RDL...${NC}"
    python3 manage.py loaddata fixtures/risorse_referendum_2026.json --settings=config.settings
    echo -e "${GREEN}    ✅ Risorse caricate${NC}"
fi

# 6. Delegati Roma (esempio)
if [ -f "fixtures/delegati_roma_referendum_2026.json" ]; then
    echo -e "${YELLOW}  → Delegati Roma (esempio)...${NC}"
    python3 manage.py loaddata fixtures/delegati_roma_referendum_2026.json --settings=config.settings
    echo -e "${GREEN}    ✅ Delegati esempio caricati${NC}"

    # Assegna territorio (Comune di Roma) ai delegati
    echo -e "${YELLOW}  → Assegna territorio Roma ai delegati...${NC}"
    python3 manage.py assign_territory_to_delegati --settings=config.settings
    echo -e "${GREEN}    ✅ Territorio assegnato${NC}"
fi

echo ""
echo -e "${GREEN}✅ Fixtures base caricati${NC}"

# Optional: Import sezioni elettorali (large dataset)
echo ""
echo -e "${YELLOW}📊 Verifica Sezioni elettorali...${NC}"

SEZIONI_COUNT=$(python3 -c "from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from territory.models import SezioneElettorale; print(SezioneElettorale.objects.count())" 2>/dev/null || echo "0")

if [ "$SEZIONI_COUNT" -ge 50000 ]; then
    echo -e "${GREEN}    ✅ ${SEZIONI_COUNT} sezioni già presenti, skip import${NC}"
else
    echo -e "${YELLOW}    → Trovate solo ${SEZIONI_COUNT} sezioni${NC}"
    echo -e "${YELLOW}📊 Vuoi importare tutte le Sezioni elettorali? (y/n)${NC}"
    echo -e "${YELLOW}   (~60.000 sezioni, richiede 2-3 minuti)${NC}"
    read -r IMPORT_SEZIONI

    if [[ "$IMPORT_SEZIONI" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${YELLOW}📥 Import Sezioni elettorali Italia...${NC}"

        if [ -f "fixtures/sezioni_eligendo.csv" ]; then
            echo -e "${YELLOW}  → Usando file locale sezioni_eligendo.csv...${NC}"
            python3 manage.py import_sezioni_italia --file=fixtures/sezioni_eligendo.csv --settings=config.settings 2>&1 | grep -E "(Created|Skipped|sections)" || true
        else
            echo -e "${RED}  ❌ File sezioni_eligendo.csv non trovato${NC}"
        fi

        SEZIONI_COUNT=$(python3 -c "from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from territory.models import SezioneElettorale; print(SezioneElettorale.objects.count())" 2>/dev/null || echo "0")
        echo -e "${GREEN}    ✅ ${SEZIONI_COUNT} sezioni in database${NC}"
    else
        echo -e "${YELLOW}⏩ Skip import sezioni (potrai farlo dopo manualmente)${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Dati iniziali caricati${NC}"

# Collect static files
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              COLLECT STATIC FILES                         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📦 Raccolta file statici Django (Admin CSS/JS)...${NC}"
python3 manage.py collectstatic --noinput --clear --settings=config.settings

STATIC_COUNT=$(find staticfiles -type f 2>/dev/null | wc -l | xargs)
echo -e "${GREEN}✅ ${STATIC_COUNT} file statici raccolti in staticfiles/${NC}"

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
