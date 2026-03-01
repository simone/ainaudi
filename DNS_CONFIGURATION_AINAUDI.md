# Configurazione DNS per ainaudi.it - Email Deliverability

## 📋 Checklist Configurazione

- [ ] SPF Record aggiunto
- [ ] DKIM generato in AWS SES
- [ ] DKIM CNAME records aggiunto al DNS (3 record)
- [ ] DMARC Record aggiunto
- [ ] Custom MAIL FROM configurato (opzionale)
- [ ] Test verificato con `test_email_deliverability.py`

---

## 1️⃣ SPF Record (Sender Policy Framework)

**Dove:** DNS provider (Cloudflare, Google Domains, AWS Route53, etc.)

```
Name:  ainaudi.it
Type:  TXT
Value: v=spf1 include:amazonses.com -all
TTL:   3600
```

**Spiegazione:**
- `v=spf1`: SPF versione 1
- `include:amazonses.com`: Consenti Amazon SES di inviare email
- `-all`: Rifiuta mail da altri server (restrittivo - migliore)

**Verifica:** Dopo 15-30 minuti (propagazione DNS), esegui:
```bash
dig ainaudi.it TXT | grep v=spf1
```

---

## 2️⃣ DKIM (DomainKeys Identified Mail)

### Step A: Generare DKIM in AWS SES Console

1. Vai a: https://console.aws.amazon.com/ses/
2. Seleziona **Email Identities** → `ainaudi.it`
3. Clicca tab **Authentication** → **DKIM**
4. Se non configurato, clicca **Create DKIM setting** oppure **Generate DKIM tokens**
5. Copia i 3 CNAME records che appaiono

**Formato dei token DKIM:**
```
Selector: default
Token:    <random-string-1>

Selector: amazon
Token:    <random-string-2>

Selector: amazonses
Token:    <random-string-3>
```

### Step B: Aggiungere i CNAME Records al DNS

Per ognuno dei 3 token, aggiungi un record CNAME:

```
Name:   default._domainkey.ainaudi.it
Type:   CNAME
Value:  <token-1>.dkim.amazonses.com
TTL:    3600

---

Name:   amazon._domainkey.ainaudi.it
Type:   CNAME
Value:  <token-2>.dkim.amazonses.com
TTL:    3600

---

Name:   amazonses._domainkey.ainaudi.it
Type:   CNAME
Value:  <token-3>.dkim.amazonses.com
TTL:    3600
```

**⚠️ IMPORTANTE:** Sostituisci `<token-1>`, `<token-2>`, `<token-3>` con i valori reali da AWS SES.

**Verifica:** Dopo 15-30 minuti, torna in AWS SES console. Il status cambierà da "Pending" a "Success" quando i record saranno propagati.

---

## 3️⃣ DMARC (Domain-based Message Authentication, Reporting & Conformance)

**Dove:** DNS provider

```
Name:  _dmarc.ainaudi.it
Type:  TXT
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@ainaudi.it; adkim=s; aspf=s
TTL:   3600
```

**Spiegazione dei parametri:**
- `v=DMARC1`: DMARC versione 1
- `p=quarantine`: Manda email sospette in spam (compromesso tra `p=none` e `p=reject`)
- `rua=mailto:dmarc@ainaudi.it`: Invia report giornalieri a dmarc@ainaudi.it
- `adkim=s`: DKIM alignment strict (firma deve essere dello stesso dominio)
- `aspf=s`: SPF alignment strict (MAIL FROM deve essere dello stesso dominio)

**Progressione di policy (se vuoi partire conservative):**
1. Usa `p=none` per monitorare (nessuna azione su email non-DMARC)
2. Dopo 1-2 settimane, cambia a `p=quarantine` (spam folder)
3. Dopo altre 1-2 settimane, cambia a `p=reject` (massima protezione)

---

## 4️⃣ Custom MAIL FROM Domain (Opzionale ma Consigliato)

### Step A: Aggiungere MX record al DNS

```
Name:   bounce.ainaudi.it
Type:   MX
Value:  10 feedback-smtp.eu-west-1.amazonses.com
TTL:    3600
```

⚠️ **Sostituisci `eu-west-1` con la tua AWS region!**

### Step B: Configurare in AWS SES Console

1. Vai a: https://console.aws.amazon.com/ses/
2. Seleziona Email Identity: `ainaudi.it`
3. Tab **Authentication**
4. Sezione **MAIL FROM domain**
5. Clicca **Set MAIL FROM domain**
6. Inserisci: `bounce.ainaudi.it`
7. Clicca **Save**

**Verifica:** Lo status cambierà a "Success" dopo propagazione DNS.

**Beneficio:** Le bounce email verranno reindirizzate a bounce@ainaudi.it invece di un indirizzo Amazon generico.

---

## 5️⃣ Email per Report DMARC

Se usi `rua=mailto:dmarc@ainaudi.it`, assicurati che l'indirizzo esista!

Opzioni:
1. **Crea mailbox** `dmarc@ainaudi.it` in AWS SES o email provider
2. **Opzione alternative:**
   ```
   rua=mailto:admin@ainaudi.it,mailto:tech@ainaudi.it
   ```

I report arrivano una volta al giorno con statistiche su:
- Email autenticate (DKIM + SPF pass)
- Email fallite
- Origini sospette

---

## 6️⃣ Ordine di Configurazione Consigliato

1. **SPF** (più veloce, nessuna dipendenza)
2. **DKIM** (richiede AWS SES, 3 record)
3. **MAIL FROM** (dipende da DKIM)
4. **DMARC** (dipende da SPF + DKIM)

Aspetta 15-30 minuti tra ogni step per propagazione DNS.

---

## 7️⃣ Test e Verifica

### Test Automatico (dopo aver configurato tutto)
```bash
python3 test_email_deliverability.py ainaudi.it noreply@ainaudi.it --verbose
```

### Test Manuali

**SPF:**
```bash
dig ainaudi.it TXT
# Deve contenere: v=spf1 include:amazonses.com -all
```

**DKIM:**
```bash
dig default._domainkey.ainaudi.it CNAME
dig amazon._domainkey.ainaudi.it CNAME
dig amazonses._domainkey.ainaudi.it CNAME
# Devono tutti risolvere a dkim.amazonses.com
```

**DMARC:**
```bash
dig _dmarc.ainaudi.it TXT
# Deve contenere: v=DMARC1; p=quarantine; ...
```

### Test Email Reale

Invia un'email da `noreply@ainaudi.it` a un account Gmail/Outlook e controlla:
1. Arriva in Inbox (non spam)
2. Clicca il lucchetto 🔒 → "Show original" → cerca:
   - `dkim=pass`
   - `spf=pass`
   - `dmarc=pass`

---

## 8️⃣ Troubleshooting

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| SPF non trovato | DNS non propagato | Attendi 30 min, controlla TTL |
| DKIM pending in AWS | CNAME record non trovato | Verifica i token siano corretti |
| Email in spam | DMARC policy non setup | Aggiungi DMARC record |
| Report DMARC non arrivano | Email inesistente | Crea mailbox `dmarc@ainaudi.it` |

---

## 9️⃣ Risorse AWS SES

- **Console SES:** https://console.aws.amazon.com/ses/
- **Docs DKIM:** https://docs.aws.amazon.com/ses/latest/dg/verify-domain-dkim.html
- **Docs MAIL FROM:** https://docs.aws.amazon.com/ses/latest/dg/mail-from.html
- **Docs DMARC:** https://dmarc.org/

---

## ✅ Deliverability Score Target

| Configurazione | Score |
|---|---|
| SPF + DKIM (basic) | 70-80 |
| + DMARC (recommended) | 85-90 |
| + MAIL FROM (advanced) | 90-100 |

**Goal:** Raggiungere almeno **85/100** per evitare spam folder.

---

Generated: 2026-02-28
Last updated email test: `test_email_deliverability.py`
