#!/bin/bash
# Development Docker utilities

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

print_help() {
    echo "RDL Referendum - Docker Development Utilities"
    echo ""
    echo "Usage: ./docker/scripts/docker-dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up          Start all services"
    echo "  down        Stop all services"
    echo "  restart     Restart all services"
    echo "  logs        Show logs (follow mode)"
    echo "  logs-back   Show backend logs only"
    echo "  logs-front  Show frontend logs only"
    echo "  shell       Open Django shell"
    echo "  bash        Open bash in backend container"
    echo "  migrate     Run Django migrations"
    echo "  makemig     Create new migrations"
    echo "  superuser   Create Django superuser"
    echo "  test        Run backend tests"
    echo "  psql        Open PostgreSQL shell"
    echo "  clean       Remove all containers and volumes"
    echo "  rebuild     Rebuild all containers"
    echo ""
}

case "$1" in
    up)
        echo -e "${GREEN}Starting all services...${NC}"
        docker-compose up -d
        echo -e "${GREEN}Services started!${NC}"
        echo ""
        echo "  Frontend:  http://localhost:3000"
        echo "  Backend:   http://localhost:3001"
        echo "  Admin:     http://localhost:3001/admin/"
        echo "  Adminer:   http://localhost:8080"
        ;;
    down)
        echo -e "${YELLOW}Stopping all services...${NC}"
        docker-compose down
        ;;
    restart)
        echo -e "${YELLOW}Restarting all services...${NC}"
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    logs-back)
        docker-compose logs -f backend
        ;;
    logs-front)
        docker-compose logs -f frontend
        ;;
    shell)
        echo -e "${GREEN}Opening Django shell...${NC}"
        docker-compose exec backend python manage.py shell
        ;;
    bash)
        echo -e "${GREEN}Opening bash in backend container...${NC}"
        docker-compose exec backend bash
        ;;
    migrate)
        echo -e "${GREEN}Running migrations...${NC}"
        docker-compose exec backend python manage.py migrate
        ;;
    makemig)
        echo -e "${GREEN}Creating migrations...${NC}"
        docker-compose exec backend python manage.py makemigrations
        ;;
    superuser)
        echo -e "${GREEN}Creating superuser...${NC}"
        docker-compose exec backend python manage.py createsuperuser
        ;;
    test)
        echo -e "${GREEN}Running tests...${NC}"
        docker-compose exec backend pytest
        ;;
    psql)
        echo -e "${GREEN}Opening PostgreSQL shell...${NC}"
        docker-compose exec db psql -U postgres -d rdl_referendum
        ;;
    clean)
        echo -e "${RED}WARNING: This will remove all containers and volumes!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans
            echo -e "${GREEN}Cleaned!${NC}"
        fi
        ;;
    rebuild)
        echo -e "${YELLOW}Rebuilding all containers...${NC}"
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    *)
        print_help
        ;;
esac
