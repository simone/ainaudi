# Event-Driven PDF Generation Implementation Summary

## ✅ Phase 1: Infrastructure (COMPLETED)

### Django Backend Changes

#### 1. Database Models Extended
- **File**: `backend_django/documents/models.py`
- **Changes**:
  - Added state machine to `GeneratedDocument` model:
    - `status` field: PREVIEW, CONFIRMED, EXPIRED, CANCELLED
    - `review_token` field: Signed token for confirmation
    - `preview_expires_at`: Preview expiry timestamp
    - `confirmed_at`: Confirmation timestamp
    - `confirmation_ip`: IP address of confirmer
    - `event_id`: Redis event ID for audit trail
  - Extended `Template` model with template editor fields:
    - `field_mappings`: Visual field mapping configuration
    - `loop_config`: Loop/pagination configuration
    - `merge_mode`: Single doc per record vs multi-page loop
  - Indexes added for performance on `review_token` and `status`

#### 2. Event Publisher Created
- **File**: `backend_django/documents/events.py` (NEW)
- **Functions**:
  - `get_redis_client()`: Redis connection factory
  - `publish_preview_pdf_and_email()`: Publishes PREVIEW_PDF_AND_EMAIL event
  - `publish_confirm_freeze()`: Publishes CONFIRM_FREEZE audit event (non-blocking)

#### 3. API Endpoints Added
- **File**: `backend_django/documents/views.py`
- **New Views**:
  - `RequestPDFPreviewView`: POST /api/documents/preview/
    - Creates document in PREVIEW state
    - Generates signed review token
    - Publishes event to Redis
    - Returns 202 Accepted with document ID and expiry
  - `ConfirmPDFView`: GET/POST /api/documents/confirm/?token=xxx
    - Verifies token signature
    - Checks expiry
    - Freezes document (PREVIEW → CONFIRMED)
    - Returns document URL for download
  - `TemplateEditorView`: GET/PUT /api/documents/templates/{id}/editor/
    - Admin-only template configuration
  - `TemplatePreviewView`: POST /api/documents/templates/{id}/preview/
    - Admin testing with test data

#### 4. URLs Updated
- **File**: `backend_django/documents/urls.py`
- **Routes Added**:
  - `/api/documents/preview/`
  - `/api/documents/confirm/`
  - `/api/documents/templates/<id>/editor/`
  - `/api/documents/templates/<id>/preview/`

#### 5. Settings Updated
- **File**: `backend_django/config/settings.py`
- **Configuration Added**:
  ```python
  REDIS_HOST = 'redis'
  REDIS_PORT = 6379
  REDIS_DB = 0
  REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
  REDIS_PDF_EVENT_CHANNEL = 'pdf_events'
  PDF_PREVIEW_EXPIRY_SECONDS = 86400  # 24 hours
  ```

#### 6. Dependencies Updated
- **File**: `backend_django/requirements.txt`
- **Added**: `redis>=5.0,<6.0`

#### 7. Migrations Created
- **File**: `backend_django/documents/migrations/0002_*.py`
- **Run**: `python manage.py migrate documents` (not executed yet)

---

## ✅ Phase 2: PDF Worker (COMPLETED)

### Worker Service

#### 1. Event Consumer Created
- **File**: `pdf/worker.py` (NEW)
- **Features**:
  - Subscribes to Redis `pdf_events` channel
  - Graceful shutdown handling (SIGINT, SIGTERM)
  - Event routing (PREVIEW_PDF_AND_EMAIL, CONFIRM_FREEZE)
  - Stateless processing (all context in event)
  - No retries (fail silently as per spec)

#### 2. PDF Generation Adapter
- **File**: `pdf/generate_adapter.py` (NEW)
- **Functions**:
  - `generate_pdf_from_template()`: Main entry point
  - `_generate_individual()`: Individual PDF (one page per record)
  - `_generate_summary()`: Summary PDF (multi-page with pagination)
  - `_apply_replacements()`: Text replacement logic
- **Reuses**: Existing PyMuPDF logic from `pdf/generate.py`

#### 3. Email Sender
- **File**: `pdf/email_sender.py` (NEW)
- **Features**:
  - HTML email with styled confirmation button
  - PDF attachment
  - Warning about 24h expiry and immutability
  - Plain text alternative
  - SMTP/TLS support

#### 4. Worker Dockerfile
- **File**: `pdf/Dockerfile.worker` (NEW)
- **Features**:
  - Based on Python 3.11-slim
  - Includes PyMuPDF system dependencies
  - Non-root user for security
  - Includes templates/ directory

#### 5. Dependencies Updated
- **File**: `pdf/requirements.txt`
- **Added**: `redis>=5.0,<6.0`

---

## ✅ Phase 3: Docker Configuration (COMPLETED)

### Docker Compose

#### 1. Worker Service Added
- **File**: `docker-compose.yml`
- **Service**: `pdf-worker`
  - Builds from `pdf/Dockerfile.worker`
  - Depends on Redis health check
  - Environment variables:
    - REDIS_HOST, REDIS_PORT, REDIS_PDF_EVENT_CHANNEL
    - EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

#### 2. Backend Environment Updated
- Added Redis connection variables:
  - REDIS_HOST=redis
  - REDIS_PORT=6379
  - REDIS_DB=0

#### 3. Redis Service
- Already present in docker-compose.yml
- Health check configured
- Used for event bus

---

## ✅ Phase 4: Frontend (COMPLETED)

### React Components

#### 1. PDF Confirmation Page
- **File**: `src/PDFConfirmPage.js` (NEW)
- **Features**:
  - Token-based confirmation (from URL query param)
  - Loading spinner
  - Success/error states
  - Download button for confirmed PDF
  - Styled with custom CSS

#### 2. Styles
- **File**: `src/PDFConfirmPage.css` (NEW)
- **Features**:
  - Loading spinner animation
  - Success/error alert boxes
  - Responsive layout
  - Info boxes with warnings

#### 3. App Integration
- **File**: `src/App.js`
- **Changes**:
  - Imported `PDFConfirmPage`
  - Added `showPdfConfirm` state
  - URL route detection for `/pdf/confirm`
  - Conditional rendering (similar to campagna pattern)

---

## 📋 Phase 5: Migration Path (TODO)

### Step 1: Apply Migrations
```bash
cd backend_django
python manage.py migrate documents
```

### Step 2: Build and Start Worker
```bash
docker-compose build pdf-worker
docker-compose up -d pdf-worker
```

### Step 3: Verify Worker
```bash
# Check worker logs
docker logs -f rdl_pdf_worker

# Should see:
# "PDF Worker started, listening on pdf_events"
```

### Step 4: Test Event Flow (Development)

#### A. Test with Console Email Backend
In development, emails are printed to console:

```bash
# Terminal 1: Watch Django logs
docker logs -f rdl_backend

# Terminal 2: Watch Worker logs
docker logs -f rdl_pdf_worker

# Terminal 3: Monitor Redis
docker exec -it rdl_redis redis-cli
> SUBSCRIBE pdf_events
```

#### B. Send Test Request
```bash
curl -X POST http://localhost:3001/api/documents/preview/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "data": {
      "replacements": {
        "COGNOME E NOME SUBDELEGATO": "Mario Rossi"
      },
      "list_replacements": []
    }
  }'
```

Expected flow:
1. Django: Event published to Redis ✓
2. Worker: Event received ✓
3. Worker: PDF generated ✓
4. Worker: Email sent (console output) ✓
5. Check email console output for confirmation link

#### C. Test Confirmation
Copy token from email console output, then:
```bash
curl http://localhost:3001/api/documents/confirm/?token=XXXX
```

Expected:
```json
{
  "message": "Document confirmed",
  "document_id": 1,
  "status": "CONFIRMED",
  "confirmed_at": "2026-02-04T...",
  "pdf_url": null
}
```

### Step 5: Production Email Configuration

#### Update Backend Environment
```env
# backend_django/.env or docker-compose.yml
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@m5s.it
```

#### Update Worker Environment
```env
# docker-compose.yml or pdf worker env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### Test Production Email
1. Request preview with real email
2. Check inbox for confirmation email
3. Click "Conferma" button in email
4. Verify document status = CONFIRMED

---

## 🔄 Migrating Existing PDF Generation (OPTIONAL)

### Current Implementation (Legacy)
- Uses Flask PDF server directly
- Synchronous download
- No preview/confirmation

### New Implementation (Event-Driven)
- Uses Django + Redis + Worker
- Asynchronous with email
- Preview with human confirmation

### Migration Example: GeneraModuli.js

**Before (Direct Download)**:
```javascript
const handleSubmitIndividuale = async (e) => {
    e.preventDefault();
    const formDataToSend = new FormData();
    formDataToSend.append('excel', excelFile);
    formDataToSend.append('replacements', JSON.stringify(formData));

    client.pdf.generate(formDataToSend, 'single').then((response) => {
        const url = window.URL.createObjectURL(new Blob([response]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'document.pdf');
        document.body.appendChild(link);
        link.click();
        link.remove();
    });
};
```

**After (Event-Driven with Preview)**:
```javascript
const handleRequestPreview = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
        // Parse Excel to get list_replacements (existing logic)
        const list_replacements = await parseExcelFile(excelFile);

        const response = await client.post('/api/documents/preview/', {
            template_id: 1,  // Get from backend or map to template name
            data: {
                replacements: formData,
                list_replacements: list_replacements
            }
        });

        setSuccess(`Preview richiesta! Controlla la tua email. Doc ID: ${response.document_id}`);
    } catch (err) {
        setError(err.message);
    } finally {
        setLoading(false);
    }
};
```

**UI Changes**:
```jsx
<button onClick={handleRequestPreview} disabled={loading}>
    {loading ? 'Invio richiesta...' : 'Richiedi Preview PDF'}
</button>
{success && <div className="alert alert-success">{success}</div>}
```

---

## 🎨 Template Editor (Phase 6 - OPTIONAL)

The template editor allows admins to visually configure PDF templates without code changes.

### Features
- Upload base PDF template
- Click to define field areas with JSONPath
- Configure loops for stampa unione
- Test with sample data
- No code deployment needed for template changes

### Implementation Status
- ✅ Backend models extended
- ✅ Backend API endpoints created
- ⏳ Frontend editor UI (documented but not implemented)

### Implementation Guide
See plan document for:
- `TemplateEditor.js` component with PDF.js
- `query_builder.py` for JSONPath → Django ORM
- Visual field mapping workflow

---

## 📊 System Architecture

### Event Flow
```
User → Django API → Redis Pub/Sub → Worker → Email → User
                                              ↓
                                         Generate PDF
```

### State Machine
```
PREVIEW (reversible) → CONFIRM (user action) → CONFIRMED (immutable)
                    ↘ EXPIRED (24h timeout)
                    ↘ CANCELLED (user action)
```

### Key Design Decisions

1. **Human-in-the-Loop**: No automatic finalization
2. **Two-Phase Freeze**: Preview is mutable, Confirmed is immutable
3. **Self-Contained Events**: No database lookups in worker
4. **No Retries**: Fail silently, user can retry from UI
5. **Token-Based Auth**: Confirmation link uses signed tokens
6. **Audit Trail**: Event IDs tracked for debugging

---

## 🔍 Verification Checklist

### Backend
- [ ] Migrations applied successfully
- [ ] Redis connection works (check Django logs)
- [ ] Event publishing works (monitor Redis channel)
- [ ] API endpoints return 202 Accepted
- [ ] Tokens are generated correctly

### Worker
- [ ] Worker starts without errors
- [ ] Subscribes to correct channel
- [ ] Receives and processes events
- [ ] Generates PDF successfully
- [ ] Sends email (console or SMTP)

### Frontend
- [ ] `/pdf/confirm?token=xxx` route works
- [ ] Confirmation page renders
- [ ] Success/error states work
- [ ] Download button appears (if PDF URL set)

### End-to-End
- [ ] Request preview → Event published
- [ ] Worker receives event → PDF generated
- [ ] Email sent → User receives email
- [ ] Click confirm link → Document confirmed
- [ ] Second confirmation → Returns "Already confirmed"
- [ ] Expired token → Returns 410 Gone

---

## 🚀 Deployment Notes

### Development
- Email backend: Console (prints to logs)
- Redis: Docker container
- Worker: Docker container
- No external dependencies

### Production
- Email backend: SMTP (Gmail, SendGrid, etc.)
- Redis: Managed service (AWS ElastiCache, GCP Memorystore)
- Worker: Multiple replicas for high availability
- Monitor worker logs for errors

### Monitoring
- **Django**: Check event publishing success rate
- **Redis**: Monitor channel activity (`redis-cli MONITOR`)
- **Worker**: Check logs for processing errors
- **Database**: Track document status distribution

### Troubleshooting
- **Event not received**: Check Redis connection, channel name
- **PDF generation fails**: Check PyMuPDF dependencies, template files
- **Email not sent**: Check SMTP credentials, firewall
- **Token invalid**: Check `SECRET_KEY` consistency, expiry time

---

## 📁 Files Changed/Created

### Backend Django
- ✅ `backend_django/documents/models.py` (modified)
- ✅ `backend_django/documents/events.py` (created)
- ✅ `backend_django/documents/views.py` (modified)
- ✅ `backend_django/documents/urls.py` (modified)
- ✅ `backend_django/config/settings.py` (modified)
- ✅ `backend_django/requirements.txt` (modified)
- ✅ `backend_django/.env.example` (modified)
- ✅ `backend_django/documents/migrations/0002_*.py` (created)

### PDF Worker
- ✅ `pdf/worker.py` (created)
- ✅ `pdf/generate_adapter.py` (created)
- ✅ `pdf/email_sender.py` (created)
- ✅ `pdf/Dockerfile.worker` (created)
- ✅ `pdf/requirements.txt` (modified)

### Infrastructure
- ✅ `docker-compose.yml` (modified)

### Frontend
- ✅ `src/PDFConfirmPage.js` (created)
- ✅ `src/PDFConfirmPage.css` (created)
- ✅ `src/App.js` (modified)

---

## 🎯 Next Steps

1. **Apply migrations**: `python manage.py migrate documents`
2. **Start worker**: `docker-compose up -d pdf-worker`
3. **Test event flow**: Use curl or Postman
4. **Configure production email**: Update SMTP settings
5. **Migrate GeneraModuli**: Replace direct download with preview flow
6. **Optional**: Implement template editor UI
7. **Optional**: Add PDF storage (GCS, S3) for confirmed documents

---

## 📝 Notes

- Legacy `GeneratePDFView` kept for backwards compatibility
- Flask PDF server still operational (legacy path)
- Template editor backend ready, frontend optional
- Worker is stateless and horizontally scalable
- No breaking changes to existing functionality

