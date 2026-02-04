# Event-Driven PDF Generation System

A robust, scalable PDF generation system with human-in-the-loop confirmation for the AInaudi electoral management platform.

## 🎯 Overview

This system implements a **two-phase** PDF generation workflow:

1. **PREVIEW Phase**: User requests PDF → System generates → Email sent with preview attachment
2. **CONFIRM Phase**: User reviews → Clicks confirmation link → Document becomes immutable

### Key Features

- ✅ **Event-Driven Architecture**: Redis Pub/Sub for decoupled processing
- ✅ **Human Confirmation**: No automatic finalization, user must approve
- ✅ **Stateless Worker**: Horizontally scalable, all context in events
- ✅ **Audit Trail**: Full event tracking for debugging and compliance
- ✅ **Token-Based Security**: Signed tokens with expiry (24h default)
- ✅ **Email Integration**: HTML emails with PDF attachment and confirmation button
- ✅ **State Machine**: PREVIEW → CONFIRMED/EXPIRED/CANCELLED
- ✅ **Template System**: Admin-configurable PDF templates (optional)

## 📁 Documentation

| Document | Purpose |
|----------|---------|
| **[Quick Start Guide](PDF_SYSTEM_QUICKSTART.md)** | Get up and running in 5 minutes |
| **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** | Complete technical details and architecture |
| **[Test Script](test_pdf_system.sh)** | Automated end-to-end testing |
| This README | High-level overview and navigation |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for Django)
- Node.js 18+ (for React)

### 1. Apply Migrations
```bash
cd backend_django
python manage.py migrate documents
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Run Tests
```bash
# Set your access token (get from browser localStorage after login)
export ACCESS_TOKEN="your-jwt-token-here"

# Run integration test
./test_pdf_system.sh
```

**Expected Result**: All checks pass ✓

See [Quick Start Guide](PDF_SYSTEM_QUICKSTART.md) for detailed instructions.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
│                     (React Frontend - port 3000)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP POST /api/documents/preview/
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Django Backend                            │
│                         (port 3001)                              │
│                                                                   │
│  1. Create GeneratedDocument (status=PREVIEW)                   │
│  2. Generate review_token (signed)                               │
│  3. Publish event to Redis                                       │
└────────────────┬────────────────────────────┬────────────────────┘
                 │                             │
                 │ Event (JSON)                │ State Storage
                 ▼                             ▼
┌─────────────────────────────┐  ┌────────────────────────────────┐
│     Redis Pub/Sub           │  │     PostgreSQL                 │
│    (pdf_events channel)     │  │  documents_generateddocument   │
└────────────┬────────────────┘  └────────────────────────────────┘
             │
             │ PREVIEW_PDF_AND_EMAIL event
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        PDF Worker                                │
│                    (Python + PyMuPDF)                            │
│                                                                   │
│  1. Consume event from Redis                                     │
│  2. Generate PDF (templates/individuale.pdf)                     │
│  3. Send email with attachment + confirmation link               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              │ Email (HTML + PDF)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                            User                                  │
│                                                                   │
│  1. Receive email                                                │
│  2. Review PDF attachment                                        │
│  3. Click "Conferma" button                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ GET /pdf/confirm?token=xxx
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django Backend                                │
│                                                                   │
│  1. Verify token signature                                       │
│  2. Check expiry                                                 │
│  3. Update status: PREVIEW → CONFIRMED                           │
│  4. Record confirmation timestamp & IP                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Workflow Example

### User Journey

1. **Request**: User fills form, uploads Excel, clicks "Richiedi Preview PDF"
   ```javascript
   POST /api/documents/preview/
   → 202 Accepted { document_id: 1, expires_at: "..." }
   ```

2. **Processing**: Worker generates PDF (takes 2-5 seconds)
   - Reads Excel data
   - Fills PDF template with data
   - Generates one PDF per record

3. **Email**: User receives email with:
   - PDF attachment (preview)
   - Green "Conferma" button
   - Warning about 24h expiry

4. **Review**: User opens PDF, verifies data is correct

5. **Confirm**: User clicks button in email
   ```
   GET /pdf/confirm?token=pdf-1:SIGNATURE
   → 200 OK { status: "CONFIRMED", pdf_url: "..." }
   ```

6. **Done**: Document is now immutable and available for download

### Error Cases

- **Expired Token**: User gets 410 Gone
- **Invalid Token**: User gets 400 Bad Request
- **Already Confirmed**: User gets 200 OK with existing data
- **PDF Generation Failed**: Worker logs error, user can retry

## 🧪 Testing

### Manual Test
```bash
# 1. Request preview
curl -X POST http://localhost:3001/api/documents/preview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template_id": 1, "data": {...}}'

# 2. Check worker logs
docker logs rdl_pdf_worker

# 3. Get token from database
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT review_token FROM documents_generateddocument WHERE id=1;"

# 4. Confirm
curl "http://localhost:3001/api/documents/confirm/?token=TOKEN_HERE"
```

### Automated Test
```bash
export ACCESS_TOKEN="your-token"
./test_pdf_system.sh
```

See [Quick Start Guide](PDF_SYSTEM_QUICKSTART.md) for detailed testing instructions.

## 📊 Monitoring

### Health Checks
```bash
# Quick status
docker ps | grep rdl

# Worker health
docker logs rdl_pdf_worker --tail 20

# Redis events (real-time)
docker exec -it rdl_redis redis-cli SUBSCRIBE pdf_events

# Database status
docker exec rdl_postgres psql -U postgres -d rdl_referendum -c \
  "SELECT status, COUNT(*) FROM documents_generateddocument GROUP BY status;"
```

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Preview Request Rate | Requests/hour to /api/documents/preview/ | Sudden spike |
| Worker Processing Time | Event received → Email sent | > 30 seconds |
| Confirmation Rate | Confirmed / Total Previews | < 70% |
| Expiry Rate | Expired / Total Previews | > 20% |
| Worker Error Rate | Failed events / Total events | > 5% |

## 🔧 Configuration

### Environment Variables

#### Django Backend
```env
# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# PDF Preview
PDF_PREVIEW_EXPIRY_SECONDS=86400  # 24 hours

# Email (development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Email (production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@m5s.it
```

#### PDF Worker
```env
# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PDF_EVENT_CHANNEL=pdf_events

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=true
```

### Scaling

#### Development
- 1 worker instance
- Redis in Docker
- Console email backend

#### Production
- 2-3 worker instances (horizontal scaling)
- Managed Redis (AWS ElastiCache, GCP Memorystore)
- Real SMTP email backend
- Load balancer for Django

**To scale workers**:
```bash
docker-compose up -d --scale pdf-worker=3
```

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Worker not receiving events | Check Redis connection, channel name |
| PDF generation fails | Check template files exist, PyMuPDF installed |
| Email not sent | Check SMTP credentials, firewall rules |
| Token invalid | Check SECRET_KEY consistency, token expiry |
| Preview expired | Increase PDF_PREVIEW_EXPIRY_SECONDS |

See [Quick Start Guide - Troubleshooting](PDF_SYSTEM_QUICKSTART.md#-troubleshooting) for detailed solutions.

## 🎨 Template System (Optional)

The system includes an admin-only template editor for visual PDF configuration:

- Upload base PDF template
- Click to define field areas
- Configure loops for multi-record documents
- Test with sample data
- No code deployment needed

**Status**: Backend ready, frontend UI optional

See [Implementation Summary - Template Editor](IMPLEMENTATION_SUMMARY.md#-template-editor-phase-6---optional) for details.

## 🔐 Security

- **Token Signing**: Uses Django's TimestampSigner (same as magic link)
- **Expiry**: 24h default, configurable
- **No Replay**: Second confirmation returns "Already confirmed"
- **IP Tracking**: Confirmation IP stored for audit
- **No Sensitive Data**: Emails don't include personal data, only link

## 📈 Performance

### Benchmarks (Local Docker)

- Preview Request: < 100ms (just DB + Redis publish)
- PDF Generation: 2-5s (depends on page count)
- Email Send: 1-2s (SMTP) or instant (console)
- Confirmation: < 50ms (DB update only)

### Bottlenecks

- PDF generation (CPU-bound) → Scale workers
- Email sending (I/O-bound) → Use async email backend
- Redis Pub/Sub → Very fast, not a bottleneck

## 🚀 Deployment

### Docker Compose (Recommended)
```bash
docker-compose up -d
```

### Kubernetes (Advanced)
```yaml
# pdf-worker deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: rdl-pdf-worker:latest
        env:
        - name: REDIS_HOST
          value: redis-service
```

See [Implementation Summary - Deployment](IMPLEMENTATION_SUMMARY.md#-deployment-notes) for production checklist.

## 📝 API Reference

### POST /api/documents/preview/
Request PDF preview with email confirmation.

**Request**:
```json
{
  "template_id": 1,
  "data": {
    "replacements": {"key": "value"},
    "list_replacements": [{"key": "value"}]
  },
  "email_to": "user@example.com"  // optional
}
```

**Response** (202 Accepted):
```json
{
  "message": "Preview request queued. Check your email.",
  "document_id": 1,
  "status": "PREVIEW",
  "expires_at": "2026-02-05T12:00:00Z"
}
```

### GET /api/documents/confirm/?token=xxx
Confirm and freeze document.

**Response** (200 OK):
```json
{
  "message": "Document confirmed",
  "document_id": 1,
  "status": "CONFIRMED",
  "confirmed_at": "2026-02-04T12:30:00Z",
  "pdf_url": "https://storage.googleapis.com/..."
}
```

**Errors**:
- 400: Invalid token
- 410: Preview expired
- 404: Document not found

## 🤝 Contributing

When modifying the PDF system:

1. Update models? → Create migration
2. Change event format? → Update both publisher and consumer
3. New template? → Add to `pdf/templates/` directory
4. Update docs? → Modify relevant markdown files

## 📚 Further Reading

- [Django Signals for Auto-Provisioning](backend_django/delegations/signals.py)
- [Magic Link Authentication Pattern](backend_django/core/views.py)
- [Existing PDF Generation Logic](pdf/generate.py)
- [Docker Compose Configuration](docker-compose.yml)

## 📞 Support

For issues or questions:

1. Check [Quick Start Guide](PDF_SYSTEM_QUICKSTART.md#-troubleshooting)
2. Review [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
3. Check worker logs: `docker logs rdl_pdf_worker`
4. Monitor Redis: `docker exec -it rdl_redis redis-cli SUBSCRIBE pdf_events`

---

**Status**: ✅ Phase 1-4 Complete | ⏳ Phase 5 (Testing) Pending | 🎨 Phase 6 (Template Editor UI) Optional

**Last Updated**: 2026-02-04
