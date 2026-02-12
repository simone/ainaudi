# 🔧 Fix Rapido - Gemini non disponibile

Se vedi l'errore `404 Publisher Model not found`, significa che Gemini non è abilitato nel progetto o non è disponibile nella region.

## ✅ Soluzione 1: Usa US (Sempre Funziona) - 30 secondi

Cambia temporaneamente a `us-central1` per testare:

```bash
# Stop Docker
docker-compose down

# Modifica docker-compose.yml
sed -i '' 's/VERTEX_AI_LOCATION:-europe-west1/VERTEX_AI_LOCATION:-us-central1/' docker-compose.yml

# Avvia Docker
docker-compose up -d

# Test
docker-compose exec backend python manage.py shell <<'EOTEST'
from ai_assistant.vertex_service import vertex_ai_service
resp = vertex_ai_service.generate_response("Ciao")
print(f"✅ SUCCESSO: {resp}")
EOTEST
```

## ✅ Soluzione 2: Abilita Gemini nel Progetto - 2 minuti

1. Vai su [Vertex AI Console](https://console.cloud.google.com/vertex-ai)
2. Seleziona progetto `ainaudi-prod`
3. Vai su **"Model Garden"** nel menu laterale
4. Cerca **"Gemini 1.5 Flash"**
5. Clicca **"ENABLE"** o **"GET STARTED"**
6. Accetta i Terms of Service
7. Riprova con europe-west1

**Via CLI (più veloce):**
```bash
# Abilita Gemini API
gcloud services enable generativelanguage.googleapis.com --project=ainaudi-prod

# Verifica che Vertex AI sia abilitato
gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --project=ainaudi-prod
```

## ✅ Soluzione 3: Verifica Permessi

Il service account potrebbe non avere permessi sufficienti:

```bash
# Verifica ruoli
gcloud projects get-iam-policy ainaudi-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:ainaudi-vertex-ai@*"

# Aggiungi ruolo Gemini (se mancante)
gcloud projects add-iam-policy-binding ainaudi-prod \
  --member="serviceAccount:ainaudi-vertex-ai@ainaudi-prod.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

## 🔍 Debug: Quali Modelli Sono Disponibili?

```python
# In Docker shell
docker-compose exec backend python manage.py shell

from google.cloud import aiplatform
aiplatform.init(project="ainaudi-prod", location="europe-west1")

# Lista modelli disponibili
from vertexai.preview import language_models
models = language_models.TextGenerationModel.list_tuned_model_names()
print(f"Modelli disponibili: {models}")
```

## 📍 Regions Gemini Supportate (2025)

| Region | Gemini 2.0 | Latenza IT | GDPR |
|--------|------------|------------|------|
| **us-central1** | ✅ **Sempre** | ~150ms | ❌ |
| **europe-west1** | ✅ **Raccomandato** | ~30ms | ✅ |
| europe-west4 | ✅ | ~40ms | ✅ |
| asia-southeast1 | ✅ | ~200ms | ❌ |

**europe-west8 (Milano)**: ❌ Gemini non disponibile (solo embeddings)

**Modelli Stabili (2025)**:
- `gemini-2.5-flash` (ultimo, più capace)
- `gemini-2.0-flash-001` (stabile, economico) ⭐ **Raccomandato**
- `gemini-1.5-flash` ❌ **Deprecato**

---

**Soluzione rapida per sviluppo**: Usa `us-central1`  
**Soluzione per produzione**: Abilita Gemini + usa `europe-west1`
