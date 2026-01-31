# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RDL (Responsabile Di Lista) is an election data collection web application for Movimento 5 Stelle during the 2024 European elections. It collects voting data from electoral sections, manages user assignments, displays KPI dashboards, and generates PDF nomination forms.

## Development Commands

```bash
# Install all dependencies
npm install
cd backend && npm install && cd ..
cd pdf && pip install -r requirements.txt && cd ..

# Run all services (backend:3001, pdf:8000, frontend:3000)
npm run dev

# Individual services
npm run frontend    # React dev server
npm run backend     # Node.js API server with nodemon
npm run pdf         # Python Flask PDF server

# Production build and deploy
npm run build       # Build React for production
npm run deploy      # Deploy frontend + backend to GAE
cd pdf && gcloud app deploy && cd ..  # Deploy PDF service
gcloud app deploy dispatch.yaml       # Deploy routing rules

# Tests
npm test            # Run React tests (jest/jsdom)
```

## Architecture

**Three-service microservices architecture deployed on Google App Engine:**

1. **React Frontend** (`src/`) - Single-page app with Google OAuth authentication
2. **Node.js Backend** (`backend/`) - Express API server that queries Google Sheets as database
3. **Python PDF Service** (`pdf/`) - Flask server using PyMuPDF for PDF generation

**Data Flow:**
- Frontend authenticates via Google OAuth2, sends ID token in Authorization header
- Backend verifies tokens and reads/writes to Google Sheets (ID: `1ZbPPXzjIiSq-1J0MjQYYjxY-ZuTwR3tDmCvcYgORabY`)
- PDF generation requests go to Python service via `/api/generate/*` routes
- Both backend services independently verify Google OAuth tokens

**Key Backend Modules** (`backend/modules/`):
- `section.js` - Electoral section CRUD operations
- `rdl.js` - User assignment management
- `kpi.js` - Data aggregation for dashboards
- `election.js` - Candidate/list data

**Caching:**
- Client-side: Map-based cache in `Client.js`
- Server-side: NodeCache with 60s TTL for data, 120s for permissions
- Rate limiting: 120 requests per 120 seconds per IP

**Permission Model:** Three levels (sections, referenti, kpi) determined by Google Sheets row matching user email.

## Environment Variables

Development `.env`:
```
REACT_APP_API_URL=http://localhost:3001
REACT_APP_PDF_URL=http://localhost:8000
```

## Deployment

- **Main service** (Node.js 18): `app.yaml` - serves React build + API
- **PDF service** (Python 3.9): `pdf/app.yaml` - handles `/api/generate/*`
- **Routing**: `dispatch.yaml` directs traffic between services
