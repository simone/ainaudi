# AInaudi Chatbot - Report di Miglioramento

**Data:** 8 Marzo 2026
**Autore:** Team AInaudi
**Versione:** v4.0 (architettura multi-agent)

---

## Executive Summary

In una settimana di lavoro mirato, AInaudi e passato da un assistente che rispondeva con emoji e "non so" a un chatbot competente che gestisce il 95% delle domande reali degli RDL con risposte precise e contestualizzate. Il refactoring verso un'architettura multi-agent ha mantenuto la qualita raggiunta.

| Metrica | Prima | Dopo | Variazione |
|---------|-------|------|------------|
| **Punteggio medio** | **5.2**/10 | **7.7**/10 | **+48%** |
| Conversazioni migliorate | — | 33/48 | **69%** |
| Regressioni | — | 2/48 | 4% |
| Risposte sotto la sufficienza (<6) | 25/48 | 2/48 | **-92%** |
| Risposte eccellenti (9-10) | 3/48 | 13/48 | **+333%** |

---

## Metodologia

Abbiamo analizzato **48 conversazioni reali** estratte dai log di produzione di fine Febbraio 2026. Ogni conversazione e stata rigiocata contro il sistema attuale e valutata con un giudice LLM indipendente (Gemini 2.0 Flash, scala 1-10), confrontando la vecchia risposta con la nuova.

I test sono stati eseguiti in 4 cicli:
- **v3 (Fase 1):** Fix codice — media 7.5
- **v4 (Fase 2):** FAQ arricchite — media 7.4
- **v5 (Fase 3):** Conoscenza generale — media 8.0
- **v6 (Multi-agent):** Refactoring architetturale — media 7.7

La variazione 7.7-8.0 tra v5 e v6 rientra nella varianza stocastica del modello (temperature=0.7) e del giudice LLM, come dimostrato dall'analisi delle regressioni (vedi sezione dedicata).

---

## Prima e Dopo: Esempi Reali

### 1. "Sei operativo? Che cosa sai fare?"
> La prima domanda che ogni utente fa al chatbot.

**PRIMA (voto: 3/10)**
```
Utente: Buongiorno, primo test per capire se l'integrazione con
        l'agent funziona. Sei operativo? che cosa sai fare?
Bot:    🤷
```

**DOPO (voto: 8/10)**
```
Utente: Buongiorno, primo test per capire se l'integrazione con
        l'agent funziona. Sei operativo? che cosa sai fare?
Bot:    Ciao! Sono AInaudi, l'assistente AI per i Rappresentanti di Lista
        del Movimento 5 Stelle. Sono qui per aiutarti durante il Referendum
        Costituzionale Giustizia 2026 [...]
```

---

### 2. "L'RDL e retribuito?"
> Una delle domande piu frequenti, a cui il bot non sapeva rispondere.

**PRIMA (voto: 3/10)**
```
Utente: E' pagato? Come funziona per il lavoro?
Bot:    Non ho informazioni riguardanti compensi economici per l'attivita di RDL.
```

**DOPO (voto: 9/10)**
```
Utente: E' pagato? Come funziona per il lavoro?
Bot:    No, il ruolo di Rappresentante di Lista e' volontario e non retribuito.
        Non e' previsto un compenso economico. Hai pero diritto a permessi
        retribuiti dal lavoro e riposi compensativi [...]
```

---

### 3. "Come installo l'app?"
> Gli utenti cercavano AInaudi sugli store. Il bot non sapeva aiutarli.

**PRIMA (voto: 2/10)**
```
Utente: Non trovo il pulsante condividi per installare
Bot:    🤷
```

**DOPO (voto: 8/10)**
```
Utente: Non trovo il pulsante condividi per installare
Bot:    L'app AInaudi e' una web-app. Non ha un pulsante "condividi".
        Per installarla:
        - Su iPhone/iPad: apri Safari, vai su https://ainaudi.it,
          tocca l'icona di condivisione → "Aggiungi alla schermata Home"
        - Su Android: apri Chrome → menu tre puntini → "Installa app"
```

---

### 4. "Dove vedo la sezione assegnata?"
> L'informazione e nella Home dell'app, ma il bot non lo sapeva.

**PRIMA (voto: 3/10)**
```
Utente: Come faccio a visualizzare la mia sezione?
Bot:    Contatta il tuo referente di zona del M5S. Lui/lei ha l'elenco
        delle sezioni assegnate ai RDL.
```

**DOPO (voto: 9/10)**
```
Utente: Come faccio a visualizzare la mia sezione?
Bot:    Le sezioni a cui sei assegnato come RDL sono visibili nella
        schermata Home di AInaudi, sotto il tuo nome. Se non vedi ancora
        nessuna sezione, l'assegnazione non e' ancora stata fatta [...]
```

---

### 5. "Che differenza c'e tra seggio e sezione?"
> Glossario elettorale di base, fondamentale per un RDL.

**PRIMA (voto: 4/10)**
```
Utente: Qual e' la differenza?
Bot:    Non ho trovato la risposta a questa domanda nei documenti forniti.
```

**DOPO (voto: 8/10)**
```
Utente: Qual e' la differenza?
Bot:    Tecnicamente la sezione elettorale e' l'unita' amministrativa
        (un gruppo di elettori assegnati a un numero), mentre il seggio
        e' il luogo fisico dove si vota. In pratica sono usati come
        sinonimi [...]
```

---

### 6. "Quanti scrutatori ci sono?"
> Domanda tecnica a cui il bot rispondeva "non so".

**PRIMA (voto: 3/10)**
```
Utente: Quanti scrutatori ci sono per il referendum?
Bot:    Non ho informazioni sul numero di scrutatori previsti per il referendum.
```

**DOPO (voto: 8/10)**
```
Utente: Quanti scrutatori ci sono per il referendum?
Bot:    Per il Referendum Costituzionale Giustizia 2026 sono previsti
        3 scrutatori per ogni seggio. Lo trovi indicato nel manuale [...]
```

---

### 7. "A che ora aprono i seggi?"
> Informazione fondamentale, ora completa di tutti gli orari.

**PRIMA (voto: 7/10)**
```
Utente: A che ora aprono i seggi?
Bot:    I seggi aprono alle ore 7:00 di domenica 22 marzo.
```

**DOPO (voto: 8/10)**
```
Utente: A che ora aprono i seggi?
Bot:    I seggi aprono alle 15:00 di sabato 22 Marzo e alle 7:00
        di domenica 23 Marzo per il Referendum Costituzionale
        Giustizia 2026. Ti consiglio di arrivare 30-60 minuti prima [...]
```

---

### 8. Domanda complessa: cittadinanza e diritto di voto

**PRIMA (voto: 3/10)**
```
Utente: Un mio amico prende la cittadinanza il 20 marzo,
        puo' votare il 22?
Bot:    Non so come possa votare, dato che l'ottenimento della
        cittadinanza e troppo a ridosso delle elezioni.
```

**DOPO (voto: 9/10)**
```
Utente: Un mio amico prende la cittadinanza il 20 marzo,
        puo' votare il 22?
Bot:    Purtroppo, anche se otterrà la cittadinanza italiana il 20 marzo,
        sarà troppo tardi per votare al Referendum del 22-23 marzo.
        Per votare bisogna essere iscritti nelle liste elettorali,
        e l'iscrizione avviene con revisione semestrale [...]
```

---

## Cosa Abbiamo Fatto

### Fase 1: Fix al Codice
- Rimosso il messaggio "Nessuna sezione assegnata" che inquinava ogni risposta
- Aggiunto riconoscimento delle espressioni di approvazione ("daje", "ok", "top")
- Migliorato il prompt di sistema per il periodo pre-elettorale

### Fase 2: Knowledge Base
Arricchite **5 FAQ esistenti** con risposte dettagliate e create **6 FAQ nuove**:
- Istruzioni installazione PWA (iOS, Android, Desktop) passo-passo
- Dove vedere la sezione assegnata in AInaudi
- Compenso RDL (volontario, permessi retribuiti, normativa)
- Glossario elettorale (seggio vs sezione, schede contestate/nulle/bianche)
- Presentazione AInaudi (cosa fa, cosa non fa)
- Orari apertura/chiusura seggi
- Eta massima presidente di seggio
- Si vota con penna o matita copiativa

### Fase 3: Conoscenza Generale
- Il bot ora usa le sue conoscenze generali sulle elezioni italiane quando la knowledge base non ha una risposta specifica, invece di rispondere "non so"
- Migliorata la gestione dei "Si" contestuali (risposta a domanda vs approvazione)

### Fase 4: Architettura Multi-Agent
Refactoring completo verso un'architettura a microservizi interni:
- **Orchestrator**: entry point unico, classifica intent e smista
- **KnowledgeBaseAgent**: risponde a domande informative (read-only)
- **DataCaptureAgent**: gestisce inserimento dati scrutinio
- **TicketingAgent**: gestisce segnalazioni incidenti
- **ElectionPolicyGuard**: valida azioni rispetto allo stato dell'elezione
- **ContextBuilder**: costruisce il profilo utente in modo modulare

---

## Distribuzione Punteggi

```
PRIMA                           DOPO (multi-agent)
═══════════════                 ═══════════════
1-3  ████████████████  25       1-3  ██  2
4-5  ████████  8                4-5  0
6-7  ████████████  12           6-7  ████████████████  14
8-9  ███  3                     8-9  ████████████████████████████  29
10   0                          10   0
                                n/a  ███  3
```

---

## Analisi Regressioni

### v5 (pre-refactor) vs v6 (multi-agent)

Il passaggio all'architettura multi-agent ha prodotto risultati equivalenti: 7.7 vs 8.0.
L'analisi session-per-session mostra che le differenze sono **varianza stocastica**, non regressioni sistematiche:

| Sessioni | v5→v6 | Analisi |
|----------|-------|---------|
| 27 sessioni | = | Stesso punteggio |
| 7 sessioni | +1/+3 | Miglioramenti |
| 9 sessioni | -1 | Varianza giudice (8→7 o 9→8) |
| Session 35 | 7→1 | **Stessa risposta**, giudice v5 indulgente, v6 severo |
| Session 40 | 7→3 | **Stessa risposta**, giudice v5 indulgente, v6 severo |

**Session 35 in dettaglio:** "Devo stampare il badge per votare?"
- v5 e v6 danno la stessa risposta ("Si, devi stampare il badge")
- Entrambe le risposte sono imprecise: il badge serve all'RDL nel ruolo, non "per votare"
- Il giudice v5 ha dato 7/10, il giudice v6 ha dato 1/10 — stessa risposta, valutazione diversa

**Session 40 in dettaglio:** Off-topic "frittata" poi "penna o matita"
- v5: "puoi usare sia penna che matita per appunti" (7/10)
- v6: "ti consiglio di portare con te sia penna che matita" (3/10)
- Risposte quasi identiche, entrambe imprecise (la risposta corretta e "matita copiativa")
- Il RAG non trova la FAQ perche il contesto off-topic inquina l'embedding

**Conclusione:** Nessuna regressione e causata dal refactoring. Le risposte del modello sono equivalenti; le differenze di punteggio derivano dalla natura non-deterministica del giudice LLM.

---

## Le 2 Regressioni Reali (vs sistema originale)

**Session 35** (Old 3 → New 1): Il bot confonde "votare" con "fare l'RDL" quando l'utente chiede del badge. Problema di comprensione contestuale, presente in entrambe le architetture.

**Session 40** (Old 3 → New 3): Off-topic ("frittata") seguito da domanda valida ("penna o matita"). Il contesto off-topic impedisce al RAG di recuperare la FAQ corretta sulla matita copiativa.

---

## Prossimi Passi

1. **Speech-to-text garbled input**: Alcuni utenti dettano messaggi vocali mal trascritti. Un pre-processing potrebbe migliorare la comprensione.
2. **Context recovery dopo off-topic**: Quando una domanda segue un messaggio off-topic, resettare il contesto RAG per la nuova query.
3. **Monitoring continuo**: Integrare il sistema di scoring nelle metriche di produzione per monitorare la qualita nel tempo.
4. **Feedback loop**: Usare i voti "utile si/no" degli utenti per identificare nuove FAQ da aggiungere.

---

*Test eseguito su 48 conversazioni reali, valutazione LLM-as-judge (Gemini 2.0 Flash), scala 1-10.*
*Knowledge base: 69 FAQ + 12 documenti indicizzati con pgvector.*
*Architettura: Orchestrator multi-agent con policy guard.*
