# 📧 Sistema Invio Email RDL - Implementazione Completa

## ✅ Stato: PRONTO PER TESTING

### Configurazione Attuale

```
✅ Backend: Console (solo log, nessun invio reale)
✅ Redis: Attivo per progress tracking
✅ Database: Migrations applicate
✅ Frontend: UI con progress bar implementata
✅ Logging: Dettagliato con emoji e sezioni
```

---

## 🚀 Quick Start Testing

### 1. Avvia l'applicazione

```bash
docker-compose up -d
```

### 2. Verifica servizi

```bash
# Verifica email backend console
docker-compose exec backend python manage.py shell -c "
from django.conf import settings
print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
"

# Verifica Redis
docker-compose exec redis redis-cli ping
# Output atteso: PONG
```

### 3. Test dall'interfaccia web

1. Apri http://localhost:3000
2. Login (Magic Link)
3. Naviga a **Gestione Designazioni**
4. Seleziona un comune con designazioni
5. Espandi un processo **APPROVATO**
6. Click **"Invia Email agli RDL"**
7. Osserva progress bar in tempo reale

### 4. Monitora i logs

```bash
# In un terminale separato
docker-compose logs -f backend | grep "📧"
```

**Output atteso**:
```
================================================================================
📧 INVIO EMAIL RDL - Processo #1
================================================================================
Destinatario: Mario Rossi <mario.rossi@example.com>
Tipo RDL: EFFETTIVO
Consultazione: Referendum 2025
Totale sezioni: 3
  🟢 Sezioni come EFFETTIVO (3):
     - Sez. 1: Via Roma 1, Roma
     - Sez. 2: Via Milano 2, Roma
     - Sez. 3: Via Napoli 3, Roma
Subject: Conferma Designazione RDL - Referendum 2025
From: AINAUDI (M5S) - Simone Federici <s.federici@gmail.com>
Backend EMAIL: django.core.mail.backends.console.EmailBackend
================================================================================
✅ Email inviata con successo a mario.rossi@example.com (EFFETTIVO)
```

---

## 📁 File Implementati

### Backend

```
backend_django/
├── config/
│   └── settings.py                    # Redis client + EMAIL_BACKEND
├── delegations/
│   ├── models.py                      # EmailDesignazioneLog + campi tracking
│   ├── serializers.py                 # Campi email in ProcessoDesignazioneSerializer
│   ├── admin.py                       # EmailDesignazioneLogAdmin
│   ├── views_processo.py              # 3 nuovi endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── email_service.py          # RDLEmailService (asincrono + Redis)
│   │   └── pdf_extraction_service.py # PDFExtractionService (con cache)
│   └── migrations/
│       └── 0022_processodesignazione_email_inviate_at_and_more.py
└── templates/
    └── delegations/
        └── email/
            ├── notifica_rdl.html      # Template HTML M5S style
            └── notifica_rdl.txt       # Fallback plain text
```

### Frontend

```
src/
└── GestioneDesignazioni.js            # UI + handlers invio email
```

### Infrastruttura

```
docker-compose.yml                      # Redis service + env vars
requirements.txt                        # redis>=4.5.0
.env                                   # EMAIL_BACKEND=console
```

### Testing & Docs

```
backend_django/test_email_rdl.py       # Script test CLI
TESTING_EMAIL_RDL.md                   # Guida testing completa
README_EMAIL_RDL.md                    # Questo file
```

---

## 🔧 API Endpoints

### 1. Invia Email (Asincrono)

```http
POST /api/deleghe/processi/{id}/invia-email/
Authorization: Bearer {token}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "message": "Invio email avviato in background",
  "task_id": "email_task_1_abc123",
  "n_designazioni": 150
}
```

### 2. Progress Tracking

```http
GET /api/deleghe/processi/{id}/email-progress/
Authorization: Bearer {token}
```

**Response**:
```json
{
  "status": "PROGRESS",
  "current": 50,
  "total": 100,
  "sent": 48,
  "failed": 2,
  "percentage": 50
}
```

### 3. Download Nomina RDL

```http
GET /api/deleghe/processi/download-mia-nomina/?consultazione_id=1
Authorization: Bearer {token}
```

**Response**: PDF file (inline)

---

## 🎨 UI Features

### Bottone Invio Email

- ✅ Visibile solo per processi APPROVATO
- ✅ Disabilitato se già inviate
- ✅ Conferma prima dell'invio
- ✅ Spinner durante elaborazione
- ✅ Progress bar con percentuale
- ✅ Contatore "Invio X/Y..."
- ✅ Alert di successo/errore

### Info Email Inviate

```
✅ Email inviate il 11/02/2026 alle 10:45
   96 inviate, 4 fallite
```

---

## 📊 Database Schema

### EmailDesignazioneLog

```sql
CREATE TABLE delegations_emaildesignazionelog (
    id SERIAL PRIMARY KEY,
    processo_id INTEGER NOT NULL REFERENCES delegations_processodesignazione,
    designazione_id INTEGER REFERENCES delegations_designazionerdl,
    destinatario_email VARCHAR(254) NOT NULL,
    destinatario_nome VARCHAR(200) NOT NULL,
    tipo_rdl VARCHAR(30) NOT NULL,  -- EFFETTIVO / SUPPLENTE / EFFETTIVO+SUPPLENTE
    stato VARCHAR(20) DEFAULT 'SUCCESS',  -- SUCCESS / FAILED / BOUNCED
    errore TEXT,
    subject VARCHAR(500),
    sent_at TIMESTAMP DEFAULT NOW(),
    sent_by_email VARCHAR(254)
);
```

### ProcessoDesignazione (nuovi campi)

```sql
ALTER TABLE delegations_processodesignazione ADD COLUMN
    email_inviate_at TIMESTAMP NULL,
    email_inviate_da VARCHAR(254),
    n_email_inviate INTEGER DEFAULT 0,
    n_email_fallite INTEGER DEFAULT 0;
```

---

## 🔄 Workflow Completo

```
1. Delegato completa designazioni → stato APPROVATO
                ↓
2. Click "Invia Email agli RDL"
                ↓
3. Backend avvia thread asincrono
                ↓
4. Redis salva task progress
                ↓
5. Per ogni email unica:
   - Raggruppa sezioni per ruolo (effettivo/supplente)
   - Render template HTML + text
   - send_mail() → console backend (log)
   - Salva EmailDesignazioneLog
   - Rate limiting: 0.2s sleep
   - Aggiorna progress in Redis
                ↓
6. Frontend polling ogni 2s
                ↓
7. Progress bar si aggiorna
                ↓
8. Completamento:
   - Processo → stato INVIATO
   - Alert di successo
   - Badge "Email inviate"
```

---

## ⚠️ Note Importanti

### Raggruppamento Email

Un RDL può avere **doppio ruolo**:
- Effettivo per sezioni 1, 2, 3
- Supplente per sezioni 4, 5, 6

**Comportamento**:
- ✅ Riceve **1 sola email**
- ✅ Email mostra **entrambe le liste**
- ✅ PDF contiene **tutte le 6 sezioni**

### Rate Limiting

- **Default**: 5 email/secondo (0.2s sleep)
- **Consigliato prod**: 2 email/secondo (0.5s sleep)
- **Provider SMTP**: Verificare limiti specifici

### Cache PDF

- **Storage**: `media/pdf_cache/`
- **TTL Redis**: 7 giorni
- **Cleanup**: Manuale (TODO: management command)

---

## 🐛 Troubleshooting

### Email non loggano

```bash
# Verifica backend
docker-compose exec backend python manage.py shell -c "
from django.conf import settings
print(settings.EMAIL_BACKEND)
"
# Deve essere: django.core.mail.backends.console.EmailBackend
```

### Progress bloccato

```bash
# Pulisci Redis
docker-compose exec redis redis-cli flushdb
```

### Django non vede Redis

```bash
# Riavvia backend
docker-compose restart backend
```

---

## 📚 Documentazione Completa

- **Testing Guide**: `TESTING_EMAIL_RDL.md`
- **Piano Implementazione**: Vedi transcript plan mode
- **Email Templates**: `backend_django/templates/delegations/email/`

---

## 🚦 Next Steps

### Fase 1: Testing Locale ✅
- [x] Console backend configurato
- [x] Logging dettagliato
- [x] UI completa
- [ ] Test con dati reali

### Fase 2: Staging
- [ ] Configurare SMTP (SendGrid/Gmail)
- [ ] Test con 10-20 email reali
- [ ] Verifica deliverability (no spam)
- [ ] Test template su diversi client

### Fase 3: Produzione
- [ ] Configurare PEC (opzionale)
- [ ] Rate limiting ottimale
- [ ] Monitoring errori
- [ ] Backup pre-invio

---

## 📞 Supporto

**Domande?** Consulta:
- `TESTING_EMAIL_RDL.md` per guide dettagliate
- Django logs: `docker-compose logs backend`
- Redis monitor: `docker-compose exec redis redis-cli monitor`

**Pronto per i test!** 🎉
