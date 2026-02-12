# AInaudi - Gestione Elettorale #

Ad uso gratuito per il Movimento 5 Stelle

© Simone Federici (s.federici@gmail.com)


# Introduzione
AInaudi è un sistema di gestione elettorale per la raccolta dati nelle sezioni.
Serve per inviare al movimento i dati raccolti nelle sezioni. Si
prega di scegliere una delle sezioni assegnate e di compilare
tutti i campi richiesti con i numeri corretti.

## Utilizzo
Per utilizzare l'applicazione è necessario avere un account Google
e accedere all'applicazione con le proprie credenziali. Una volta
effettuato l'accesso, è possibile scegliere la sezione da compilare
e inserire i dati richiesti. Una volta completata la compilazione,
è possibile inviare i dati al movimento.

## Subdelegati
I sub delegati sono i responsabili delle sezioni e possono assegnare
le sezioni ai propri RDL. I sub delegati possono accedere all'applicazione
con le proprie credenziali e assegnare le sezioni ai propri RDL.
Inoltre possono visualizzare i dati inviati dai propri RDL.

## Grafici
I grafici mostrano i dati raccolti nelle sezioni. I grafici sono
aggiornati in tempo reale e mostrano i dati inviati dai RDL.
E' possibile vedere i voti per ogni candidato e il totale dei voti
divisi per cittò e municipio.


## Project Structure
```text
project-root/
│
├── backend/ (API server che gestisce i dati)
│ └── server.js 
│
├── pdf/ (Generazione dei PDF per la stampa delle nomine)
│ ├── app.yaml 
│ ├── main.py
│ └── requirements.txt
│
├── public/
│ └── ... (File statici)
│
├── src/
│ └── ... (Applicazione React)
│
├── package.json
├── package-lock.json
├── app.yaml
└── dispatch.yaml
```

# Installazione
## Sviluppo
Per installare l'applicazione è necessario clonare il repository
e installare le dipendenze. E' necessario avere:
* Node.js e npm
* Python e pip


L'applicazione react può coordinare tutto il progetto. Per installare:
```bash
$ npm install
$ cd backend && npm install && cd ..
$ cd pdf && pip install -r requirements.txt && cd ..
```

Per avviare l'applicazione in modalità sviluppo avviando tutti e tre i servizi:
```bash
$ npm run dev
```

Se si vuole avviare solo l'applicazione React:
```bash
$ npm start
```

Se si vuole avviare solo il server API:
```bash
$ npm run backend
```

Se si vuole avviare solo il server PDF:
```bash
$ npm run pdf
```


## Produzione
Per installare l'applicazione in produzione è necessario avere un account
Google Cloud e creare un progetto. Una volta creato il progetto basta
eseguire il comando:
```bash
$ npm run deploy
$ cd pdf && gcloud app deploy && cd ..
$ gcloud app deploy dispatch.yaml
```

Questo comando creerà un'applicazione su Google App Engine e la renderà
disponibile all'indirizzo `https://<project-id>.appspot.com`.


TODO: Gestire i secrets con Google Secret Manager
```bash
$ gcloud secrets create <secret-name> --replication-policy automatic
$ gcloud secrets versions add <secret-name> --data-file <file>
```

---

## 🤖 AI Assistant (Nuovo!)

AInaudi ora include un assistente AI basato su **Gemini 2.0 Flash** per supportare gli RDL durante le operazioni elettorali.

### Features
- 💬 Chat testuale + 🎤 input vocale (Web Speech API)
- 📚 RAG (Retrieval-Augmented Generation) su FAQ e documenti
- 🇮🇹 Deployment su Vertex AI Milano (GDPR compliant)
- ⚡ Ingestion automatica via Django signals
- 📍 Risposte con fonti citate

### Quick Start (3 minuti)

```bash
# 1. Setup automatico Google Cloud
./scripts/setup-vertex-ai.sh ainaudi-prod

# 2. Build e avvia Docker
docker-compose build --no-cache backend
docker-compose up -d

# 3. Test
docker-compose exec backend python manage.py shell
```

**Documentazione completa:**
- [QUICK_START_AI.md](./QUICK_START_AI.md) - Setup rapido in 3 minuti
- [VERTEX_AI_SETUP.md](./VERTEX_AI_SETUP.md) - Guida completa per sviluppo e produzione

### Costi
- **Sviluppo**: ~$0.10/giorno (primi 100 test gratis)
- **Produzione**: ~$50-100/mese (1000 utenti, 10 domande/giorno)
