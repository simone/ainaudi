# Testing Invio Email RDL

## 🔧 Configurazione Testing (Console Backend)

Il sistema è configurato per **NON inviare email reali** in ambiente di sviluppo. Le email vengono loggate in console.

### Configurazione Attiva

**File**: `docker-compose.yml`
```yaml
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Comportamento**:
- ✅ Nessun invio SMTP reale
- ✅ Email loggate in console Django
- ✅ Log dettagliati con sezioni e ruoli RDL
- ✅ Audit trail completo in database

---

## 🧪 Come Testare

### Opzione 1: Tramite Interfaccia Web (Consigliato)

1. **Accedi all'applicazione**:
   ```bash
   # Apri browser
   http://localhost:3000
   ```

2. **Naviga a Gestione Designazioni**:
   - Seleziona consultazione attiva
   - Naviga fino a un comune con designazioni

3. **Visualizza processo APPROVATO**:
   - Nell'archivio, espandi un processo completato
   - Verifica che ci siano designazioni confermate

4. **Invia email test**:
   - Click su "Invia Email agli RDL"
   - Conferma nel dialog
   - Osserva progress bar in tempo reale

5. **Verifica logs**:
   ```bash
   # In un altro terminale
   docker-compose logs -f backend
   ```

   Vedrai output simile a:
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

### Opzione 2: Script di Test Backend

```bash
# Lista processi disponibili
docker-compose exec backend python test_email_rdl.py

# Test specifico processo
docker-compose exec backend python test_email_rdl.py 1
```

**Output script**:
```
================================================================================
🧪 TEST INVIO EMAIL - Processo #1
================================================================================
Consultazione: Referendum 2025
Stato: APPROVATO
N. Designazioni: 150
================================================================================

🚀 Avvio invio email asincrono...
✅ Task avviato: email_task_1_abc123

📊 Monitoraggio progress...
Status: PROGRESS | Progress: 50/100 | Sent: 48 | Failed: 2
Status: PROGRESS | Progress: 100/100 | Sent: 96 | Failed: 4

✅ Invio completato!
📧 Email inviate: 96
❌ Email fallite: 4

================================================================================
✅ Test completato
================================================================================

📋 Ultimi 10 log email:
  ✅ mario.rossi@example.com (EFFETTIVO) - 10:45:23
  ✅ laura.bianchi@example.com (SUPPLENTE) - 10:45:23
  ✅ giovanni.verdi@example.com (EFFETTIVO+SUPPLENTE) - 10:45:22
  ...
```

### Opzione 3: Django Admin

1. **Accedi all'admin**:
   ```
   http://localhost:3001/admin/
   ```

2. **Naviga a**:
   ```
   Delegations > Email designazione logs
   ```

3. **Verifica**:
   - Elenco completo email inviate
   - Filtri per stato (SUCCESS/FAILED)
   - Dettagli errori per email fallite
   - Timestamp invio

---

## 📊 Monitoraggio Redis

```bash
# Verifica task attivi
docker-compose exec redis redis-cli keys "email_task_*"

# Dettagli task
docker-compose exec redis redis-cli hgetall "email_task_1_abc123"

# Cache PDF (se usata)
docker-compose exec redis redis-cli keys "pdf_nomina:*"
```

---

## 🔄 Passaggio a Invio Reale (Produzione)

Quando sei pronto per inviare email reali:

### Modifica `docker-compose.yml`:

```yaml
environment:
  - EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
  - EMAIL_HOST=smtp.gmail.com
  - EMAIL_PORT=587
  - EMAIL_USE_TLS=True
  - EMAIL_HOST_USER=your-email@gmail.com
  - EMAIL_HOST_PASSWORD=your-app-password
```

### O usa `.env`:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Riavvia:

```bash
docker-compose restart backend
```

---

## ⚠️ Checklist Pre-Produzione

Antes de activar email reali:

- [ ] Verifica credenziali SMTP valide
- [ ] Test con 1-2 email reali (tua email)
- [ ] Verifica che email non finiscano in spam (SPF/DKIM)
- [ ] Configura rate limiting SMTP provider
- [ ] Verifica template HTML su diversi client (Gmail, Outlook)
- [ ] Test caso doppio ruolo (effettivo + supplente)
- [ ] Verifica handling errori SMTP
- [ ] Backup database prima di invio massivo
- [ ] Monitora logs durante primo invio reale

---

## 🐛 Troubleshooting

### Email non compaiono nei logs

```bash
# Verifica backend configurato
docker-compose exec backend printenv EMAIL_BACKEND

# Deve ritornare:
# django.core.mail.backends.console.EmailBackend
```

### Progress non aggiorna

```bash
# Verifica Redis funzionante
docker-compose exec redis redis-cli ping
# Deve ritornare: PONG

# Verifica connessione backend->redis
docker-compose exec backend python -c "import redis; r = redis.Redis(host='redis', port=6379); print(r.ping())"
# Deve ritornare: True
```

### Task bloccato

```bash
# Pulisci task Redis
docker-compose exec redis redis-cli del "email_task_1_abc123"
docker-compose exec redis redis-cli del "email_task_current_1"
```

---

## 📝 Note Sviluppatori

### Rate Limiting

- **Default**: 5 email/sec (0.2s sleep tra invii)
- **Modificabile in**: `delegations/services/email_service.py:163`
- **Consigliato prod**: 0.5s per evitare blacklist SMTP

### Raggruppamento Email

- Sistema raggruppa per **email unica** (non per designazione)
- RDL con doppio ruolo (effettivo + supplente) riceve **1 sola email**
- Email mostra **entrambe le liste** di sezioni

### Cache PDF

- Cache attiva solo con Redis disponibile
- TTL: 7 giorni
- Location: `media/pdf_cache/`
- Cleanup automatico: TODO (management command)

### Logging

- Level: INFO per email inviate
- Level: ERROR per fallimenti
- Format: Unicode-safe (emoji supportati)
- Output: stdout (raccolto da Docker logs)
