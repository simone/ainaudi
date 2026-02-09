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

echo "🗳️  Carico Referendum Costituzionale Giustizia 2026..."
run_manage loaddata fixtures/referendum_giustizia_2026.json

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4: Comuni (da CSV ISTAT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏘️  Import comuni italiani da dati ISTAT..."
echo "   (Questo può richiedere 1-2 minuti...)"

# Controlla se il file CSV esiste
# Con Docker il working dir è /app (= backend_django/)
# Senza Docker siamo nella root del progetto
if [ -z "$DOCKER_CMD" ]; then
    # Locale: usa percorso relativo da root progetto
    CSV_PATH="backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv"
else
    # Docker: usa percorso relativo da /app
    CSV_PATH="fixtures/SCUANAGRAFESTAT20252620250901.csv"
fi

if [ -f "backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv" ]; then
    run_manage import_comuni_istat --file "$CSV_PATH"
else
    echo "⚠️  File CSV comuni non trovato, salto questo step"
    echo "   Path cercato: backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv"
    echo "   Puoi scaricarlo da: https://dati.istat.it/"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5: Municipi Roma (opzionale)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# I municipi richiedono che il comune di Roma esista già (import step 4)
if [ -f "backend_django/fixtures/roma_municipi.json" ]; then
    read -p "Vuoi caricare i 15 municipi di Roma? (richiede comuni import) (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🏛️  Carico municipi di Roma..."
        run_manage loaddata fixtures/roma_municipi.json || {
            echo "❌ Errore: probabilmente Roma non esiste ancora nel database"
            echo "   Esegui prima: python manage.py import_comuni_istat --file fixtures/SCUANAGRAFESTAT20252620250901.csv"
        }
    else
        echo "⏭️  Salto municipi Roma"
    fi
else
    echo "ℹ️  Fixture municipi Roma non trovato, salto"
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

        # Stesso CSV dei comuni (contiene sia comuni che sezioni)
        if [ -z "$DOCKER_CMD" ]; then
            CSV_SEZIONI="backend_django/fixtures/SCUANAGRAFESTAT20252620250901.csv"
        else
            CSV_SEZIONI="fixtures/SCUANAGRAFESTAT20252620250901.csv"
        fi

        run_manage import_sezioni_italia --file "$CSV_SEZIONI"
    else
        echo "⚠️  File CSV sezioni non trovato"
    fi
else
    echo "⏭️  Salto import sezioni"
    echo "   Puoi importarle dopo con:"
    if [ -z "$DOCKER_CMD" ]; then
        echo "   python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv"
    else
        echo "   docker-compose exec backend python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6bis: Update Dettagli Sezioni (es. Roma)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📍 I dati ISTAT contengono plessi scolastici (edifici nazionali)."
echo "   Per collegare le sezioni agli indirizzi specifici del comune,"
echo "   serve importare i dati rilasciati dal comune stesso."
echo ""

if [ -f "backend_django/fixtures/ROMA - Sezioni.csv" ]; then
    read -p "Vuoi aggiornare le sezioni di Roma con indirizzi specifici? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🏛️  Aggiorno sezioni di Roma con indirizzi..."

        if [ -z "$DOCKER_CMD" ]; then
            CSV_ROMA="backend_django/fixtures/ROMA - Sezioni.csv"
        else
            CSV_ROMA="fixtures/ROMA - Sezioni.csv"
        fi

        run_manage update_sezioni_dettagli "$CSV_ROMA"
    else
        echo "⏭️  Salto update sezioni Roma"
    fi
else
    echo "ℹ️  File 'ROMA - Sezioni.csv' non trovato, salto questo step"
    echo "   Puoi aggiungerlo dopo in fixtures/ e eseguire:"
    echo "   python manage.py update_sezioni_dettagli 'fixtures/ROMA - Sezioni.csv'"
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
echo "   ✅ Referendum Costituzionale Giustizia 2026 (ATTIVO)"
echo "   ✅ Date: 22-23 marzo 2026"
echo "   ✅ Tipo: Confermativo (NO quorum richiesto)"
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
