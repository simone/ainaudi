# AInaudi - Piattaforma Gestione Elettorale

> **La soluzione completa per organizzare, coordinare e monitorare i Rappresentanti di Lista**

---

## Il Problema

Organizzare una consultazione elettorale richiede:
- Reclutare centinaia di volontari come Rappresentanti di Lista (RDL)
- Gestire una complessa catena di deleghe secondo normativa
- Assegnare ogni RDL a una specifica sezione elettorale
- Raccogliere i dati dello scrutinio in tempo reale da migliaia di seggi
- Coordinare il tutto rispettando le gerarchie territoriali

**Tutto questo, spesso, viene gestito con fogli Excel, gruppi WhatsApp e telefonate.**

---

## La Soluzione: AInaudi

**AInaudi** è una piattaforma web mobile-first che trasforma la complessità della gestione elettorale in un processo guidato, semplice e replicabile.

### La Parola Chiave: Semplificazione

Ogni consultazione elettorale è diversa, ma i problemi sono sempre gli stessi: chi coordina cosa? Come si fa questa cosa? A chi devo chiedere? Dove trovo quel documento?

AInaudi risolve questi problemi **proceduralizzando** l'intero iter amministrativo:

| Problema | Soluzione AInaudi |
|----------|-------------------|
| *"Non so cosa devo fare"* | Flusso guidato step-by-step per ogni ruolo |
| *"Non trovo le informazioni"* | Knowledge base centralizzata con FAQ e documenti |
| *"Devo spiegare tutto da capo"* | La piattaforma insegna, tu coordini |
| *"Ogni territorio fa a modo suo"* | Processo uniforme per tutti, dall'Alto Adige alla Sicilia |
| *"Non so a che punto siamo"* | Dashboard in tempo reale con stato avanzamento |

### Come Funziona

1. **Configuri una volta** → La consultazione, le schede, i territori
2. **La piattaforma guida tutti** → Ogni utente vede solo ciò che deve fare
3. **I dati confluiscono** → Un unico punto di verità, aggiornato in tempo reale
4. **Tu monitori** → Sai sempre chi ha fatto cosa, dove mancano RDL, come procede lo scrutinio

### Basta Rincorse

Con AInaudi non devi più:
- Formare ogni volta centinaia di coordinatori territoriali
- Rispondere alle stesse domande su 15 gruppi WhatsApp diversi
- Rincorrere i dati dello scrutinio con telefonate notturne
- Ricostruire cosa è successo quando qualcosa va storto

**La conoscenza è nella piattaforma**, non nella testa di pochi. Quando un coordinatore cambia, il nuovo trova tutto pronto: procedure, documenti, storico.

### Accesso Semplificato
- **Login senza password** tramite Magic Link via email
- Niente da ricordare: ricevi un link, clicchi, sei dentro
- Funziona su qualsiasi dispositivo: smartphone, tablet, PC

![Login Magic Link](Login%20-%20Via%20Magic%20Link.png)

---

## I 6 Moduli della Piattaforma

![Dashboard Moduli 1-3](Dashboard%20-%20Moduli%201-3.png)
![Dashboard Moduli 4-6](Dashboard%20-%20Moduli%204-6.png)

### 1. Territorio (Amministratori)
**Gestione completa dei dati territoriali italiani**

- 20 Regioni, 107 Province, 7.896 Comuni, 61.559 Sezioni elettorali
- Import massivo via CSV per aggiornamenti rapidi
- Gestione Municipi per le grandi città (Roma, Milano, Napoli...)

![Territorio](Territorio%20-%20Regioni%20-%20Provincie%20-%20Comuni%20-%20Sezioni.png)

### 2. Consultazione
**Configurazione delle schede elettorali**

- Supporto multi-scheda: Referendum, Europee, Politiche, Comunali
- Configurazione quesiti, liste e candidati
- Colori e denominazioni per ogni scheda

![Consultazione](Consultazione%20-%20Configurazione%20Scheda%20Elettorale.png)

### 3. Delegati
**Gestione della catena delle deleghe secondo normativa**

La piattaforma rispetta la gerarchia prevista dalla legge:

```
COMITATO PROMOTORE / PARTITO
         ↓ mandato autenticato
DELEGATO DI LISTA (deputati, consiglieri)
         ↓ sub-delega
SUB-DELEGATO (per territorio)
         ↓ designa
RDL (Effettivo + Supplente)
```

- Visualizzazione chiara della propria posizione nella catena
- Note normative integrate (L. 352/1970, DPR 361/1957)
- Generazione automatica documenti PDF

![Delegati](Delegati%20-%20Catena%20Deleghe.png)

### 4. RDL - Gestione Rappresentanti di Lista
**Reclutamento, approvazione e assegnazione**

#### Campagne di Reclutamento
Crea link pubblici personalizzati per raccogliere candidature:
- Link condivisibili sui social e via WhatsApp
- Scadenza automatica configurabile
- Filtro per territorio (regione, provincia, comune)
- Contatore registrazioni in tempo reale

![Campagne](RDL%20-%20Campagne%20di%20Reclutamento.png)

#### Pagina di Auto-Candidatura
Form pubblico ottimizzato per la conversione:
- "Vuoi fare la differenza? Diventa Rappresentante di Lista"
- Registrazione in 2 minuti
- Nessun requisito particolare richiesto

![Auto-candidatura](RDL%20-%20Auto%20candidature%20-%20Modulo%20Standard.png)

#### Gestione e Approvazione
- Lista candidature con filtri per stato e territorio
- Approvazione/rifiuto con un click
- Dettaglio completo di ogni candidato

![Gestione RDL](RDL%20-%20Gestione-Approvazione.png)

#### Mappatura RDL-Sezioni
Assegnazione operativa degli RDL alle sezioni elettorali:
- Vista per Plesso (edificio scolastico) o per Lista
- Selezione multipla per assegnazioni rapide
- Distinzione Effettivo/Supplente
- Contatori in tempo reale: assegnati vs da assegnare

![Mappatura](RDL%20-%20Mappatura%20Plessi-Sezioni.png)

### 5. Scrutinio
**Inserimento dati votazioni mobile-first**

L'RDL inserisce i dati direttamente dal seggio:

#### Lista Sezioni Assegnate
- Raggruppamento per plesso (edificio)
- Barra di progresso per ogni sezione
- Ricerca rapida per numero, città, indirizzo

![Scrutinio Lista](Scrutinio%20-%20Lista%20Plessi-Sezoni%20assegnate%20agli%20RDL.png)

#### Wizard Inserimento Dati
Interfaccia touch-friendly con:
- **Step 1**: Dati seggio (elettori iscritti, votanti, affluenza)
- **Step 2+**: Voti per ogni scheda elettorale
- Salvataggio automatico ad ogni passaggio
- Navigazione semplice: Indietro/Avanti

![Dati Seggio](Scrutinio%20-%20Dati%20seggio.png)

#### Schede Referendum
Input dedicato per SI/NO con:
- Schede bianche, nulle, contestate
- Schede ricevute vs autenticate
- Validazione automatica dei totali

![Scheda Referendum](Scrutinio%20-%20Scheda%20Elettorale.png)

### 6. Assistenza
**Centro di supporto integrato**

- **Documenti**: Guide operative, modulistica ufficiale
- **FAQ**: Risposte alle domande frequenti per categoria
- **Ricerca**: Trova rapidamente quello che cerchi

![Assistenza](Assistenza%20-%20FAQ.png)

---

## Caratteristiche Tecniche

### Sicurezza
- Autenticazione Magic Link (no password da gestire)
- Permessi basati su catena deleghe
- Ogni utente vede solo il proprio territorio

### Mobile-First
- Interfaccia ottimizzata per smartphone
- Touch target minimi 44px (WCAG)
- Funziona anche con connessione lenta

### Scalabilità
- Gestisce migliaia di sezioni e RDL
- Paginazione intelligente
- Aggiornamenti in tempo reale

### Conformità Normativa
- Rispetta L. 352/1970 (Referendum)
- Rispetta DPR 361/1957 (Elezioni)
- Gerarchia deleghe conforme

---

## Casi d'Uso

| Consultazione | Schede | Sezioni | RDL necessari |
|---------------|--------|---------|---------------|
| Referendum Costituzionale | 1-5 | 61.559 | ~120.000 |
| Elezioni Europee | 1 | 61.559 | ~120.000 |
| Elezioni Comunali Roma | 1-2 | 2.603 | ~5.000 |
| Elezioni Regionali Lazio | 1 | ~5.000 | ~10.000 |

---

## Perché AInaudi?

| Prima | Dopo |
|-------|------|
| Fogli Excel condivisi | Database centralizzato |
| Gruppi WhatsApp caotici | Flusso di lavoro strutturato |
| Telefonate per raccogliere dati | Inserimento diretto da smartphone |
| Risultati il giorno dopo | Dashboard in tempo reale |
| Errori di trascrizione | Validazione automatica |
| Nessuna tracciabilità | Audit log completo |

---

## Next Steps - Il Futuro della Piattaforma

### Segnalazione Anomalie Guidata

**Problema attuale**: Quando un RDL nota un'irregolarità al seggio, spesso non sa:
- Se è effettivamente un'anomalia rilevante
- Come documentarla correttamente
- Quali passi seguire per contestarla
- Cosa scrivere esattamente nel verbale

**Soluzione in arrivo**:

#### 1. Wizard Segnalazione Anomalie
Flusso guidato passo-passo:

```
1. COSA È SUCCESSO?
   → Selezione da categorie:
     • Elettore senza documento
     • Scrutatori che contano male
     • Presidente assente
     • Urna non sigillata
     • Brogli evidenti
     • Altro...

2. QUANDO E DOVE?
   → Timestamp automatico
   → Foto/video opzionali
   → Sezione pre-compilata

3. TESTIMONI
   → Chi altro ha visto?
   → Dati di altri presenti

4. AZIONI IMMEDIATE
   → Hai già contestato?
   → Hai firmato il verbale con riserva?
```

#### 2. Assistente AI Integrato

L'**AI Assistant** conosce:
- Tutta la normativa elettorale (DPR 361/1957, L.352/1970)
- Precedenti casi simili
- Best practice dal campo
- Modulistica ufficiale

**Cosa fa l'AI**:

**Durante la Segnalazione**
```
RDL: "Il presidente non vuole farmi entrare"

AI: 🤖 Questo è un diritto garantito dall'art. 25 DPR 361/1957.

    COSA FARE ORA:
    1. Mostra il tuo documento di rappresentante
    2. Cita l'articolo 25 (te lo dico io)
    3. Se insiste, chiama i Carabinieri
    4. Documenta tutto con una foto

    COSA SCRIVERE A VERBALE:
    "Il sottoscritto rappresentante di lista,
    regolarmente designato ai sensi dell'art. 25
    DPR 361/1957, è stato impedito nell'accesso
    al seggio dal Presidente ore [HH:MM].
    Protesto formalmente e mi riservo ogni azione."
```

**Suggerimenti Contestuali**
```
Scenario: RDL segnala urna non sigillata all'apertura

AI: 🚨 ANOMALIA GRAVE - Intervento immediato necessario

    GRAVITÀ: Alta
    URGENZA: Massima (prima del voto)

    PASSI DA SEGUIRE:

    1. FOTO IMMEDIATA
       Scatta foto dell'urna non sigillata PRIMA che
       qualcuno la tocchi

    2. RICHIESTA FORMALE
       "Chiedo formalmente la sostituzione dell'urna
       ai sensi dell'art. X. Sospendo le operazioni
       fino a sigillatura regolare."

    3. VERBALE
       "Alle ore [HH:MM] urna elettorale priva di
       sigilli regolamentari. Richiesta sostituzione
       ai sensi art. X DPR 361/1957. Operazioni
       sospese fino a regolarizzazione."

    4. ESCALATION
       Se il presidente rifiuta → Chiama Prefettura
       Numero: [XXX]

    ⚠️ NON permettere l'inizio delle votazioni
       con urna non sigillata: il voto sarebbe nullo.
```

**Dopo lo Scrutinio**
```
RDL: "Ho notato che hanno contato male le schede bianche"

AI: Hai già firmato il verbale?

    [SÌ] → Troppo tardi per contestare il conteggio,
           ma puoi:
           1. Segnalare tramite canali ufficiali
           2. Documentare per ricorso

    [NO] → PERFETTO! Prima di firmare:
           1. Chiedi un riconteggio pubblico
           2. Se confermato l'errore, fai correggere
           3. Se rifiutano, scrivi a verbale:
              "Il sottoscritto contesta il conteggio
               delle schede bianche che risulta
               [NUMERO] invece di [NUMERO CORRETTO].
               Firma con riserva."
```

#### 3. Knowledge Base Dinamica

L'AI impara da ogni segnalazione:
- Anomalie più frequenti per territorio
- Soluzioni che hanno funzionato
- Casistiche nuove da condividere

**Dashboard Coordinatori**:
- "Nelle ultime 3 ore: 12 segnalazioni su urne non sigillate a Roma"
- "Alert pattern: 5 seggi stessa zona, stessa anomalia"
- "Suggerimento: invia comunicazione preventiva ai presidenti"

#### 4. Escalation Automatica

Quando necessario, l'AI allerta automaticamente:
- Coordinatore territoriale
- Delegato di lista
- Ufficio legale (per casi gravi)

Con tutti i dettagli già pronti per l'intervento.

---

### Perché Questo Cambia Tutto

| Oggi | Con AI Assistant |
|------|------------------|
| RDL confuso, non sa cosa fare | Guida passo-passo in tempo reale |
| "Devo chiamare qualcuno" | Risposta immediata, 24/7 |
| Dimenticanze, errori | Checklist automatica |
| Contestazioni improvvisate | Testo normativo pronto da copiare |
| Anomalie ignorate | Riconoscimento automatico gravità |
| Learning lento | Esperienza condivisa istantaneamente |

**Risultato**:
- Meno telefonate di panico ai coordinatori
- Più anomalie documentate correttamente
- Contestazioni più efficaci
- RDL più sicuri e preparati

---

## Contatti

**AInaudi** - Piattaforma Gestione Elettorale

© Simone Federici - Gratuito per il Movimento 5 Stelle

---

*Screenshots dalla versione demo - Referendum Costituzionale Giustizia 2026*
