# 🚀 Quick Start - AI Assistant (3 minuti)

Guida rapida per testare l'AI Assistant in locale con Docker.

**Setup automatizzato con script bash!** ⚡

## ✅ Prerequisiti

- Docker Desktop installato e avviato
- Account Google Cloud (anche trial gratuito)

---

## 📝 Setup in 3 Step

### Step 1: Setup Automatico Google Cloud (1 min) ⚡

Esegui lo script automatico che:
- ✅ Crea service account
- ✅ Assegna ruoli Vertex AI
- ✅ Scarica credenziali JSON
- ✅ Abilita API necessarie
- ✅ Crea `.env.docker`

```bash
# Se hai già fatto gcloud auth login:
./scripts/setup-vertex-ai.sh

# Altrimenti, prima autenticati:
gcloud auth login
./scripts/setup-vertex-ai.sh

# Per un progetto diverso:
./scripts/setup-vertex-ai.sh mio-progetto-id
```

**Output atteso:**
```
=================================
  ✅ Setup completato!
=================================

Configurazione:
  Project:         ainaudi-prod
  Service Account: ainaudi-vertex-ai@ainaudi-prod.iam.gserviceaccount.com
  Credenziali:     secrets/gcp-credentials.json
```

> **Alternativa manuale**: Se preferisci fare il setup manualmente, vedi [VERTEX_AI_SETUP.md](./VERTEX_AI_SETUP.md) - Passo 1-3

### Step 2: Verifica Configurazione (30 sec)

```bash
# Verifica che il file esista
ls -la secrets/gcp-credentials.json

# Verifica variabili (opzionale)
cat .env.docker | grep VERTEX
```

Valori default (già configurati):
```bash
VERTEX_AI_PROJECT=ainaudi-prod
VERTEX_AI_LOCATION=europe-west1  # Belgio (Gemini disponibile)
VERTEX_AI_LLM_MODEL=gemini-2.0-flash-001  # Modello stabile
FEATURE_AI_ASSISTANT=true
```

### Step 3: Avvia Docker e Testa (2 min)

```bash
# Rebuild backend con nuove dipendenze (solo prima volta)
docker-compose build --no-cache backend

# Avvia tutti i servizi
docker-compose up -d

# Controlla i log
docker-compose logs -f backend
```

Attendi il messaggio: `Django version X.X.X, using settings 'config.settings'`

### Test RAG

```bash
# Entra nel container backend
docker-compose exec backend python manage.py shell
```

Nel shell Python:
```python
from ai_assistant.vertex_service import vertex_ai_service

# Test 1: Embedding (veloce)
emb = vertex_ai_service.generate_embedding("test")
print(f"✅ Embedding: {len(emb)} dimensioni")  # Deve essere 768

# Test 2: LLM (richiede ~2-3 secondi)
resp = vertex_ai_service.generate_response("Ciao, come stai?")
print(f"✅ Gemini: {resp[:100]}...")

# Exit
exit()
```

Se vedi entrambi i ✅ → **Setup completato!**

---

## 📚 Vettorializza Knowledge Base (Opzionale)

Per abilitare il RAG con le FAQ e i Documenti esistenti:

```bash
# Vettorializza tutte le FAQ e i Documenti
docker-compose exec backend python manage.py vectorize_knowledge

# Output atteso:
# ✅ 12 FAQ vettorializzate
# ✅ 11 Documenti processati
# ⏱️ ~15 secondi
```

**Altre opzioni:**
```bash
--faq-only    # Solo FAQ
--docs-only   # Solo Documenti
--force       # Re-vettorializza tutto
--dry-run     # Mostra cosa farebbe senza farlo
```

## 🎯 Test Frontend

1. Apri http://localhost:3000
2. Login (usa Magic Link o credenziali esistenti)
3. Cerca il **FAB button giallo** in basso a destra (icona robot 🤖)
4. Clicca e invia: _"Cosa dice il Ministero dell'Interno sul referendum?"_
5. Verifica la risposta **con fonti citate** 📚

---

## 🐛 Troubleshooting

### Errore: "Permission denied"

```bash
# Verifica che il file JSON esista
ls -la secrets/gcp-credentials.json

# Verifica che Docker lo monti
docker-compose exec backend ls -la /app/secrets/gcp-credentials.json

# Se manca, riavvia
docker-compose down && docker-compose up -d
```

### Errore: "API not enabled"

```bash
# Abilita Vertex AI
gcloud services enable aiplatform.googleapis.com --project=ainaudi-prod
```

### Errore: "Extension 'vector' does not exist"

Il container usa già `ankane/pgvector`, quindi non dovrebbe succedere.

Verifica:
```bash
docker-compose exec db psql -U postgres -d ainaudi_db -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

Se manca:
```bash
# Riavvia il database
docker-compose restart db

# Esegui migrations
docker-compose exec backend python manage.py migrate
```

### Performance lenta (>10s)

Causa: Cold start Vertex AI (prima richiesta)

Soluzione: Aspetta 30s e riprova. Dalla seconda richiesta sarà veloce (~2s).

---

## 📚 Documentazione Completa

Per setup produzione, costi, monitoring: vedi [VERTEX_AI_SETUP.md](./VERTEX_AI_SETUP.md)

---

## 🆘 Aiuto

Problemi? Controlla i log:
```bash
# Log backend
docker-compose logs backend | grep -i "vertex\|gemini\|error"

# Log database
docker-compose logs db | grep -i "vector\|error"

# Tutti i log
docker-compose logs --tail=50
```

---

**Setup completato in**: ~3 minuti ⚡ (automatizzato!)
**Prossimi step**: Ingest FAQ, test chat interface, deploy produzione
**Costi**: Primi 100 test gratis, poi ~$0.10/giorno per sviluppo
