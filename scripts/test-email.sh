#!/bin/bash
# Script per testare invio email sia con Docker che senza
# Uso: ./scripts/test-email.sh destinatario@example.com

set -e

RECIPIENT="$1"

if [ -z "$RECIPIENT" ]; then
    echo "❌ Errore: specifica un destinatario"
    echo ""
    echo "Uso: ./scripts/test-email.sh destinatario@example.com"
    exit 1
fi

# Valida email
if [[ ! "$RECIPIENT" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo "❌ Errore: email non valida: $RECIPIENT"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Invio Email"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📧 Destinatario: $RECIPIENT"
echo ""

# Controlla se Docker è in uso
if docker-compose ps 2>/dev/null | grep -q "backend.*Up"; then
    echo "🐳 Rilevato Docker Compose attivo"
    echo "📦 Eseguo test dentro il container backend..."
    echo ""

    docker-compose exec -T backend python test_email.py "$RECIPIENT"

elif docker ps 2>/dev/null | grep -q "ainaudi.*backend"; then
    echo "🐳 Rilevato Docker attivo"
    echo "📦 Eseguo test dentro il container backend..."
    echo ""

    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep backend | head -1)
    docker exec -it "$CONTAINER_NAME" python test_email.py "$RECIPIENT"

else
    echo "💻 Docker non rilevato, eseguo in locale"
    echo ""

    # Controlla se siamo nella directory giusta
    if [ ! -f "backend_django/test_email.py" ]; then
        echo "❌ Errore: test_email.py non trovato"
        echo "   Esegui questo script dalla root del progetto"
        exit 1
    fi

    cd backend_django
    python test_email.py "$RECIPIENT"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
