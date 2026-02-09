# 📧 Setup Gmail SMTP - 3 Passi Veloci

Guida rapida per configurare **s.federici@gmail.com** per inviare email da AInaudi.

---

## ✅ Passo 1: Genera App Password Gmail

1. **Abilita 2FA** (se non l'hai già fatto):
   - Vai su: https://myaccount.google.com/security
   - **Sicurezza** → **Verifica in due passaggi** → Attiva

2. **Genera App Password**:
   - Vai su: https://myaccount.google.com/apppasswords
   - App: **Mail**
   - Dispositivo: **Altro** → scrivi "AInaudi Django"
   - Clicca **Genera**
   - **Copia la password di 16 caratteri** (es: `abcd efgh ijkl mnop`)

**⚠️ SALVA subito**: La password appare una sola volta!

---

## ✅ Passo 2: Configura localmente (test)

### A. Configura variabili ambiente

**Con Docker** (raccomandato):

Modifica `.env.docker`:

```bash
# Decommentare e configurare
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=s.federici@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop  # La tua App Password (senza spazi)
DEFAULT_FROM_EMAIL=s.federici@gmail.com
```

Poi riavvia Docker:

```bash
docker-compose down
docker-compose up -d
```

**Senza Docker**:

Modifica `backend_django/.env`:

```bash
# Stesso contenuto sopra
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
...
```

### B. Testa l'invio

**Metodo 1: Script automatico** (funziona con e senza Docker)

```bash
./scripts/test-email.sh tua@email.com
```

**Metodo 2: Comandi manuali**

Con Docker:

```bash
docker-compose exec backend python test_email.py tua@email.com
```

Senza Docker:

```bash
cd backend_django
python test_email.py tua@email.com
```

Se vedi `✅ Email inviata con successo!`, vai avanti!

---

## ✅ Passo 3: Configura su GCP (produzione)

Esegui lo script automatico:

```bash
./scripts/setup-gmail-secrets.sh
```

Lo script ti chiederà:
1. Password database PostgreSQL (quella che hai creato prima)
2. Gmail App Password (quella del Passo 1)

**Fatto!** I secrets sono configurati su Secret Manager.

---

## 🚀 Deploy

Ora puoi deployare su App Engine:

```bash
cd backend_django
python manage.py collectstatic --noinput
gcloud app deploy app.yaml --project=ainaudi-prod
```

Le email verranno inviate come **s.federici@gmail.com** 📧

---

## ⚠️ Limiti Gmail

- **500 email/giorno** (limite account Gmail personale)
- Per volumi maggiori, passa a SendGrid (vedi `PRODUCTION_SETUP.md` Opzione B)

---

## 🐛 Troubleshooting

**Email non parte?**

1. Verifica 2FA attivo su Gmail
2. Verifica App Password corretta (16 caratteri, senza spazi)
3. Controlla firewall (porta 587 aperta)
4. Controlla logs Django: `python manage.py shell` poi:
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Messaggio', 's.federici@gmail.com', ['test@example.com'])
   ```

**Email finisce in spam?**

- Aggiungi SPF record al tuo dominio
- Per produzione seria, usa dominio personalizzato + SendGrid

---

## 📖 Documentazione Completa

Vedi `PRODUCTION_SETUP.md` per setup completo GCP + database + storage.
