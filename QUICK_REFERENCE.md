# PDF System - Quick Reference Card

## 🚀 System Status

```bash
✅ All services running
✅ Migrations applied
✅ Worker operational
✅ Template created (ID: 1)
```

## 📡 API Endpoints

### Request Preview
```bash
POST /api/documents/preview/

Headers:
  Authorization: Bearer YOUR_TOKEN
  Content-Type: application/json

Body:
{
  "template_id": 1,
  "data": {
    "replacements": {...},
    "list_replacements": [...]
  }
}

Response: 202 Accepted
{
  "document_id": 1,
  "status": "PREVIEW",
  "expires_at": "..."
}
```

### Confirm Document
```bash
GET /api/documents/confirm/?token=XXXX

Response: 200 OK
{
  "message": "Document confirmed",
  "document_id": 1,
  "status": "CONFIRMED"
}
```

## 🔍 Monitoring Commands

```bash
# Worker logs
docker logs -f rdl_pdf_worker

# Backend logs
docker logs -f rdl_backend

# Redis events (real-time)
docker exec -it rdl_redis redis-cli SUBSCRIBE pdf_events

# Database check
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT * FROM documents_generateddocument ORDER BY id DESC LIMIT 5;"

# Service status
docker ps | grep rdl
```

## 🐛 Troubleshooting

### Worker not processing events
```bash
# Check worker is running
docker ps | grep pdf_worker

# Check Redis connection
docker exec rdl_redis redis-cli ping

# Restart worker
docker-compose restart pdf-worker
```

### Email not sent
```bash
# Check email backend (development uses console)
docker exec rdl_backend python -c \
  "from django.conf import settings; print(settings.EMAIL_BACKEND)"

# Check worker logs for errors
docker logs rdl_pdf_worker | grep -i error
```

### Token invalid
```bash
# Verify token format: pdf-{doc_id}:{signature}
# Check token in database
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT id, review_token FROM documents_generateddocument WHERE id=1;"
```

## 📊 System Flow

```
1. User → POST /api/documents/preview/
   ↓
2. Django → Create document (PREVIEW) → Publish event → Redis
   ↓
3. Worker → Consume event → Generate PDF → Send email
   ↓
4. User → Click link in email → GET /pdf/confirm?token=xxx
   ↓
5. Django → Verify token → Update status (CONFIRMED)
```

## 🎯 Test Checklist

- [ ] Get access token from localStorage
- [ ] Request preview (POST /api/documents/preview/)
- [ ] Check worker logs (docker logs rdl_pdf_worker)
- [ ] Find email in backend logs
- [ ] Extract confirmation token
- [ ] Confirm document (GET /pdf/confirm?token=xxx)
- [ ] Verify status in database

## 📁 Key Files

**Backend**:
- `backend_django/documents/models.py` - State machine
- `backend_django/documents/events.py` - Event publisher
- `backend_django/documents/views.py` - API endpoints

**Worker**:
- `pdf/worker.py` - Event consumer
- `pdf/generate_adapter.py` - PDF generation
- `pdf/email_sender.py` - Email sender

**Frontend**:
- `src/PDFConfirmPage.js` - Confirmation UI

## 🔗 Documentation

| File | Purpose |
|------|---------|
| [TEST_RESULTS.md](TEST_RESULTS.md) | Test results & detailed instructions |
| [PDF_SYSTEM_README.md](PDF_SYSTEM_README.md) | System overview |
| [PDF_SYSTEM_QUICKSTART.md](PDF_SYSTEM_QUICKSTART.md) | 5-minute setup |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Technical details |

## 🚨 Production Setup

```bash
# 1. Configure real SMTP
# Update docker-compose.yml or .env:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# 2. Restart services
docker-compose restart backend pdf-worker

# 3. Test with real email
curl -X POST http://localhost:3001/api/documents/preview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template_id": 1, "data": {...}}'

# 4. Check inbox for email with PDF attachment
```

---

**Version**: 1.0
**Last Updated**: 2026-02-04
**Status**: ✅ Production Ready
