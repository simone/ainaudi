# Deployment Google App Engine (GAE)

## Template PDF Upload - Cloud Storage Configuration

### Prerequisiti

1. **Google Cloud Storage Bucket**
   ```bash
   # Crea bucket per media files
   gsutil mb -p PROJECT_ID gs://rdl-media-bucket

   # Imposta permessi pubblici in lettura
   gsutil iam ch allUsers:objectViewer gs://rdl-media-bucket
   ```

2. **Service Account con permessi Storage**
   ```bash
   # Crea service account
   gcloud iam service-accounts create rdl-storage-sa \
       --display-name="RDL Storage Service Account"

   # Assegna ruolo Storage Object Admin
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:rdl-storage-sa@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/storage.objectAdmin"

   # Scarica chiave JSON (per local testing)
   gcloud iam service-accounts keys create storage-key.json \
       --iam-account=rdl-storage-sa@PROJECT_ID.iam.gserviceaccount.com
   ```

### app.yaml Configuration

```yaml
runtime: python311
service: default
entrypoint: gunicorn -b :$PORT config.wsgi:application

env_variables:
  # Django settings
  DEBUG: "False"
  DJANGO_SECRET_KEY: "your-secret-key-from-secret-manager"
  ALLOWED_HOSTS: "your-domain.appspot.com,your-custom-domain.com"

  # Database (Cloud SQL)
  DB_HOST: "/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME"
  DB_NAME: "rdl_referendum"
  DB_USER: "postgres"
  DB_PASSWORD: "from-secret-manager"

  # Cloud Storage for media files
  USE_GCS: "True"
  GS_BUCKET_NAME: "rdl-media-bucket"
  GS_PROJECT_ID: "PROJECT_ID"

  # Redis (Memorystore)
  REDIS_HOST: "10.x.x.x"  # Internal IP from Memorystore
  REDIS_PORT: "6379"

  # Email
  EMAIL_BACKEND: "django.core.mail.backends.smtp.EmailBackend"
  EMAIL_HOST: "smtp.gmail.com"
  EMAIL_PORT: "587"
  EMAIL_HOST_USER: "from-secret-manager"
  EMAIL_HOST_PASSWORD: "from-secret-manager"

  # Frontend URL
  FRONTEND_URL: "https://your-domain.com"

# Cloud SQL connection
vpc_access_connector:
  name: "projects/PROJECT_ID/locations/REGION/connectors/rdl-connector"

# Static files handler (whitenoise handles in Django)
handlers:
- url: /static
  static_dir: staticfiles/
  secure: always

- url: /.*
  script: auto
  secure: always

# Instance resources
instance_class: F2
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.65
```

### Local Testing con GCS

```bash
# Imposta credenziali
export GOOGLE_APPLICATION_CREDENTIALS="path/to/storage-key.json"

# Abilita GCS nel .env locale
export USE_GCS=True
export GS_BUCKET_NAME=rdl-media-bucket
export GS_PROJECT_ID=your-project-id

# Testa upload
python manage.py shell
>>> from django.core.files.base import ContentFile
>>> from documents.models import Template
>>> t = Template.objects.first()
>>> t.template_file.save('test.pdf', ContentFile(b'test'))
>>> print(t.template_file.url)
# https://storage.googleapis.com/rdl-media-bucket/templates/test.pdf
```

### Deploy

```bash
# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Deploy to GAE
gcloud app deploy app.yaml --project=PROJECT_ID

# Verify
curl https://PROJECT_ID.appspot.com/api/documents/templates/
```

### Monitoring

```bash
# Logs
gcloud app logs tail -s default

# Storage usage
gsutil du -sh gs://rdl-media-bucket

# List uploaded templates
gsutil ls -lh gs://rdl-media-bucket/templates/
```

### Cleanup Old Files (Optional)

```bash
# Lifecycle policy per auto-delete preview PDFs dopo 7 giorni
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 7,
          "matchesPrefix": ["generated_documents/preview/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://rdl-media-bucket
```

### Security Best Practices

1. **Secret Manager per credenziali sensibili**
   ```bash
   # Store secrets
   echo -n "SECRET_VALUE" | gcloud secrets create SECRET_NAME --data-file=-

   # Access in app.yaml
   env_variables:
     DJANGO_SECRET_KEY: "projects/PROJECT_ID/secrets/django-secret-key/versions/latest"
   ```

2. **Bucket privato con Signed URLs** (alternativa a public bucket)
   ```python
   # In models.py
   def get_signed_url(self):
       from google.cloud import storage
       client = storage.Client()
       bucket = client.bucket(settings.GS_BUCKET_NAME)
       blob = bucket.blob(self.template_file.name)
       return blob.generate_signed_url(expiration=timedelta(hours=1))
   ```

3. **CORS per upload da frontend**
   ```bash
   # cors.json
   cat > cors.json <<EOF
   [
     {
       "origin": ["https://your-domain.com"],
       "method": ["GET", "POST", "PUT"],
       "responseHeader": ["Content-Type"],
       "maxAgeSeconds": 3600
     }
   ]
   EOF

   gsutil cors set cors.json gs://rdl-media-bucket
   ```

### Costs Estimate (Italia)

- **Cloud Storage**: ~€0.020/GB/mese (Standard)
- **Network Egress**: €0.12/GB (primi 1TB)
- **Operations**: Get/List €0.004 per 10k requests

**Stima mensile per 100 template PDF (5GB):**
- Storage: €0.10
- Egress (100 download/giorno): €1.80
- **Totale: ~€2/mese**

### Troubleshooting

**Error: Permission denied**
```bash
# Verifica IAM
gsutil iam get gs://rdl-media-bucket

# Aggiungi permessi mancanti
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

**Error: Bucket not found**
```bash
# Verifica bucket esiste
gsutil ls | grep rdl-media

# Crea se mancante
gsutil mb -p PROJECT_ID gs://rdl-media-bucket
```

**Files not public**
```bash
# Rendi bucket pubblico in lettura
gsutil iam ch allUsers:objectViewer gs://rdl-media-bucket
```

---

**Ultima modifica**: 2026-02-04
