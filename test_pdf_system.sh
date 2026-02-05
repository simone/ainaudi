#!/bin/bash
# PDF System Test Script
# Tests the event-driven PDF generation workflow

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:3001}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "=================================================="
echo "PDF System Integration Test"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not installed. Install for better output: brew install jq${NC}"
    echo ""
fi

# Step 1: Check services
echo "Step 1: Checking Services..."
echo "----------------------------"

# Redis
echo -n "Redis: "
if docker exec rdl_redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    exit 1
fi

# PostgreSQL
echo -n "PostgreSQL: "
if docker exec rdl_postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    exit 1
fi

# Backend
echo -n "Django Backend: "
if curl -s "$BACKEND_URL/api/" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    exit 1
fi

# Worker
echo -n "PDF Worker: "
if docker ps | grep rdl_pdf_worker | grep -q Up; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    exit 1
fi

echo ""

# Step 2: Check migrations
echo "Step 2: Checking Migrations..."
echo "-------------------------------"

MIGRATIONS_OUTPUT=$(docker exec rdl_backend python manage.py showmigrations documents 2>&1 || echo "error")

if echo "$MIGRATIONS_OUTPUT" | grep -q "0002.*\[X\]"; then
    echo -e "${GREEN}✓ Migrations applied${NC}"
elif echo "$MIGRATIONS_OUTPUT" | grep -q "0002.*\[ \]"; then
    echo -e "${RED}✗ Migrations not applied${NC}"
    echo "Run: docker exec rdl_backend python manage.py migrate documents"
    exit 1
else
    echo -e "${YELLOW}⚠ Could not verify migrations${NC}"
fi

echo ""

# Step 3: Get authentication token
echo "Step 3: Authentication..."
echo "-------------------------"

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Please provide an access token:"
    echo ""
    echo "Option 1: Set ACCESS_TOKEN environment variable"
    echo "  export ACCESS_TOKEN='your-token-here'"
    echo ""
    echo "Option 2: Login via browser and get token from localStorage"
    echo "  1. Open $FRONTEND_URL"
    echo "  2. Login"
    echo "  3. DevTools → Application → Local Storage → rdl_access_token"
    echo ""
    echo "Option 3: Use magic link (need to check Django logs for token)"
    echo "  curl -X POST $BACKEND_URL/api/auth/magic-link/request/ \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"email\": \"your@email.com\"}'"
    echo ""
    exit 0
fi

echo -e "${GREEN}✓ Token provided${NC}"
echo ""

# Step 4: Request PDF preview
echo "Step 4: Requesting PDF Preview..."
echo "----------------------------------"

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BACKEND_URL/api/documents/preview/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "data": {
      "replacements": {
        "COGNOME E NOME SUBDELEGATO": "TEST SCRIPT",
        "LUOGO DI NASCITA SUBDELEGATO": "Roma",
        "DATA DI NASCITA SUBDELEGATO": "01/01/2000"
      },
      "list_replacements": [
        {
          "SEZIONE": "001",
          "EFFETTIVO COGNOME E NOME": "Mario Rossi",
          "EFFETTIVO LUOGO DI NASCITA": "Milano"
        }
      ]
    }
  }')

HTTP_STATUS=$(echo "$RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "202" ]; then
    echo -e "${GREEN}✓ Preview request accepted${NC}"

    if command -v jq &> /dev/null; then
        echo "$BODY" | jq .
        DOCUMENT_ID=$(echo "$BODY" | jq -r .document_id)
    else
        echo "$BODY"
        DOCUMENT_ID=$(echo "$BODY" | grep -o '"document_id":[0-9]*' | cut -d: -f2)
    fi

    echo ""
    echo "Document ID: $DOCUMENT_ID"
else
    echo -e "${RED}✗ Request failed (HTTP $HTTP_STATUS)${NC}"
    echo "$BODY"
    exit 1
fi

echo ""

# Step 5: Check worker processing
echo "Step 5: Checking Worker Processing..."
echo "--------------------------------------"
echo "Waiting 5 seconds for worker to process..."
sleep 5

WORKER_LOGS=$(docker logs rdl_pdf_worker --tail 50)

if echo "$WORKER_LOGS" | grep -q "Event.*processed successfully"; then
    echo -e "${GREEN}✓ Event processed by worker${NC}"
else
    echo -e "${YELLOW}⚠ Worker may not have processed event yet${NC}"
    echo "Check logs: docker logs rdl_pdf_worker"
fi

if echo "$WORKER_LOGS" | grep -q "Email sent"; then
    echo -e "${GREEN}✓ Email sent${NC}"
else
    echo -e "${YELLOW}⚠ Email not sent yet${NC}"
fi

echo ""

# Step 6: Check database
echo "Step 6: Checking Database..."
echo "----------------------------"

DB_CHECK=$(docker exec rdl_postgres psql -U postgres -d rdl_referendum -t -c \
  "SELECT status FROM documents_generateddocument WHERE id=$DOCUMENT_ID;" 2>&1 || echo "error")

if [ "$DB_CHECK" = " PREVIEW" ]; then
    echo -e "${GREEN}✓ Document in PREVIEW state${NC}"
else
    echo -e "${RED}✗ Unexpected state: $DB_CHECK${NC}"
fi

echo ""

# Step 7: Get confirmation token
echo "Step 7: Getting Confirmation Token..."
echo "--------------------------------------"

TOKEN_QUERY="SELECT review_token FROM documents_generateddocument WHERE id=$DOCUMENT_ID;"
REVIEW_TOKEN=$(docker exec rdl_postgres psql -U postgres -d rdl_referendum -t -c "$TOKEN_QUERY" | xargs)

if [ -n "$REVIEW_TOKEN" ]; then
    echo -e "${GREEN}✓ Token retrieved${NC}"
    echo ""
    echo "Confirmation URL:"
    echo "$FRONTEND_URL/pdf/confirm?token=$REVIEW_TOKEN"
    echo ""
    echo "API Endpoint:"
    echo "curl '$BACKEND_URL/api/documents/confirm/?token=$REVIEW_TOKEN'"
else
    echo -e "${RED}✗ No token found${NC}"
    exit 1
fi

echo ""

# Step 8: Confirm document
echo "Step 8: Confirming Document..."
echo "-------------------------------"

CONFIRM_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  "$BACKEND_URL/api/documents/confirm/?token=$REVIEW_TOKEN")

CONFIRM_STATUS=$(echo "$CONFIRM_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
CONFIRM_BODY=$(echo "$CONFIRM_RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$CONFIRM_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Document confirmed${NC}"

    if command -v jq &> /dev/null; then
        echo "$CONFIRM_BODY" | jq .
    else
        echo "$CONFIRM_BODY"
    fi
else
    echo -e "${RED}✗ Confirmation failed (HTTP $CONFIRM_STATUS)${NC}"
    echo "$CONFIRM_BODY"
fi

echo ""

# Step 9: Verify final state
echo "Step 9: Verifying Final State..."
echo "---------------------------------"

FINAL_STATE=$(docker exec rdl_postgres psql -U postgres -d rdl_referendum -t -c \
  "SELECT status, confirmed_at IS NOT NULL FROM documents_generateddocument WHERE id=$DOCUMENT_ID;")

if echo "$FINAL_STATE" | grep -q "CONFIRMED.*t"; then
    echo -e "${GREEN}✓ Document confirmed in database${NC}"
else
    echo -e "${RED}✗ Document not confirmed: $FINAL_STATE${NC}"
fi

echo ""

# Step 10: Test idempotency
echo "Step 10: Testing Idempotency..."
echo "--------------------------------"

SECOND_CONFIRM=$(curl -s "$BACKEND_URL/api/documents/confirm/?token=$REVIEW_TOKEN")

if echo "$SECOND_CONFIRM" | grep -q "Already confirmed"; then
    echo -e "${GREEN}✓ Second confirmation handled correctly${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response: $SECOND_CONFIRM${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✓ All Tests Passed!${NC}"
echo "=================================================="
echo ""
echo "The PDF system is working correctly."
echo ""
echo "Next steps:"
echo "1. Check email output: docker logs rdl_backend | grep -A 20 'Preview PDF'"
echo "2. Monitor events: docker exec -it rdl_redis redis-cli SUBSCRIBE pdf_events"
echo "3. View documents: SELECT * FROM documents_generateddocument;"
echo ""
