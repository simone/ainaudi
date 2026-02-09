#!/bin/bash
# Script per inizializzare il database da zero con tutti i dati necessari
# Uso: ./scripts/init-db.sh

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Inizializzazione Database AInaudi"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Rileva ambiente (Docker o locale)
if docker-compose ps 2>/dev/null | grep -q "backend.*Up"; then
    echo "🐳 Rilevato Docker Compose"
    DOCKER_CMD="docker-compose exec -T backend"
elif docker ps 2>/dev/null | grep -q "ainaudi.*backend"; then
    echo "🐳 Rilevato Docker"
    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep backend | head -1)
    DOCKER_CMD="docker exec -i $CONTAINER_NAME"
else
    echo "💻 Esecuzione in locale (no Docker)"
    DOCKER_CMD=""
fi

# Helper function per eseguire comandi Django
run_manage() {
    if [ -z "$DOCKER_CMD" ]; then
        cd backend_django
        python manage.py "$@"
        cd ..
    else
        $DOCKER_CMD python manage.py "$@"
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1: Migrations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_manage migrate

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Dati Iniziali (Regioni, Province)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📍 Carico Regioni e Province italiane..."
run_manage loaddata fixtures/initial_data.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3: Consultazione Elettorale"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🗳️  Carico Consultazione Multipla 2025..."
run_manage loaddata fixtures/consultazione_multipla_2025.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4: Comuni (da CSV ISTAT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏘️  Import comuni italiani da dati ISTAT..."
echo "   (Questo può richiedere 1-2 minuti...)"

# Controlla se il file CSV esiste
if [ -f "backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv" ]; then
    run_manage import_comuni_istat backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv
else
    echo "⚠️  File CSV comuni non trovato, salto questo step"
    echo "   Puoi scaricarlo da: https://dati.istat.it/"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5: Municipi Roma (opzionale)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "backend_django/fixtures/roma_municipi.json" ]; then
    echo "🏛️  Carico municipi di Roma..."
    run_manage loaddata fixtures/roma_municipi.json
else
    echo "⏭️  Fixture municipi Roma non trovato, salto"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6: Sezioni Elettorali (opzionale)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Vuoi importare le sezioni elettorali ora? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv" ]; then
        echo "🗳️  Import sezioni italiane..."
        echo "   (Questo può richiedere 5-10 minuti per tutta Italia...)"
        run_manage import_sezioni_italia backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv
    else
        echo "⚠️  File CSV sezioni non trovato"
    fi
else
    echo "⏭️  Salto import sezioni"
    echo "   Puoi importarle dopo con:"
    echo "   python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 7: Superuser Django"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Vuoi creare un superuser adesso? (Y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -z "$DOCKER_CMD" ]; then
        cd backend_django
        python manage.py createsuperuser
        cd ..
    else
        $DOCKER_CMD python manage.py createsuperuser
    fi
else
    echo "⏭️  Salto creazione superuser"
    echo "   Puoi crearlo dopo con: python manage.py createsuperuser"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ INIZIALIZZAZIONE COMPLETATA!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Database popolato con:"
echo "   ✅ 20 Regioni"
echo "   ✅ 107 Province"
echo "   ✅ ~8.000 Comuni (se CSV importato)"
echo "   ✅ Consultazione Elettorale attiva"
echo "   ✅ 5 Referendum + Europee + Politiche + Comunali"
echo ""
echo "🚀 Prossimi passi:"
echo "   1. Accedi: http://localhost:3000"
echo "   2. Login con Magic Link"
echo "   3. Admin: http://localhost:3001/admin"
echo ""
echo "📖 Per importare dati specifici:"
echo "   - Sezioni: python manage.py import_sezioni_italia <csv>"
echo "   - Municipi: python manage.py import_municipi <csv>"
echo ""
