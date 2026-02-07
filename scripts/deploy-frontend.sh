#!/bin/bash
set -e

# Frontend Deploy Script for Cloud Storage + CDN
# Deploys React build to Cloud Storage and invalidates CDN cache

PROJECT_ID="your-project-id"
BUCKET_NAME="rdl-frontend-prod"
CDN_URL_MAP="rdl-frontend-lb"
API_URL="https://api.rdl-example.com"  # Set your backend URL

echo "========================================="
echo "  FRONTEND DEPLOYMENT"
echo "========================================="
echo ""
echo "This will deploy the React frontend to Cloud Storage."
echo ""
echo "Configuration:"
echo "  - API URL: $API_URL"
echo "  - Bucket: gs://$BUCKET_NAME/"
echo "  - CDN: $CDN_URL_MAP"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

# Step 1: Build React
echo ""
echo ">>> Step 1/4: Building React application..."
REACT_APP_API_URL=$API_URL npm run build

if [ ! -d "build" ]; then
    echo "ERROR: Build directory not found"
    exit 1
fi

echo "✓ Build completed"

# Step 2: Upload to Cloud Storage
echo ""
echo ">>> Step 2/4: Uploading to Cloud Storage..."
gsutil -m rsync -r -d -c build/ gs://$BUCKET_NAME/

echo "✓ Upload completed"

# Step 3: Set cache headers
echo ""
echo ">>> Step 3/4: Setting cache headers..."

# Static assets: cache 1 year (immutable)
echo "    - Static assets (js, css, images): max-age=31536000, immutable"
gsutil -m setmeta \
    -h "Cache-Control:public,max-age=31536000,immutable" \
    "gs://$BUCKET_NAME/static/**" || true

# HTML files: no cache (always fresh)
echo "    - HTML files: no-cache"
gsutil -m setmeta \
    -h "Cache-Control:no-cache,no-store,must-revalidate" \
    "gs://$BUCKET_NAME/**.html"

gsutil -m setmeta \
    -h "Cache-Control:no-cache,no-store,must-revalidate" \
    "gs://$BUCKET_NAME/index.html"

echo "✓ Cache headers set"

# Step 4: Invalidate CDN cache
echo ""
echo ">>> Step 4/4: Invalidating CDN cache..."
gcloud compute url-maps invalidate-cdn-cache $CDN_URL_MAP \
    --path="/*" \
    --project=$PROJECT_ID \
    --async

echo "✓ CDN cache invalidation requested (async)"

# Summary
echo ""
echo "========================================="
echo "  DEPLOYMENT COMPLETE"
echo "========================================="
echo ""
echo "Frontend deployed successfully!"
echo ""
echo "URLs:"
echo "  - Cloud Storage: gs://$BUCKET_NAME/"
echo "  - Public URL: https://your-domain.com"
echo ""
echo "Next steps:"
echo "  1. Verify deployment at https://your-domain.com"
echo "  2. Check browser console for API connectivity"
echo "  3. Monitor CDN cache invalidation:"
echo "     gcloud compute operations list --project=$PROJECT_ID"
echo ""
