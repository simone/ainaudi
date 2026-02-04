# Event-Driven PDF Generation - Quick Start Guide

## 🚀 Getting Started (5 Minutes)

### 1. Apply Database Migrations
```bash
cd backend_django
python manage.py migrate documents
```

Expected output:
```
Running migrations:
  Applying documents.0002_generateddocument_confirmation_ip_and_more... OK
```

### 2. Start All Services
```bash
# From project root
docker-compose up -d
```

Services started:
- ✅ PostgreSQL (port 5432)
- ✅ Django Backend (port 3001)
- ✅ React Frontend (port 3000)
- ✅ Redis (port 6379)
- ✅ **PDF Worker** (new!)

### 3. Verify Worker is Running
```bash
docker logs -f rdl_pdf_worker
```

Should see:
```
PDF Worker started, listening on pdf_events
Redis: redis:6379
```

Press Ctrl+C to exit logs.

---

## 🧪 Test the System (10 Minutes)

### Step 1: Get Access Token
Login to the app and get your JWT token:

```bash
# Option A: From browser DevTools
# 1. Open http://localhost:3000
# 2. Login
# 3. Open DevTools → Application → Local Storage
# 4. Copy 'rdl_access_token' value

# Option B: Using magic link
curl -X POST http://localhost:3001/api/auth/magic-link/request/ \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'

# Check Django console logs for token, then:
curl -X POST http://localhost:3001/api/auth/magic-link/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN_FROM_EMAIL"}'
```

### Step 2: Request PDF Preview
```bash
export TOKEN="your-access-token"

curl -X POST http://localhost:3001/api/documents/preview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "data": {
      "replacements": {
        "COGNOME E NOME SUBDELEGATO": "Mario Rossi",
        "LUOGO DI NASCITA SUBDELEGATO": "Roma",
        "DATA DI NASCITA SUBDELEGATO": "01/01/1980"
      },
      "list_replacements": [
        {
          "SEZIONE": "001",
          "EFFETTIVO COGNOME E NOME": "Giuseppe Verdi",
          "EFFETTIVO LUOGO DI NASCITA": "Milano"
        }
      ]
    }
  }'
```

Expected response:
```json
{
  "message": "Preview request queued. Check your email.",
  "document_id": 1,
  "status": "PREVIEW",
  "expires_at": "2026-02-05T12:00:00Z"
}
```

### Step 3: Check Email (Console)
In development, emails are printed to console:

```bash
docker logs rdl_backend | grep -A 50 "Preview PDF"
```

Or for worker logs:
```bash
docker logs rdl_pdf_worker
```

You should see:
```
Processing PREVIEW_PDF_AND_EMAIL event abc-123
Email sent successfully to ['user@example.com']
Event abc-123 processed successfully
```

### Step 4: Confirm Document
Extract the token from the email output (look for `confirm?token=...`), then:

```bash
# Method 1: API call
curl "http://localhost:3001/api/documents/confirm/?token=pdf-1:SIGNATURE_HERE"

# Method 2: Browser (better for testing)
# Open: http://localhost:3000/pdf/confirm?token=pdf-1:SIGNATURE_HERE
```

Expected response:
```json
{
  "message": "Document confirmed",
  "document_id": 1,
  "status": "CONFIRMED",
  "confirmed_at": "2026-02-04T12:30:00Z",
  "pdf_url": null
}
```

### Step 5: Verify in Database
```bash
docker exec -it rdl_postgres psql -U postgres -d rdl_referendum

SELECT id, status, confirmed_at FROM documents_generateddocument;
```

Expected:
```
 id |  status   |       confirmed_at
----+-----------+------------------------
  1 | CONFIRMED | 2026-02-04 12:30:00+00
```

---

## 🔍 Monitor the System

### Watch All Events in Real-Time
```bash
# Terminal 1: Redis events
docker exec -it rdl_redis redis-cli
> SUBSCRIBE pdf_events

# Terminal 2: Worker processing
docker logs -f rdl_pdf_worker

# Terminal 3: Django API
docker logs -f rdl_backend
```

### Check System Health
```bash
# Redis
docker exec rdl_redis redis-cli ping
# Expected: PONG

# Worker
docker ps | grep pdf_worker
# Should show: Up X seconds (healthy)

# Database
docker exec rdl_postgres pg_isready
# Expected: accepting connections
```

---

## 🐛 Troubleshooting

### Problem: Worker not receiving events

**Check 1**: Redis connection
```bash
docker exec rdl_pdf_worker python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
# Expected: True
```

**Check 2**: Channel name
```bash
# In Django shell
docker exec -it rdl_backend python manage.py shell
>>> from django.conf import settings
>>> print(settings.REDIS_PDF_EVENT_CHANNEL)
# Should be: pdf_events
```

**Check 3**: Worker logs
```bash
docker logs rdl_pdf_worker --tail 100
```

### Problem: PDF generation fails

**Check 1**: Template files exist
```bash
docker exec rdl_pdf_worker ls -la /app/templates/
# Should show: individuale.pdf, riepilogativo.pdf
```

**Check 2**: PyMuPDF installed
```bash
docker exec rdl_pdf_worker python -c "import fitz; print(fitz.__version__)"
# Expected: 1.24.x
```

### Problem: Email not sent

**Check 1**: Email backend (development)
```bash
docker exec rdl_backend python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_BACKEND)
# Expected: django.core.mail.backends.console.EmailBackend
```

**Check 2**: SMTP settings (production)
```bash
docker exec rdl_pdf_worker env | grep EMAIL
# Should show: EMAIL_HOST, EMAIL_PORT, etc.
```

### Problem: Token invalid/expired

**Check 1**: Token format
```bash
# Valid token format: pdf-{document_id}:{signature}
# Example: pdf-1:1h2j3k4l5m6n7o8p9q0r
```

**Check 2**: Secret key consistency
```bash
# Both Django and worker must use same SECRET_KEY
docker exec rdl_backend python -c "from django.conf import settings; print(settings.SECRET_KEY[:10])"
```

**Check 3**: Preview expiry
```bash
# Check document expiry in database
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, status, preview_expires_at, NOW() FROM documents_generateddocument WHERE id=1;"
```

---

## 📊 System Status Dashboard

### Quick Health Check
```bash
#!/bin/bash
echo "=== PDF System Health Check ==="

echo -n "Redis: "
docker exec rdl_redis redis-cli ping

echo -n "Worker: "
docker ps --filter name=pdf_worker --format "{{.Status}}"

echo -n "Database: "
docker exec rdl_postgres pg_isready -U postgres

echo -e "\n=== Recent Events ==="
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, status, generated_at FROM documents_generateddocument ORDER BY id DESC LIMIT 5;"

echo -e "\n=== Worker Last Activity ==="
docker logs rdl_pdf_worker --tail 5
```

Save as `check_pdf_system.sh` and run:
```bash
chmod +x check_pdf_system.sh
./check_pdf_system.sh
```

---

## 🎯 Production Checklist

Before deploying to production:

- [ ] Apply migrations to production database
- [ ] Configure real SMTP email backend
- [ ] Set strong SECRET_KEY (not 'dev-secret-key')
- [ ] Set PDF_PREVIEW_EXPIRY_SECONDS (default 24h)
- [ ] Configure Redis persistence or managed service
- [ ] Scale worker replicas (e.g., 2-3 instances)
- [ ] Set up monitoring alerts for worker failures
- [ ] Test email delivery with real addresses
- [ ] Verify PDF templates are included in worker image
- [ ] Configure CORS_ALLOWED_ORIGINS for production domain
- [ ] Set up log aggregation (e.g., CloudWatch, Datadog)

---

## 💡 Tips & Best Practices

### Development
1. Use console email backend to avoid SMTP setup
2. Monitor Redis channel to debug event flow
3. Keep worker logs open in separate terminal
4. Use `docker-compose logs -f` to see all services

### Testing
1. Test with minimal data first (1-2 records)
2. Verify token format before confirmation
3. Check expiry time is reasonable (24h default)
4. Test error cases (expired token, invalid token)

### Production
1. Use managed Redis service (not Docker)
2. Configure email retries in SMTP settings
3. Monitor worker CPU/memory usage
4. Set up dead letter queue for failed events (future)
5. Implement rate limiting on preview endpoint
6. Add PDF file size limits
7. Configure backup for generated PDFs

---

## 📚 Additional Resources

- **Full Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Architecture Plan**: See plan document from Phase 0
- **Django Docs**: https://docs.djangoproject.com/
- **Redis Pub/Sub**: https://redis.io/topics/pubsub
- **PyMuPDF**: https://pymupdf.readthedocs.io/

---

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker logs rdl_pdf_worker`
2. Check Redis: `docker exec -it rdl_redis redis-cli SUBSCRIBE pdf_events`
3. Check database: `SELECT * FROM documents_generateddocument;`
4. Verify environment variables in `docker-compose.yml`
5. Review `IMPLEMENTATION_SUMMARY.md` for detailed architecture

Common issues are documented in the Troubleshooting section above.
