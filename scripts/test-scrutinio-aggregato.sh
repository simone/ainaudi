#!/bin/bash
# Quick test per endpoint scrutinio aggregato

echo "=== TEST SCRUTINIO AGGREGATO ==="
echo ""

# Test 1: Check endpoint accessibility (401 expected without token)
echo "Test 1: Verifica endpoint disponibile..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/scrutinio/aggregato?consultazione_id=1)

if [ "$RESPONSE" = "401" ] || [ "$RESPONSE" = "403" ]; then
    echo "✓ Endpoint disponibile (401/403 atteso senza auth)"
elif [ "$RESPONSE" = "200" ]; then
    echo "✓ Endpoint funzionante (200 OK)"
elif [ "$RESPONSE" = "404" ]; then
    echo "✗ Endpoint NON trovato (404)"
    exit 1
elif [ "$RESPONSE" = "500" ]; then
    echo "✗ Errore server (500)"
    echo "Checking logs..."
    docker logs rdl_backend --tail 20 | grep -i error
    exit 1
else
    echo "? Status code inatteso: $RESPONSE"
fi

echo ""

# Test 2: Check view is loaded in Django
echo "Test 2: Verifica view caricata in Django..."
VIEW_CHECK=$(docker exec rdl_backend python manage.py shell -c "
from data.views_scrutinio_aggregato import ScrutinioAggregatoView
print('OK' if ScrutinioAggregatoView else 'FAIL')
" 2>&1 | grep -o "OK")

if [ "$VIEW_CHECK" = "OK" ]; then
    echo "✓ ScrutinioAggregatoView importabile"
else
    echo "✗ Errore import view"
    exit 1
fi

echo ""

# Test 3: Check URL registration
echo "Test 3: Verifica URL registration..."
URL_CHECK=$(docker exec rdl_backend grep "aggregato" /app/data/urls.py)
if [ -n "$URL_CHECK" ]; then
    echo "✓ URL 'aggregato' registrato"
    echo "  $URL_CHECK"
else
    echo "✗ URL non registrato"
    exit 1
fi

echo ""
echo "=== TUTTI I TEST PASSATI ==="
echo ""
echo "Per testare con dati reali:"
echo "  1. Login su http://localhost:3000 come delegato"
echo "  2. Click su 'Scrutinio Aggregato' nel menu"
echo "  3. Naviga la gerarchia territoriale"
echo ""
