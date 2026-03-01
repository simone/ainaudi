# Configurazione DNS ainaudi.it su Squarespace

**Hostname:** ainaudi.it
**Registrar:** Squarespace (ex Google Domains)
**Email Provider:** Amazon SES
**AWS Region:** eu-west-3 (Parigi)

---

## 🚀 Step-by-Step Setup su Squarespace

### 1️⃣ Accedi a Squarespace

1. Vai a: https://squarespace.com/login
2. Accedi con le tue credenziali Google Domains (dovrebbero essere migrate automaticamente)
3. Nel menu: **Account** → **Domains**
4. Clicca su **ainaudi.it**

---

### 2️⃣ Aggiungi i Record DNS su Squarespace

In Squarespace, i record DNS si aggiungono nel pannello "Advanced DNS" (o "DNS records").

Cerca una sezione tipo:
```
DNS Providers → Manage custom records → ainaudi.it
```

---

## 📝 Record DNS da Aggiungere (in ordine)

### A. SPF Record

| Field | Value |
|-------|-------|
| **Type** | TXT |
| **Name/Host** | @ (oppure lascia vuoto) |
| **Data/Value** | `v=spf1 include:amazonses.com -all` |
| **TTL** | 3600 (default) |

**Salva** → Attendi propagazione (15-30 min)

---

### B. DKIM Records (3 CNAME records)

**PRIMA:** Devi generare i token da AWS SES Console!

#### Step B1: Genera i Token DKIM su AWS SES

1. Vai a: https://console.aws.amazon.com/ses/
2. **Email Identities** → seleziona `ainaudi.it`
3. Tab **Authentication**
4. Sezione **DKIM**
5. Se non è configurato: clicca **Create DKIM setting**
6. Ti appariranno 3 token. **Copia tutto** (avrà formato simile):

```
Selector: default
Token:    xxxxxxxxxxxxxxxxxxxxxxxx.dkim.amazonses.com

Selector: amazon
Token:    yyyyyyyyyyyyyyyyyyyyyyyy.dkim.amazonses.com

Selector: amazonses
Token:    zzzzzzzzzzzzzzzzzzzzzzzz.dkim.amazonses.com
```

#### Step B2: Aggiungi i 3 CNAME Records su Squarespace

Per **ognuno** dei 3 token, aggiungi un record CNAME in Squarespace:

```
Type: CNAME
Name: default._domainkey
Data: xxxxxxxxxxxxxxxxxxxxxxxx.dkim.amazonses.com
TTL:  3600
```

```
Type: CNAME
Name: amazon._domainkey
Data: yyyyyyyyyyyyyyyyyyyyyyyy.dkim.amazonses.com
TTL:  3600
```

```
Type: CNAME
Name: amazonses._domainkey
Data: zzzzzzzzzzzzzzzzzzzzzzzz.dkim.amazonses.com
TTL:  3600
```

**Salva ogni record** → Attendi propagazione (15-30 min)

✅ Quando i record saranno propagati, AWS SES Console cambierà lo stato da "Pending" a "Success" (attendi max 1 ora)

---

### C. DMARC Record

| Field | Value |
|-------|-------|
| **Type** | TXT |
| **Name/Host** | _dmarc |
| **Data/Value** | `v=DMARC1; p=quarantine; rua=mailto:dmarc@ainaudi.it; adkim=s; aspf=s` |
| **TTL** | 3600 |

**Salva** → Attendi propagazione (15-30 min)

⚠️ **Nota:** Assicurati che l'indirizzo `dmarc@ainaudi.it` esista nel tuo email provider! (Altrimenti non riceverai i report)

---

### D. MAIL FROM Domain (Opzionale ma Consigliato)

| Field | Value |
|-------|-------|
| **Type** | MX |
| **Name/Host** | bounce |
| **Data/Value** | `10 feedback-smtp.eu-west-3.amazonses.com` |
| **TTL** | 3600 |

**Salva** → Attendi propagazione (15-30 min)

#### Configura anche in AWS SES Console:
1. Vai a AWS SES → `ainaudi.it` → Tab **Authentication**
2. Sezione **MAIL FROM domain**
3. Clicca **Set MAIL FROM domain**
4. Inserisci: `bounce.ainaudi.it`
5. Clicca **Save**

Lo status cambierà a "Success" dopo propagazione DNS.

---

## 📋 Checklist Configurazione

- [ ] **SPF:** Aggiunto `v=spf1 include:amazonses.com -all`
- [ ] **DKIM Token 1:** `default._domainkey` → CNAME aggiunto
- [ ] **DKIM Token 2:** `amazon._domainkey` → CNAME aggiunto
- [ ] **DKIM Token 3:** `amazonses._domainkey` → CNAME aggiunto
- [ ] **DKIM Status:** AWS SES Console mostra "Success" per tutti e 3
- [ ] **DMARC:** `_dmarc` → TXT record aggiunto
- [ ] **MAIL FROM:** `bounce` → MX record aggiunto (opzionale)
- [ ] **Email DMARC:** Indirizzo `dmarc@ainaudi.it` esiste e funziona

---

## ⏱️ Timeline di Propagazione

| Step | Tempo | Note |
|------|-------|------|
| SPF aggiunto | 15-30 min | Controllare con `dig ainaudi.it TXT` |
| DKIM CNAME aggiunto | 15-30 min | AWS SES mostrerà "Pending" |
| DKIM propagato completamente | 30-60 min | AWS SES cambierà a "Success" |
| DMARC propagato | 15-30 min | Controllare con `dig _dmarc.ainaudi.it TXT` |
| MAIL FROM propagato | 15-30 min | AWS SES status diventerà "Success" |

**Totale:** ~1 ora per avere tutto funzionante

---

## 🧪 Test Finale

Una volta che tutti i record sono propagati (AWS SES Console mostra tutti "Success"):

```bash
python3 test_email_deliverability.py ainaudi.it noreply@ainaudi.it --verbose
```

**Target:** Score ≥ 85/100

```
✓ Tests OK: ['spf', 'dkim', 'dmarc', 'ses_dkim', 'reverse_dns', 'mail_from']
📈 Deliverability Score: 90/100
✓ Eccellente - Email dovrebbe arrivare in Inbox
```

---

## 🔧 Squarespace DNS Panel Tips

1. **Trovare il pannello DNS:**
   - Menu → **Account** → **Domains**
   - Clicca `ainaudi.it`
   - Sezione **DNS** o **Advanced DNS settings**

2. **Aggiungere nuovi record:**
   - Pulsante "+ Add Record"
   - Seleziona **Type** (TXT, CNAME, MX)
   - Compila **Name** (host), **Data** (value), **TTL**
   - Clicca **Save** o **Add**

3. **Controllare i record:**
   - Squarespace mostra una lista di tutti i record
   - Puoi eliminarli o modificarli facilmente

4. **Propagazione:**
   - Squarespace di solito propaga in 15-30 minuti
   - Per urgenze: attendi max 1 ora

---

## ❓ Troubleshooting

### "DKIM pending in AWS SES dopo 1 ora"
- Verifica che i CNAME record su Squarespace siano corretti
- Copia di nuovo i token da AWS SES (non aggiungere `.dkim.amazonses.com` due volte)
- Usa `dig` per verificare:
  ```bash
  dig default._domainkey.ainaudi.it CNAME
  ```
  Deve rispondere con il token DKIM.

### "SPF record non trovato"
- Accedi a Squarespace, vai a **DNS settings**
- Verifica che il record TXT per `@` o il root contenga `v=spf1 include:amazonses.com -all`
- Aspetta 30 minuti per propagazione

### "Email ancora in spam"
- Attendi che DKIM sia "Success" in AWS SES (non solo aggiunto)
- Assicurati DMARC policy sia `p=quarantine` o `p=reject`
- Invia un email test a Gmail e controlla con il lucchetto 🔒 "Show original"

---

## 📞 Support

- **Squarespace DNS Help:** https://support.squarespace.com/hc/en-us/articles/206812908
- **AWS SES Documentation:** https://docs.aws.amazon.com/ses/
- **Email Test:** `python3 test_email_deliverability.py ainaudi.it noreply@ainaudi.it --verbose`

---

**Sei pronto? Fammi sapere quando hai aggiunto i record e faremo il test!** 🚀
