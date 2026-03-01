# Abilitare Cloud DNS API su Google Cloud

## Step 1: Vai a Google Cloud Console

1. Accedi a: https://console.cloud.google.com/

---

## Step 2: Abilita Cloud DNS API

### Metodo A: Via Marketplace API (Consigliato)

1. Nel menu superiore, clicca su **APIs & Services** (o cerca nella barra)
2. Clicca **Enable APIs and Services**
3. Cerca: `cloud dns`
4. Clicca su **Cloud DNS API**
5. Clicca **ENABLE** (pulsante blu grande)

**Aspetta** 1-2 minuti mentre si abilita...

### Metodo B: Via Link Diretto

Apri direttamente:
```
https://console.cloud.google.com/apis/library/dns.googleapis.com
```

Clicca **ENABLE**

---

## Step 3: Verifica che sia Abilitato

Vai a: https://console.cloud.google.com/apis/enabled

Dovresti vedere **Cloud DNS API** nella lista.

---

## Step 4: Configura Credenziali (se necessario)

Se ti chiede di creare credenziali:
1. Clicca **Create Credentials**
2. Scegli:
   - **Application type:** Service account
   - Dai un nome tipo `rdl-dns-manager`
   - Clicca **Create and Continue**
3. Assegna il ruolo: **DNS Administrator** (o **DNS.admin**)
4. Clicca **Continue** → **Done**

---

## Dopo che hai abilitato Cloud DNS API

Torna qui e dimmi che è abilitato! 🚀

Poi faremo:
1. ✅ Creare una zona DNS per ainaudi.it
2. ✅ Aggiungere i 4 nameserver di Google Cloud al dominio (su Squarespace)
3. ✅ Aggiungere i record DNS (SPF, DKIM, DMARC, MAIL FROM)

**Dimmi quando è fatto!**
