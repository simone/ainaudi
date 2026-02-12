# Vertex AI Setup Guide

Guida completa per configurare Vertex AI (Gemini + Embeddings) per l'assistente AI di AInaudi.

## 📋 Prerequisiti

- Account Google Cloud con billing attivo
- Progetto Google Cloud esistente (o crearne uno nuovo)
- Permessi di amministratore sul progetto

---

## 🚀 Setup per SVILUPPO (Docker Locale)

> **⚡ Setup Automatico**: Usa lo script `./scripts/setup-vertex-ai.sh` per automatizzare i passi 1-4!
>
> ```bash
> gcloud auth login  # Se non già fatto
> ./scripts/setup-vertex-ai.sh ainaudi-prod
> ```
>
> Lo script crea automaticamente:
> - Service account con ruoli corretti
> - Chiave JSON (`gcp-credentials.json`)
> - Abilita API necessarie
> - File `.env.docker`
>
> Poi salta direttamente al **Passo 5**.

---

### Setup Manuale (Alternativa)

### Passo 1: Crea/Seleziona un Progetto Google Cloud

1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Clicca sul menu a tendina del progetto (in alto a sinistra)
3. Opzioni:
   - **Progetto esistente**: Seleziona `ainaudi-prod` (o il tuo progetto)
   - **Nuovo progetto**: Clicca "NEW PROJECT" e chiamalo `ainaudi-dev` o `ainaudi-test`

4. Annota il **Project ID** (es. `ainaudi-prod`)

### Passo 2: Abilita le API necessarie

Vai su [API & Services > Library](https://console.cloud.google.com/apis/library) e abilita:

1. **Vertex AI API**
   - Cerca "Vertex AI API"
   - Clicca "ENABLE"
   - URL diretta: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com

2. **Cloud Resource Manager API** (se non già abilitata)
   - URL diretta: https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com

**Tempo stimato**: 2-3 minuti per l'abilitazione

### Passo 3: Crea Service Account

1. Vai su [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)

2. Clicca **"+ CREATE SERVICE ACCOUNT"**

3. Compila i dettagli:
   ```
   Service account name: ainaudi-vertex-ai
   Service account ID: ainaudi-vertex-ai (generato automaticamente)
   Description: Service account for Vertex AI (Gemini + Embeddings)
   ```

4. Clicca **"CREATE AND CONTINUE"**

5. Assegna i seguenti **Ruoli** (Role):
   ```
   - Vertex AI User (roles/aiplatform.user)
   - Vertex AI Service Agent (roles/aiplatform.serviceAgent)
   ```

   Per aggiungerli:
   - Clicca "Select a role"
   - Cerca "Vertex AI User" → Seleziona
   - Clicca "+ ADD ANOTHER ROLE"
   - Cerca "Vertex AI Service Agent" → Seleziona

6. Clicca **"CONTINUE"** → **"DONE"**

### Passo 4: Scarica le Credenziali JSON

1. Nella lista Service Accounts, trova `ainaudi-vertex-ai`

2. Clicca sui **tre puntini** (⋮) a destra → **"Manage keys"**

3. Clicca **"ADD KEY"** → **"Create new key"**

4. Seleziona **"JSON"** → Clicca **"CREATE"**

5. Il file JSON viene scaricato automaticamente (es. `ainaudi-prod-abc123.json`)

6. **Rinomina il file** in `gcp-credentials.json`

7. **Sposta il file** nella root del progetto:
   ```bash
   mv ~/Downloads/ainaudi-prod-abc123.json /path/to/rdleu2024/gcp-credentials.json
   ```

⚠️ **IMPORTANTE**: NON committare questo file in Git! È già in `.gitignore`.

### Passo 5: Configura le Variabili d'Ambiente

1. Copia il file `.env.docker.example`:
   ```bash
   cp .env.docker.example .env.docker
   ```

2. Modifica `.env.docker` e aggiorna i valori:
   ```bash
   # Vertex AI Configuration
   VERTEX_AI_PROJECT=ainaudi-prod          # Il tuo Project ID
   VERTEX_AI_LOCATION=europe-west1         # Belgio (Gemini disponibile)
   VERTEX_AI_LLM_MODEL=gemini-2.0-flash-001  # Modello stabile
   GCP_CREDENTIALS_PATH=./secrets/gcp-credentials.json
   FEATURE_AI_ASSISTANT=true
   ```

3. Verifica che `gcp-credentials.json` esista:
   ```bash
   ls -la gcp-credentials.json
   ```

### Passo 6: Testa la Configurazione

1. Avvia Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Controlla i log del backend:
   ```bash
   docker-compose logs -f backend
   ```

3. Entra nel container backend:
   ```bash
   docker-compose exec backend python manage.py shell
   ```

4. Testa Vertex AI:
   ```python
   from ai_assistant.vertex_service import vertex_ai_service

   # Test embedding
   embedding = vertex_ai_service.generate_embedding("test")
   print(f"✅ Embedding dimensions: {len(embedding)}")  # Deve essere 768

   # Test LLM
   response = vertex_ai_service.generate_response("Ciao, come stai?")
   print(f"✅ LLM response: {response}")
   ```

   Se tutto funziona, vedrai:
   ```
   ✅ Embedding dimensions: 768
   ✅ LLM response: Ciao! Sto bene, grazie per aver chiesto...
   ```

---

## 🌐 Setup per PRODUZIONE (Google App Engine)

### Passo 1: Abilita le API (come sopra)

Segui **Passo 2** della sezione sviluppo.

### Passo 2: Configura le Variabili d'Ambiente in app.yaml

Modifica `backend_django/app.yaml`:

```yaml
env_variables:
  # ... altre variabili ...

  # Vertex AI Configuration
  VERTEX_AI_PROJECT: "ainaudi-prod"
  VERTEX_AI_LOCATION: "europe-west1"  # Belgio (Gemini disponibile)
  VERTEX_AI_LLM_MODEL: "gemini-2.0-flash-001"  # Modello stabile
  FEATURE_AI_ASSISTANT: "true"
```

### Passo 3: Abilita pgvector in Cloud SQL

⚠️ **IMPORTANTE**: pgvector richiede PostgreSQL 15+

1. Vai su [Cloud SQL](https://console.cloud.google.com/sql/instances)

2. Seleziona la tua istanza PostgreSQL

3. Clicca **"EDIT"**

4. Cerca **"Database flags"** → **"ADD DATABASE FLAG"**

5. Aggiungi il flag:
   ```
   Flag: cloudsql.enable_pgvector
   Value: on
   ```

6. Clicca **"SAVE"**

7. L'istanza si riavvierà (downtime ~2-5 minuti)

8. Verifica l'estensione:
   ```bash
   gcloud sql connect YOUR_INSTANCE_NAME --user=postgres
   ```

   Nel prompt PostgreSQL:
   ```sql
   \c ainaudi_db
   CREATE EXTENSION IF NOT EXISTS vector;
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

   Dovresti vedere:
   ```
   extname | extowner | extnamespace | ...
   --------+----------+--------------+-----
   vector  | 10       | 2200         | ...
   ```

### Passo 4: Configura IAM per App Engine

Il service account di App Engine (default) ha già i permessi necessari, ma verifica:

1. Vai su [IAM & Admin > IAM](https://console.cloud.google.com/iam-admin/iam)

2. Cerca il service account:
   ```
   YOUR-PROJECT@appspot.gserviceaccount.com
   ```

3. Verifica che abbia questi ruoli:
   ```
   - Editor (già presente di default)
   - Vertex AI User (aggiungi se mancante)
   ```

4. Se manca "Vertex AI User":
   - Clicca sulla matita (✏️) accanto al service account
   - Clicca **"+ ADD ANOTHER ROLE"**
   - Cerca "Vertex AI User" → Seleziona
   - Clicca **"SAVE"**

### Passo 5: Deploy su GAE

```bash
cd backend_django
gcloud app deploy
```

Durante il deploy, le variabili d'ambiente in `app.yaml` vengono automaticamente configurate.

### Passo 6: Testa in Produzione

1. Vai su https://ainaudi-prod.uc.r.appspot.com (o il tuo dominio)

2. Login come utente con permesso `can_ask_to_ai_assistant`

3. Clicca sul FAB button (⚡ robot icon in basso a destra)

4. Invia un messaggio: "Come si compila la scheda?"

5. Verifica la risposta con fonti

---

## 🧪 Test Funzionalità RAG

### Test 1: Ingestion automatica FAQ

```bash
docker-compose exec backend python manage.py shell
```

```python
from resources.models import FAQ, CategoriaFAQ
from ai_assistant.models import KnowledgeSource

# Crea una FAQ di test
categoria = CategoriaFAQ.objects.first()
faq = FAQ.objects.create(
    domanda="Come si vota per il referendum?",
    risposta="Per votare al referendum bisogna tracciare un segno sulla scelta preferita (SI o NO).",
    categoria=categoria,
    is_attivo=True
)

# Verifica che sia stata creata la KnowledgeSource
ks = KnowledgeSource.objects.filter(title__contains="Come si vota").first()
print(f"✅ KnowledgeSource creata: {ks.title}")
print(f"✅ Ha embedding: {ks.embedding is not None}")
```

### Test 2: Query RAG

```python
from ai_assistant.rag_service import rag_service

result = rag_service.answer_question("Come si vota per il referendum?")
print(f"\n📝 Answer: {result['answer']}")
print(f"📚 Retrieved docs: {result['retrieved_docs']}")
print(f"🔗 Sources: {[s['title'] for s in result['sources']]}")
```

### Test 3: Chat API

```bash
# Ottieni JWT token (via Magic Link o admin)
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Test chat endpoint
curl -X POST http://localhost:3001/api/ai/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Come si compila la scheda?",
    "context": "SCRUTINY"
  }'
```

Risposta attesa:
```json
{
  "session_id": 1,
  "message": {
    "id": 2,
    "role": "assistant",
    "content": "Per compilare la scheda...",
    "sources": [
      {
        "id": 5,
        "title": "FAQ: Come si compila la scheda?",
        "type": "FAQ",
        "similarity": 0.89
      }
    ],
    "retrieved_docs": 3
  }
}
```

---

## 💰 Costi e Limiti

### Gemini 1.5 Flash (LLM)

| Metrica | Prezzo | Note |
|---------|--------|------|
| Input (testo) | $0.075 / 1M token | ~750 pagine |
| Output (testo) | $0.30 / 1M token | ~750 pagine |
| Context window | 1M token | Enorme! |

**Esempio**: 1000 utenti, 10 domande/giorno = ~$30-50/mese

### text-embedding-004 (Embeddings)

| Metrica | Prezzo | Note |
|---------|--------|------|
| Richieste | **GRATIS** fino a 1M/mese | Poi $0.025/1K |
| Dimensioni | 768 | Fisso |
| Context window | 2048 token | ~1500 parole |

**Esempio**: 100 FAQ + 50 documenti = 150 embedding iniziali (gratis)

### Limiti (Quota)

| Risorsa | Limite Default | Come aumentare |
|---------|----------------|----------------|
| Gemini requests | 300/min | Richiedere aumento quota |
| Embedding requests | 60/min | Richiedere aumento quota |
| Concurrent requests | 10 | Aumenta automaticamente |

**Monitoraggio**: [Console > Quotas & Limits](https://console.cloud.google.com/iam-admin/quotas?service=aiplatform.googleapis.com)

---

## 🔒 Sicurezza

### Protezione Credenziali

✅ **Fai**:
- Usa service account con ruoli minimi necessari
- Ruota le chiavi ogni 90 giorni
- Usa Secret Manager in produzione (opzionale)
- Monitora i log di accesso

❌ **Non fare**:
- Committare `gcp-credentials.json` in Git
- Condividere le credenziali via email/chat
- Usare lo stesso service account per dev e prod
- Dare ruoli "Owner" o "Editor" non necessari

### Monitoraggio Costi

1. Imposta budget alert:
   - Vai su [Billing > Budgets & Alerts](https://console.cloud.google.com/billing/budgets)
   - Clicca **"CREATE BUDGET"**
   - Imposta soglia: $100/mese
   - Alert al 50%, 90%, 100%

2. Controlla usage giornaliero:
   - [Vertex AI > Dashboard](https://console.cloud.google.com/vertex-ai)
   - Verifica request count e token usage

---

## 🐛 Troubleshooting

### Errore: "Permission denied" o "403 Forbidden"

**Causa**: Service account senza permessi

**Soluzione**:
```bash
# Verifica ruoli assegnati
gcloud projects get-iam-policy ainaudi-prod \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:ainaudi-vertex-ai@*"

# Aggiungi ruolo mancante
gcloud projects add-iam-policy-binding ainaudi-prod \
  --member="serviceAccount:ainaudi-vertex-ai@ainaudi-prod.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Errore: "API not enabled"

**Causa**: Vertex AI API non abilitata

**Soluzione**:
```bash
# Abilita via gcloud
gcloud services enable aiplatform.googleapis.com --project=ainaudi-prod
```

### Errore: "GOOGLE_APPLICATION_CREDENTIALS not found"

**Causa**: File JSON non montato correttamente in Docker

**Soluzione**:
```bash
# Verifica il file esista
ls -la gcp-credentials.json

# Verifica sia montato nel container
docker-compose exec backend ls -la /app/gcp-credentials.json

# Se manca, riavvia Docker Compose
docker-compose down
docker-compose up -d
```

### Errore: "Extension 'vector' does not exist"

**Causa**: pgvector non abilitato in PostgreSQL

**Soluzione Docker**:
```bash
# Usa l'immagine ankane/pgvector invece di postgres:15-alpine
# Già configurato in docker-compose.yml

# Verifica
docker-compose exec db psql -U postgres -d ainaudi_db -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

**Soluzione Cloud SQL**:
```bash
# Abilita il flag database
gcloud sql instances patch YOUR_INSTANCE \
  --database-flags=cloudsql.enable_pgvector=on
```

### Errore: "Model not found" o "INVALID_ARGUMENT"

**Causa**: Regione sbagliata o modello non disponibile

**Soluzione**:
- Usa `europe-west8` (Milano) o `europe-west1` (Belgio) - entrambe supportano Gemini
- Verifica il nome modello: `gemini-1.5-flash-002` (non `gemini-1.5-flash`)
- Se Europe non funziona, prova temporaneamente `us-central1` per debug

### Performance lenta (>5s per risposta)

**Cause possibili**:
1. Embedding generation su documenti lunghi
2. Troppi documenti retrieved (RAG_TOP_K troppo alto)
3. Cold start Vertex AI

**Soluzioni**:
```python
# In settings.py
RAG_TOP_K = 3  # Riduci da 5 a 3
RAG_MAX_CONTEXT_TOKENS = 3000  # Riduci da 4000

# Limita lunghezza documenti
# In ai_assistant/rag_service.py, linea 42:
context_parts.append(f"[{doc.source_type}] {doc.title}\n{doc.content[:1500]}")
# Riduci da 2000 a 1500 caratteri
```

---

## 📚 Risorse Utili

### Documentazione Google Cloud

- [Vertex AI Overview](https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview)
- [Gemini API Quickstart](https://cloud.google.com/vertex-ai/docs/generative-ai/start/quickstarts/quickstart-multimodal)
- [Text Embeddings Guide](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-for-using-service-accounts)

### SDK Python

- [google-cloud-aiplatform](https://cloud.google.com/python/docs/reference/aiplatform/latest)
- [vertexai Package](https://cloud.google.com/vertex-ai/docs/python-sdk/use-vertex-ai-python-sdk)

### Vertex AI Regions (Europa)

| Region | Location | Gemini 2.0 | Latenza (Italia) | GDPR |
|--------|----------|------------|------------------|------|
| **europe-west1** | **Belgio** 🇪🇺 | ✅ | **~30ms** | ✅ |
| europe-west4 | Paesi Bassi | ✅ | ~40ms | ✅ |
| europe-west8 | Milano, Italia 🇮🇹 | ❌ (solo embeddings) | ~5ms | ✅ |
| us-central1 | Iowa, USA | ✅ | ~150ms | ❌ |

**Raccomandazione**: Usa `europe-west1` (Belgio) per Gemini + GDPR compliance in EU.

**Note**: Milano (europe-west8) supporta solo embeddings, non Gemini LLM.

---

## ✅ Checklist Setup

### Sviluppo (Docker)

- [ ] Progetto Google Cloud creato
- [ ] Vertex AI API abilitata
- [ ] Service account creato con ruoli corretti
- [ ] `gcp-credentials.json` scaricato e rinominato
- [ ] `.env.docker` configurato con le variabili
- [ ] Docker Compose avviato con successo
- [ ] Test embedding funzionante (768 dimensioni)
- [ ] Test LLM funzionante (risposta Gemini)
- [ ] Test RAG con FAQ di prova

### Produzione (GAE)

- [ ] Vertex AI API abilitata
- [ ] pgvector abilitato in Cloud SQL
- [ ] `app.yaml` configurato con variabili Vertex AI
- [ ] Service account GAE ha ruolo "Vertex AI User"
- [ ] Budget alert impostato ($100/mese)
- [ ] Deploy completato con successo
- [ ] Test chat interface su dominio produzione
- [ ] Monitoraggio costi attivo

---

## 🆘 Supporto

Per problemi o domande:

1. **Errori setup**: Controlla i log di Docker (`docker-compose logs backend`)
2. **Errori API**: Verifica [Cloud Console Logs](https://console.cloud.google.com/logs/query)
3. **Costi elevati**: Riduci `RAG_TOP_K` e abilita caching
4. **Performance**: Usa regione geograficamente vicina

---

**Ultima modifica**: 2024-02-11
**Autore**: Assistente AI
**Versione**: 1.0
