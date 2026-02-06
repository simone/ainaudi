# Shared Storage Solution for Django & PDF Service

## Problem

Both Django backend and PDF generation service need access to uploaded template files. Currently using local filesystem which doesn't work across services.

---

## Solution

### Development: Docker Shared Volume

Use a named Docker volume or bind mount to share the `media/` directory between services.

#### docker-compose.yml Configuration

```yaml
version: '3.8'

services:
  backend:
    build: ./backend_django
    volumes:
      - shared_media:/app/media  # Shared volume for uploaded files
      - ./backend_django:/app
    environment:
      - MEDIA_ROOT=/app/media
    ports:
      - "3001:8000"

  pdf_service:
    build: ./pdf_service  # Your PDF generation service
    volumes:
      - shared_media:/app/media  # Same shared volume
    environment:
      - MEDIA_ROOT=/app/media
    ports:
      - "3002:8000"

  frontend:
    build: .
    volumes:
      - ./src:/app/src
      - ./public:/app/public
    ports:
      - "3000:5173"

  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=rdl_db
      - POSTGRES_USER=rdl_user
      - POSTGRES_PASSWORD=rdl_password

volumes:
  shared_media:  # Named volume for media files
  postgres_data:
```

**Benefits:**
- ✅ Simple setup for development
- ✅ Files automatically accessible to both services
- ✅ Persists data across container restarts
- ✅ No cloud dependencies for local dev

---

### Production: Google Cloud Storage (GCS)

Use Django's storage backends with Google Cloud Storage for production.

#### 1. Install Dependencies

```bash
pip install django-storages[google]
```

Add to `backend_django/requirements.txt`:
```
django-storages[google]==1.14.4
google-cloud-storage==2.18.2
```

#### 2. Django Settings

**File:** `backend_django/config/settings.py`

```python
import os
from google.cloud import storage

# Media files configuration
if os.getenv('ENVIRONMENT') == 'production':
    # Production: Use Google Cloud Storage
    DEFAULT_FILE_STORAGE = 'storages.backends.gcs.GoogleCloudStorage'
    GS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'rdleu2024-media')
    GS_PROJECT_ID = os.getenv('GCP_PROJECT_ID')

    # Optional: Use specific credentials file
    # GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
    #     'path/to/service-account.json'
    # )

    # Public URLs for media files
    GS_DEFAULT_ACL = 'publicRead'  # or 'private' for authenticated access
    GS_QUERYSTRING_AUTH = False

    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'
else:
    # Development: Use local filesystem with shared volume
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_URL = '/media/'
```

#### 3. Create GCS Bucket

```bash
# Create bucket (one-time setup)
gsutil mb -l europe-west1 gs://rdleu2024-media

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://rdleu2024-media  # For public access
# OR
gsutil iam ch serviceAccount:your-service@appspot.gserviceaccount.com:objectAdmin gs://rdleu2024-media
```

#### 4. Configure Service Account

Create service account with Storage Object Admin role:

```bash
gcloud iam service-accounts create rdl-storage \
    --display-name="RDL Storage Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:rdl-storage@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create key file
gcloud iam service-accounts keys create storage-key.json \
    --iam-account=rdl-storage@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### 5. GAE Configuration

**File:** `app.yaml`

```yaml
runtime: python311
service: default

env_variables:
  ENVIRONMENT: production
  GCS_BUCKET_NAME: rdleu2024-media
  GCP_PROJECT_ID: your-project-id
  # Django will use Application Default Credentials on GAE

handlers:
  # Static files from build
  - url: /static
    static_dir: build/static

  # All other requests go to Django
  - url: /.*
    script: auto
    secure: always
```

---

## Implementation Steps

### Step 1: Update Docker Compose (Development)

1. Edit `docker-compose.yml` to add shared volume
2. Rebuild containers:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

### Step 2: Update Django Settings

1. Add environment-based storage configuration
2. Install django-storages:
   ```bash
   docker exec rdl_backend pip install django-storages[google]
   ```

### Step 3: Test Locally

1. Upload a template via "Gestione Template"
2. Verify file appears in `media/templates/` directory
3. Check both services can access the file

### Step 4: Production Setup (When Ready)

1. Create GCS bucket
2. Configure service account
3. Update `app.yaml` with environment variables
4. Deploy to GAE

---

## File URL Patterns

### Development (Local/Docker)

```
Template file: /app/media/templates/uuid-here.pdf
URL: http://localhost:3001/media/templates/uuid-here.pdf
```

### Production (GCS)

```
Template file: gs://rdleu2024-media/templates/uuid-here.pdf
URL: https://storage.googleapis.com/rdleu2024-media/templates/uuid-here.pdf
```

---

## Migration Strategy

### Option A: Keep Existing Files (Recommended)

If templates are already uploaded to local filesystem:

```bash
# Copy existing media files to GCS
gsutil -m cp -r media/* gs://rdleu2024-media/
```

### Option B: Re-upload Templates

Use "Gestione Template" UI to re-upload all templates after switching to GCS.

---

## Alternative: Nginx Reverse Proxy (Simpler for Dev)

If you don't need separate services, use Nginx to serve media files:

**docker-compose.yml:**

```yaml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - shared_media:/usr/share/nginx/html/media:ro
    ports:
      - "8080:80"
    depends_on:
      - backend

  backend:
    volumes:
      - shared_media:/app/media

volumes:
  shared_media:
```

Both Django and PDF service write to shared_media, Nginx serves publicly.

---

## Recommended Approach

**Development:**
```
Docker Compose with shared named volume
└── Simplest, no cloud dependencies
```

**Production:**
```
Google Cloud Storage
└── Scalable, accessible from all services
└── No server storage needed
└── Built-in CDN capabilities
```

---

## Code Example: Accessing Files from PDF Service

```python
# pdf_service/generator.py

import os
from google.cloud import storage

def get_template_file_path(template_file_url):
    """
    Get template file path, works for both local and GCS.
    """
    if os.getenv('ENVIRONMENT') == 'production':
        # Download from GCS to temporary file
        client = storage.Client()
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        bucket = client.bucket(bucket_name)

        # Extract blob path from URL
        blob_path = template_file_url.replace(
            f'https://storage.googleapis.com/{bucket_name}/', ''
        )
        blob = bucket.blob(blob_path)

        # Download to temp file
        temp_path = f'/tmp/{os.path.basename(blob_path)}'
        blob.download_to_filename(temp_path)
        return temp_path
    else:
        # Local development: use shared volume
        return template_file_url.replace('http://localhost:3001', '/app')
```

---

## Next Steps

1. ✅ Update `docker-compose.yml` with shared volume
2. ✅ Test file upload/access in development
3. ⏸️ Production GCS setup (when deploying to GAE)

---

**Created**: 2026-02-05
**Status**: Development solution ready, production solution documented
