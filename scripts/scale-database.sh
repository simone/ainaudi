#!/bin/bash
# Script per scalare il tier Cloud SQL in base alle necessità
# Usage: ./scripts/scale-database.sh [idle|setup|scrutinio]

set -e  # Exit on error

# Default values
PROJECT="ainaudi-prod"
INSTANCE="ainaudi-db"
REGION="europe-west1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to get tier specs (Bash 3.x compatible)
# Returns: "tier|RAM|vCPU|Cost/month|Description"
get_tier_specs() {
    local preset=$1
    case $preset in
        idle)
            echo "db-f1-micro|0.6GB|Shared|~7€|Minimo costo, solo idle/sviluppo"
            ;;
        setup)
            echo "db-g1-small|1.7GB|1 vCPU|~25€|Setup iniziale, import dati"
            ;;
        scrutinio)
            echo "db-n1-standard-1|3.75GB|1 vCPU|~50€|Scrutinio attivo, alta concorrenza"
            ;;
        high)
            echo "db-n1-standard-2|7.5GB|2 vCPU|~100€|Picco massimo (scrutinio + dashboard)"
            ;;
        *)
            echo ""
            ;;
    esac
}

show_usage() {
    echo "Usage: $0 [PRESET] [OPTIONS]"
    echo ""
    echo "Presets:"
    echo "  idle        Scala a db-f1-micro (minimo costo, ~7€/mese)"
    echo "  setup       Scala a db-g1-small (import dati, ~25€/mese)"
    echo "  scrutinio   Scala a db-n1-standard-1 (scrutinio attivo, ~50€/mese)"
    echo "  high        Scala a db-n1-standard-2 (picco massimo, ~100€/mese)"
    echo ""
    echo "Options:"
    echo "  --tier TIER     Specifica tier manualmente (es: db-n1-standard-4)"
    echo "  --project ID    Project ID GCP (default: ainaudi-prod)"
    echo "  --instance NAME Instance name (default: ainaudi-db)"
    echo "  --status        Mostra tier corrente e esci"
    echo "  --help, -h      Mostra questo messaggio"
    echo ""
    echo "Esempi:"
    echo "  $0 setup                    # Scala a db-g1-small per import dati"
    echo "  $0 scrutinio                # Scala a db-n1-standard-1 per scrutinio"
    echo "  $0 idle                     # Torna a db-f1-micro dopo scrutinio"
    echo "  $0 --status                 # Mostra tier corrente"
    echo "  $0 --tier db-n1-standard-4  # Scala a tier custom"
}

show_status() {
    echo -e "${BLUE}📊 Stato corrente database${NC}"
    echo ""

    CURRENT_TIER=$(gcloud sql instances describe ${INSTANCE} \
        --project=${PROJECT} \
        --format="value(settings.tier)")

    CURRENT_STATE=$(gcloud sql instances describe ${INSTANCE} \
        --project=${PROJECT} \
        --format="value(state)")

    echo -e "   Instance: ${GREEN}${INSTANCE}${NC}"
    echo -e "   Project:  ${GREEN}${PROJECT}${NC}"
    echo -e "   Tier:     ${CYAN}${CURRENT_TIER}${NC}"
    echo -e "   State:    ${GREEN}${CURRENT_STATE}${NC}"
    echo ""
}

show_tier_comparison() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              CLOUD SQL TIER COMPARISON (PostgreSQL)                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    printf "%-20s %-10s %-12s %-15s %s\n" "TIER" "RAM" "vCPU" "COSTO/MESE" "USO RACCOMANDATO"
    echo "────────────────────────────────────────────────────────────────────────────"
    printf "%-20s %-10s %-12s %-15s %s\n" "db-f1-micro" "0.6 GB" "Shared" "~7 EUR" "Idle/Sviluppo"
    printf "%-20s %-10s %-12s %-15s %s\n" "db-g1-small" "1.7 GB" "1 vCPU" "~25 EUR" "Setup/Import dati"
    printf "%-20s %-10s %-12s %-15s %s\n" "db-n1-standard-1" "3.75 GB" "1 vCPU" "~50 EUR" "Scrutinio attivo"
    printf "%-20s %-10s %-12s %-15s %s\n" "db-n1-standard-2" "7.5 GB" "2 vCPU" "~100 EUR" "Picco massimo"
    printf "%-20s %-10s %-12s %-15s %s\n" "db-n1-standard-4" "15 GB" "4 vCPU" "~200 EUR" "Stress test"
    echo ""
    echo -e "${YELLOW}💡 Tip: Scala su prima di operazioni pesanti, poi torna a idle${NC}"
    echo ""
}

scale_database() {
    local TARGET_TIER=$1

    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    SCALING CLOUD SQL DATABASE                         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Get current tier
    CURRENT_TIER=$(gcloud sql instances describe ${INSTANCE} \
        --project=${PROJECT} \
        --format="value(settings.tier)")

    if [ "$CURRENT_TIER" == "$TARGET_TIER" ]; then
        echo -e "${YELLOW}⚠️  Database già sul tier: ${TARGET_TIER}${NC}"
        echo ""
        show_status
        exit 0
    fi

    echo -e "${YELLOW}📋 Dettagli operazione:${NC}"
    echo -e "   Instance:    ${GREEN}${INSTANCE}${NC}"
    echo -e "   Project:     ${GREEN}${PROJECT}${NC}"
    echo -e "   Tier attuale: ${RED}${CURRENT_TIER}${NC}"
    echo -e "   Tier target:  ${GREEN}${TARGET_TIER}${NC}"
    echo ""

    # Show tier specs if available
    for preset in idle setup scrutinio high; do
        specs=$(get_tier_specs "$preset")
        if [ -n "$specs" ]; then
            IFS='|' read -r tier ram vcpu cost desc <<< "$specs"
            if [ "$tier" == "$TARGET_TIER" ]; then
                echo -e "${CYAN}Specifiche ${TARGET_TIER}:${NC}"
                echo -e "   RAM:      ${ram}"
                echo -e "   vCPU:     ${vcpu}"
                echo -e "   Costo:    ${cost}"
                echo -e "   Uso:      ${desc}"
                echo ""
            fi
        fi
    done

    echo -e "${YELLOW}⚠️  ATTENZIONE:${NC}"
    echo -e "   • Il database sarà ${RED}OFFLINE${NC} per ~1-3 minuti durante il resize"
    echo -e "   • Le connessioni attive saranno interrotte"
    echo -e "   • Il costo mensile cambierà"
    echo ""

    # Confirm
    read -p "$(echo -e ${YELLOW}Procedere con il resize? [y/N]: ${NC})" -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Operazione annullata${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}🔧 Scaling database in corso...${NC}"
    echo -e "${YELLOW}   (Questo richiederà 1-3 minuti)${NC}"
    echo ""

    # Perform scaling
    if gcloud sql instances patch ${INSTANCE} \
        --project=${PROJECT} \
        --tier=${TARGET_TIER} \
        --quiet; then

        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                  ✅ SCALING COMPLETATO CON SUCCESSO                    ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        show_status

        echo -e "${BLUE}💡 Prossimi passi:${NC}"
        if [[ "$TARGET_TIER" == "db-g1-small" ]] || [[ "$TARGET_TIER" == "db-n1-standard"* ]]; then
            echo -e "   1. Esegui operazioni pesanti (import, migrations, etc.)"
            echo -e "   2. Quando finito, scala giù: ${CYAN}./scripts/scale-database.sh idle${NC}"
        else
            echo -e "   Database in modalità risparmio energetico"
        fi
        echo ""

    else
        echo ""
        echo -e "${RED}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                     ❌ SCALING FALLITO                                 ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Verifica i log:${NC}"
        echo "   gcloud sql operations list --instance=${INSTANCE} --limit=5"
        exit 1
    fi
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 0
fi

TARGET_TIER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        idle|setup|scrutinio|high)
            PRESET=$1
            specs=$(get_tier_specs "$PRESET")
            IFS='|' read -r tier ram vcpu cost desc <<< "$specs"
            TARGET_TIER=$tier
            shift
            ;;
        --tier)
            TARGET_TIER="$2"
            shift 2
            ;;
        --project)
            PROJECT="$2"
            shift 2
            ;;
        --instance)
            INSTANCE="$2"
            shift 2
            ;;
        --status)
            show_status
            show_tier_comparison
            exit 0
            ;;
        --help|-h)
            show_usage
            show_tier_comparison
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opzione sconosciuta: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Verify gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI non trovato${NC}"
    exit 1
fi

# Set project
gcloud config set project ${PROJECT} --quiet

# Validate target tier
if [ -z "$TARGET_TIER" ]; then
    echo -e "${RED}❌ Devi specificare un preset o --tier${NC}"
    show_usage
    exit 1
fi

# Execute scaling
scale_database "$TARGET_TIER"
