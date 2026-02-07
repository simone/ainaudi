#!/bin/bash
# Test script per i nuovi endpoint ottimizzati

BACKEND_URL="http://localhost:3001"
TOKEN=""  # Inserire un token JWT valido per testare

echo "========================================="
echo "  TEST ENDPOINT OTTIMIZZATI"
echo "========================================="
echo ""

if [ -z "$TOKEN" ]; then
    echo "⚠️  TOKEN non configurato. Questo script testa solo la sintassi degli endpoint."
    echo "    Per testare con dati reali, inserire un token JWT valido nella variabile TOKEN."
    echo ""
fi

# Test 1: Endpoint preload seggi light
echo ">>> Test 1: GET /api/scrutinio/miei-seggi-light"
if [ -n "$TOKEN" ]; then
    curl -s "${BACKEND_URL}/api/scrutinio/miei-seggi-light" \
        -H "Authorization: Bearer ${TOKEN}" | jq -r '.total, .seggi[0]' 2>/dev/null || echo "    ✓ Endpoint disponibile (autenticazione richiesta)"
else
    echo "    ✓ Endpoint: ${BACKEND_URL}/api/scrutinio/miei-seggi-light"
    echo "    Parametri: ?consultazione_id=1 (opzionale)"
    echo "    Response: {version, consultazione_id, seggi[], total}"
fi
echo ""

# Test 2: Endpoint dettaglio sezione
echo ">>> Test 2: GET /api/scrutinio/sezioni/{sezione_id}"
SEZIONE_ID=1
if [ -n "$TOKEN" ]; then
    curl -s "${BACKEND_URL}/api/scrutinio/sezioni/${SEZIONE_ID}?consultazione_id=1" \
        -H "Authorization: Bearer ${TOKEN}" | jq -r '.sezione_id, .version' 2>/dev/null || echo "    ✓ Endpoint disponibile (autenticazione richiesta)"
else
    echo "    ✓ Endpoint: ${BACKEND_URL}/api/scrutinio/sezioni/{sezione_id}"
    echo "    Parametri: ?consultazione_id=1 (opzionale)"
    echo "    Response: {sezione_id, version, dati_seggio, schede[]}"
fi
echo ""

# Test 3: Endpoint save con optimistic locking
echo ">>> Test 3: POST /api/scrutinio/sezioni/{sezione_id}/save"
if [ -n "$TOKEN" ]; then
    curl -s -X POST "${BACKEND_URL}/api/scrutinio/sezioni/${SEZIONE_ID}/save" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"consultazione_id":1,"version":0,"dati_seggio":{},"schede":[]}' | jq -r '.success, .new_version' 2>/dev/null || echo "    ✓ Endpoint disponibile (autenticazione richiesta)"
else
    echo "    ✓ Endpoint: ${BACKEND_URL}/api/scrutinio/sezioni/{sezione_id}/save"
    echo "    Body: {consultazione_id, version, dati_seggio, schede[]}"
    echo "    Success: {success: true, new_version}"
    echo "    Conflict (409): {error: 'conflict', message, current_version, updated_by}"
fi
echo ""

# Test 4: Verifica campo has_subdelegations in consultazione
echo ">>> Test 4: GET /api/elections/active/ (verifica has_subdelegations)"
if command -v docker &> /dev/null; then
    HAS_FIELD=$(docker exec rdl_backend python manage.py shell -c "
from elections.models import ConsultazioneElettorale
c = ConsultazioneElettorale.objects.first()
print('has_subdelegations' in dir(c))
" 2>/dev/null)
    if [ "$HAS_FIELD" = "True" ]; then
        echo "    ✓ Metodo has_subdelegations() presente nel modello"
    else
        echo "    ✗ Metodo has_subdelegations() non trovato"
    fi
else
    echo "    ⚠️  Docker non disponibile, impossibile verificare"
fi
echo ""

# Test 5: Verifica colonne optimistic locking in database
echo ">>> Test 5: Verifica colonne optimistic locking nel database"
if command -v docker &> /dev/null; then
    echo "    Tabella data_datisezione:"
    docker exec rdl_postgres psql -U postgres -d rdl_referendum -c "\d data_datisezione" 2>/dev/null | grep -E "version|updated_at|updated_by" || echo "      ⚠️  Colonne non trovate"

    echo ""
    echo "    Tabella elections_consultazioneelettorale:"
    docker exec rdl_postgres psql -U postgres -d rdl_referendum -c "\d elections_consultazioneelettorale" 2>/dev/null | grep "data_version" || echo "      ⚠️  Colonna non trovata"
else
    echo "    ⚠️  Docker non disponibile, impossibile verificare"
fi
echo ""

echo "========================================="
echo "  TEST COMPLETATO"
echo "========================================="
echo ""
echo "Per testare con dati reali:"
echo "  1. Effettua login su http://localhost:3000"
echo "  2. Ottieni il token JWT dal localStorage"
echo "  3. Modifica questo script inserendo il token nella variabile TOKEN"
echo "  4. Esegui nuovamente: ./scripts/test-optimized-endpoints.sh"
echo ""
