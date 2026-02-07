#!/bin/bash
# Test scrutinio aggregato with proper JWT token

set -e

echo "=== TESTING SCRUTINIO AGGREGATO ==="
echo ""

# Generate JWT token for test delegato
echo "Generating JWT token for test.delegato@example.com..."
TOKEN=$(docker exec rdl_backend python manage.py shell -c "
from core.models import User
from rest_framework_simplejwt.tokens import RefreshToken

user = User.objects.get(email='test.delegato@example.com')
refresh = RefreshToken.for_user(user)
print(str(refresh.access_token))
" 2>/dev/null | tail -n 1)

if [ -z "$TOKEN" ]; then
    echo "✗ Failed to generate token"
    exit 1
fi

echo "✓ Token generated"
echo ""

# Test endpoint
echo "Testing GET /api/scrutinio/aggregato?consultazione_id=1..."

# Save response to temp file
TEMP_FILE=$(mktemp)
HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TEMP_FILE" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:3001/api/scrutinio/aggregato?consultazione_id=1)

BODY=$(cat "$TEMP_FILE")
rm -f "$TEMP_FILE"

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ SUCCESS - Endpoint returned 200 OK"
    echo ""
    echo "Response preview:"
    echo "$BODY" | python3 -m json.tool | head -n 30
    echo "..."
elif [ "$HTTP_CODE" = "403" ]; then
    echo "✗ FAILED - Still getting 403 Forbidden"
    echo "Response: $BODY"
    exit 1
elif [ "$HTTP_CODE" = "401" ]; then
    echo "✗ FAILED - 401 Unauthorized (token issue)"
    echo "Response: $BODY"
    exit 1
else
    echo "? Unexpected status code: $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi

echo ""
echo "=== ALL TESTS PASSED ==="
