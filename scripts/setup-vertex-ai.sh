#!/bin/bash

# ============================================================================
# Setup Vertex AI for AInaudi - Automated Script
# ============================================================================
# Questo script automatizza:
# 1. Creazione service account Google Cloud
# 2. Assegnazione ruoli (Vertex AI User + Service Agent)
# 3. Download credenziali JSON
# 4. Abilitazione API necessarie
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-ainaudi-prod}"
SERVICE_ACCOUNT_NAME="ainaudi-vertex-ai"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SECRETS_DIR="secrets"
KEY_FILE="${SECRETS_DIR}/gcp-credentials.json"

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}  Vertex AI Setup - AInaudi${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Errore: gcloud CLI non installato${NC}"
    echo ""
    echo "Installa Google Cloud SDK:"
    echo "  macOS:   brew install --cask google-cloud-sdk"
    echo "  Linux:   curl https://sdk.cloud.google.com | bash"
    echo "  Windows: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✓${NC} gcloud CLI trovato"

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q @; then
    echo -e "${YELLOW}⚠${NC}  Non sei autenticato su Google Cloud"
    echo ""
    echo "Esegui: gcloud auth login"
    exit 1
fi

CURRENT_USER=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo -e "${GREEN}✓${NC} Autenticato come: ${CURRENT_USER}"

# Set project
echo ""
echo -e "${BLUE}Progetto:${NC} ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID} 2>/dev/null || {
    echo -e "${RED}❌ Progetto '${PROJECT_ID}' non trovato o non accessibile${NC}"
    echo ""
    echo "Progetti disponibili:"
    gcloud projects list --format="table(projectId,name)"
    echo ""
    echo "Usage: $0 [PROJECT_ID]"
    echo "Esempio: $0 ainaudi-prod"
    exit 1
}

echo -e "${GREEN}✓${NC} Progetto impostato"

# Enable required APIs
echo ""
echo -e "${BLUE}📡 Abilitazione API...${NC}"

APIS=(
    "aiplatform.googleapis.com"           # Vertex AI
    "cloudresourcemanager.googleapis.com" # Resource Manager
)

for api in "${APIS[@]}"; do
    echo -n "  - ${api}... "
    if gcloud services list --enabled --filter="name:${api}" --format="value(name)" | grep -q "${api}"; then
        echo -e "${GREEN}già abilitata${NC}"
    else
        gcloud services enable ${api} --quiet
        echo -e "${GREEN}✓ abilitata${NC}"
    fi
done

# Check if service account exists
echo ""
echo -e "${BLUE}👤 Service Account: ${SERVICE_ACCOUNT_NAME}${NC}"

if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  Service account già esistente"
    echo ""
    read -p "Vuoi creare comunque una nuova chiave? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    echo "Creazione service account..."
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="AInaudi Vertex AI Service Account" \
        --description="Service account per Vertex AI (Gemini + Embeddings)" \
        --quiet

    echo -e "${GREEN}✓${NC} Service account creato: ${SERVICE_ACCOUNT_EMAIL}"
fi

# Assign roles
echo ""
echo -e "${BLUE}🔐 Assegnazione ruoli...${NC}"

ROLES=(
    "roles/aiplatform.user"
    "roles/aiplatform.serviceAgent"
)

for role in "${ROLES[@]}"; do
    echo -n "  - ${role}... "

    # Check if role already assigned
    if gcloud projects get-iam-policy ${PROJECT_ID} \
        --flatten="bindings[].members" \
        --filter="bindings.role:${role}" \
        --format="value(bindings.members)" | grep -q "serviceAccount:${SERVICE_ACCOUNT_EMAIL}"; then
        echo -e "${GREEN}già assegnato${NC}"
    else
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="${role}" \
            --quiet > /dev/null
        echo -e "${GREEN}✓ assegnato${NC}"
    fi
done

# Create and download key
echo ""
echo -e "${BLUE}🔑 Creazione chiave JSON...${NC}"

# Create secrets directory if it doesn't exist
mkdir -p "${SECRETS_DIR}"

# Check if key file already exists
if [ -f "${KEY_FILE}" ]; then
    echo -e "${YELLOW}⚠${NC}  File ${KEY_FILE} già esistente"
    echo ""
    read -p "Vuoi sovrascriverlo? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operazione annullata"
        exit 0
    fi
    rm -f ${KEY_FILE}
fi

gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SERVICE_ACCOUNT_EMAIL} \
    --quiet

echo -e "${GREEN}✓${NC} Chiave creata: ${KEY_FILE}"

# Create .env.docker if it doesn't exist
if [ ! -f ".env.docker" ]; then
    echo ""
    echo -e "${BLUE}📝 Creazione .env.docker...${NC}"
    cp .env.docker.example .env.docker
    echo -e "${GREEN}✓${NC} File .env.docker creato"
fi

# Summary
echo ""
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  ✅ Setup completato!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo -e "${BLUE}Configurazione:${NC}"
echo "  Project:         ${PROJECT_ID}"
echo "  Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "  Credenziali:     ${KEY_FILE}"
echo ""
echo -e "${BLUE}Prossimi step:${NC}"
echo "  1. Verifica le variabili in .env.docker"
echo "  2. Avvia Docker: docker-compose up -d"
echo "  3. Testa Vertex AI: docker-compose exec backend python manage.py shell"
echo ""
echo -e "${BLUE}Test rapido:${NC}"
cat <<'EOF'
  from ai_assistant.vertex_service import vertex_ai_service
  emb = vertex_ai_service.generate_embedding("test")
  print(f"✅ Embedding: {len(emb)} dimensioni")
EOF
echo ""
echo -e "${YELLOW}⚠${NC}  IMPORTANTE: NON committare ${KEY_FILE} su Git!"
echo ""
