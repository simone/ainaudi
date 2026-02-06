# API URL Configuration Fix ✅

## Date: 2026-02-05

## Problem

Il frontend stava chiamando le API su `http://localhost:3000` (frontend stesso) invece di `http://localhost:3001` (backend Django), causando errori 404.

```
Request URL: http://localhost:3000/api/auth/magic-link/request/
Status Code: 404 Not Found
```

---

## Root Cause

**Conflitto tra URL assoluti e Vite proxy:**

1. Nel codice, `SERVER_API` era impostato a `http://localhost:3001`
2. Le chiamate usavano URL assoluti: `${SERVER_API}/api/...` → `http://localhost:3001/api/...`
3. **Ma** `vite.config.js` ha un proxy configurato:
   ```javascript
   proxy: {
     '/api': {
       target: 'http://localhost:3001',
       changeOrigin: true,
     },
   }
   ```
4. Il proxy di Vite funziona **solo con URL relativi** (`/api/...`), non con URL assoluti

**Risultato:** Le chiamate bypassavano il proxy e fallivano perché il frontend non aveva accesso diretto alla porta 3001 in alcuni contesti Docker.

---

## Solution

Usare **URL relativi** per sfruttare il proxy di Vite in development e same-origin in production.

### Modifiche

#### 1. App.js (linee 26-28)

**PRIMA:**
```javascript
const SERVER_API = import.meta.env.MODE === 'development' ? import.meta.env.VITE_API_URL : '';
const SERVER_PDF = import.meta.env.MODE === 'development' ? import.meta.env.VITE_PDF_URL : '';
```

**DOPO:**
```javascript
// In development, use empty string to leverage Vite proxy (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';
const SERVER_PDF = '';
```

#### 2. AuthContext.js (linea 6)

**PRIMA:**
```javascript
const SERVER_API = import.meta.env.MODE === 'development' ? import.meta.env.VITE_API_URL : '';
```

**DOPO:**
```javascript
// Use empty string to leverage Vite proxy in development (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';
```

#### 3. Altri 6 file aggiornati

Tutti i file con `VITE_API_URL` sono stati aggiornati:
- `ComuneAutocomplete.js`
- `PDFConfirmPage.js`
- `RdlSelfRegistration.js`
- `CampagnaRegistration.js`
- `SezzionePlessAutocomplete.js`
- `Risorse.js`

#### 4. Client.js - upload() method

**PRIMA:**
```javascript
const upload = async (url, formData, options = {}) => {
    return fetch(fullUrl, {
        method: 'POST',
        // ...
    });
};
```

**DOPO:**
```javascript
const upload = async (url, formData, method = 'POST') => {
    return fetch(fullUrl, {
        method: method,  // Supporta sia POST che PUT
        // ...
    });
};
```

#### 5. GestioneTemplate.js

**Modifiche:**
- Ora riceve `client` come prop invece di importare `Client` direttamente
- Usa `client.get()`, `client.upload()`, `client.delete()` con URL relativi
- Coerente con tutti gli altri componenti Gestione*

#### 6. docker-compose.yml

Rimosso `VITE_API_URL` environment variable (non più necessaria):

**PRIMA:**
```yaml
frontend:
  environment:
    - VITE_API_URL=http://localhost:3001
```

**DOPO:**
```yaml
frontend:
  # No VITE_API_URL needed - uses Vite proxy (see vite.config.js)
```

---

## How It Works Now

### Development (Docker Compose)

```
Frontend (localhost:3000)
   ↓
   /api/... (relative URL)
   ↓
Vite Proxy (vite.config.js)
   ↓
http://localhost:3001/api/... (backend Django)
```

**Esempio:**
```javascript
// Code
await client.get('/api/documents/templates/')

// Browser request
GET http://localhost:3000/api/documents/templates/

// Vite proxy forwards to
GET http://localhost:3001/api/documents/templates/
```

### Production (Build Served by Nginx/GAE)

```
Browser
   ↓
   /api/... (same-origin request)
   ↓
Same server handles both static files and API
```

**Esempio:**
```javascript
// Code
await client.get('/api/documents/templates/')

// Browser request (same origin)
GET https://yourdomain.com/api/documents/templates/
```

---

## Benefits

### ✅ Fixes

1. **404 errors resolved** - API calls now reach backend correctly
2. **Consistent behavior** - Same pattern in dev and production
3. **No environment variables needed** - Simpler configuration
4. **Docker networking simplified** - No need for cross-container direct access

### ✅ Architecture

- **Development**: Vite proxy handles routing automatically
- **Production**: Same-origin requests (standard pattern)
- **No hardcoded URLs**: All URLs are relative
- **CORS not needed**: Proxy in dev, same-origin in prod

---

## Testing

### 1. Check Magic Link Login

```bash
# Frontend should call:
POST /api/auth/magic-link/request/

# NOT:
POST http://localhost:3001/api/auth/magic-link/request/
```

### 2. Check Template Management

```bash
# Open browser console when accessing "Gestione Template"
# Network tab should show:
GET /api/documents/templates/
GET /api/documents/template-types/
GET /api/elections/

# All relative URLs, proxied by Vite
```

### 3. Verify Vite Proxy

In browser console, relative URLs should work:
```javascript
fetch('/api/elections/')
  .then(r => r.json())
  .then(console.log)
```

---

## vite.config.js Proxy Configuration

```javascript
server: {
  port: 3000,
  open: true,
  proxy: {
    '/api': {
      target: 'http://localhost:3001',
      changeOrigin: true,
    },
  },
}
```

**What it does:**
- Intercepts all requests to `/api/*`
- Forwards to `http://localhost:3001/api/*`
- Returns response to frontend
- Transparent to the browser (appears as same-origin)

---

## Checklist

- [✅] Removed all `VITE_API_URL` environment variable checks
- [✅] Updated all `SERVER_API` to empty string
- [✅] Fixed `GestioneTemplate.js` to use client prop
- [✅] Updated `Client.js` upload method to support PUT
- [✅] Removed environment variables from docker-compose.yml
- [✅] Build passes successfully
- [✅] Vite proxy configuration intact

---

## Production Deployment Notes

In production (e.g., Google App Engine):

1. **Build once:**
   ```bash
   npm run build
   ```

2. **Static files and API on same origin:**
   ```
   yourdomain.com/          → Serve build/index.html
   yourdomain.com/api/...   → Django backend
   ```

3. **No proxy needed** - Nginx/GAE routes `/api/*` to Django, everything else to static files

---

## Related Files

| File | Purpose |
|------|---------|
| `vite.config.js` | Proxy configuration |
| `src/App.js` | Main app with SERVER_API |
| `src/AuthContext.js` | Authentication with magic links |
| `src/Client.js` | API client with upload method |
| `src/GestioneTemplate.js` | Template management UI |
| `docker-compose.yml` | Development environment |

---

**Status:** ✅ Complete - All API calls now use relative URLs with Vite proxy
**Date:** 2026-02-05
**Build:** Successful (1.51s)
