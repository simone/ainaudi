# Sistema RDL - Responsabile Di Lista
## Documentazione Tecnica e Funzionale - Versione 2026

---

## Indice

1. [Executive Summary](#1-executive-summary)
2. [Panoramica del Sistema](#2-panoramica-del-sistema)
3. [Cosa è Cambiato dalla Versione 2024](#3-cosa-è-cambiato-dalla-versione-2024)
4. [Architettura Tecnica](#4-architettura-tecnica)
5. [Data Model Completo](#5-data-model-completo)
6. [Nuove Funzionalità](#6-nuove-funzionalità)
7. [Miglioramenti Tecnici](#7-miglioramenti-tecnici)
8. [Flussi Operativi](#8-flussi-operativi)
9. [Sicurezza e Compliance](#9-sicurezza-e-compliance)
10. [Deployment e Scalabilità](#10-deployment-e-scalabilità)

---

## 1. Executive Summary

Il sistema **RDL (Responsabile Di Lista)** è la piattaforma tecnologica del Movimento 5 Stelle per la gestione completa del ciclo elettorale italiano. Copre l'intera catena di delega prevista dal DPR 361/1957 Art. 25, dalla nomina dei Delegati di Lista fino alla raccolta dei dati di voto nelle singole sezioni elettorali.

### Obiettivi Principali

- **Gestione della catena di delega**: Delegato → Sub-Delegato → RDL
- **Raccolta dati elettorali** in tempo reale dalle sezioni
- **Generazione automatica** della documentazione legale (designazioni, deleghe)
- **Dashboard KPI** per il monitoraggio dell'affluenza e dei risultati
- **Gestione multi-consultazione**: supporto simultaneo di Referendum, Europee, Politiche e Comunali
- **Supporto ballottaggio**: gestione automatica primo turno / secondo turno

### La Trasformazione 2024 → 2026

| Aspetto | Versione 2024 | Versione 2026 |
|---------|---------------|---------------|
| Backend | Node.js + Express | **Django REST Framework** |
| Database | Google Sheets API | **PostgreSQL 15** |
| Autenticazione | Google OAuth | **Magic Link** (passwordless) |
| Deleghe | Gestione manuale | **Catena digitale completa** |
| Documenti | Generazione manuale | **PDF automatici** con catena deleghe |
| Caching | NodeCache | **Redis** |
| Ruoli | Semplici (RDL/Admin) | **RBAC territoriale granulare** |
| Campagne | Google Form | **Sistema integrato** |
| Ballottaggio | Manuale | **Automatico per data** |

---

## 2. Panoramica del Sistema

### 2.1 Contesto Normativo

Il sistema implementa la gerarchia elettorale italiana secondo il **DPR 361/1957**:

```
PARTITO (Movimento 5 Stelle)
        │
        │ nomina formale
        ▼
┌─────────────────────────────────────────────────────────────┐
│  DELEGATO DI LISTA                                          │
│  (Deputati, Senatori, Consiglieri Regionali, Eurodeputati)  │
│  Può nominare direttamente gli RDL o delegare               │
└─────────────────────────────────────────────────────────────┘
        │
        │ sub-delega
        ▼
┌─────────────────────────────────────────────────────────────┐
│  SUB-DELEGATO                                               │
│  Responsabile di un territorio (Regione/Provincia/Comune)   │
│                                                             │
│  Due modalità di sub-delega:                                │
│                                                             │
│  • FIRMA AUTENTICATA: Il Sub-Delegato ha firma autenticata  │
│    da notaio o funzionario comunale. Può designare gli RDL  │
│    direttamente senza ulteriore approvazione del Delegato.  │
│    Le designazioni diventano immediatamente CONFERMATE.     │
│                                                             │
│  • MAPPATURA: Il Sub-Delegato NON ha firma autenticata.     │
│    Può preparare le designazioni RDL come BOZZE, ma queste  │
│    devono essere approvate dal Delegato per diventare       │
│    CONFERMATE. Utile per delegare il lavoro operativo       │
│    mantenendo il controllo formale.                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
        │
        │ designazione
        ▼
┌─────────────────────────────────────────────────────────────┐
│  RDL (Responsabile Di Lista)                                │
│  Presente al seggio il giorno delle elezioni                │
│  Raccoglie e inserisce i dati di voto                       │
│  - Effettivo: presente allo scrutinio                       │
│  - Supplente: disponibile in caso di impedimento            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Ambito Funzionale

Il sistema gestisce:

1. **Territorio**: 20 Regioni → 107 Province → 7.896 Comuni → ~61.000 Sezioni Elettorali
2. **Elezioni**: Referendum, Europee, Politiche (Camera/Senato), Regionali, Comunali, Municipali
3. **Utenti**: Circa 500 Delegati, 5.000 Sub-Delegati, 60.000+ RDL potenziali
4. **Dati**: Elettori, votanti, schede, voti per lista/candidato per ogni sezione

---

## 3. Cosa è Cambiato dalla Versione 2024

### 3.1 Migrazione Architetturale Completa

#### Prima (2024): Stack Node.js + Google Sheets

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React UI   │────▶│  Express.js  │────▶│Google Sheets │
│   (SPA)      │     │  + NodeCache │     │   (Database) │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Limitazioni della versione 2024:**

- **Google Sheets come database**: Limiti di quota API (100 requests/100 secondi per utente), impossibilità di query complesse, nessun indice, nessuna transazione
- **Caching in-memory**: NodeCache non persistente, perso al restart del server
- **Task Queue manuale**: Per evitare race conditions sulle scritture
- **Nessun modello di dominio**: Dati destrutturati in fogli di calcolo
- **Audit limitato**: Difficile tracciare chi ha fatto cosa
- **Scalabilità**: Single instance, nessun load balancing reale

#### Dopo (2026): Stack Django + PostgreSQL

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React UI   │────▶│    Django    │────▶│  PostgreSQL  │
│   (SPA)      │     │  REST + ORM  │     │    + Redis   │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
        │                   ├──▶ Django Admin
        │                   └──▶ Background Tasks
        │
        └──▶ Docker Compose (dev) / Cloud Run (prod)
```

### 3.2 File Eliminati dal Vecchio Backend

Il seguente codice Node.js è stato completamente rimosso:

| File | Funzione Originale | Sostituito da |
|------|-------------------|---------------|
| `backend/server.js` | Entry point Express | `backend_django/config/` |
| `backend/modules/election.js` | API elezioni | `elections/` app Django |
| `backend/modules/rdl.js` | Registrazioni RDL | `campaign/` app Django |
| `backend/modules/section.js` | Dati sezioni | `sections/` app Django |
| `backend/modules/kpi.js` | Dashboard KPI | `kpi/` app Django |
| `backend/modules/react.js` | Utility React | Non necessario |
| `backend/queue.js` | Task queue | PostgreSQL transactions |
| `backend/query.js` | Query builder Sheets | Django ORM |
| `backend/tools.js` | Utilities | Django utilities |

### 3.3 Confronto Dettagliato delle Funzionalità

| Funzionalità | 2024 | 2026 | Miglioramento |
|--------------|------|------|---------------|
| **Autenticazione** | Google OAuth | Magic Link (passwordless) | UX semplificata, no account Google richiesto |
| **Ruoli** | 2 (RDL, Admin) | 6 con scope territoriale | Granularità completa |
| **Deleghe** | Non gestite | Catena completa digitale | Nuovo |
| **Documenti** | PDF manuali | Generazione automatica | Automazione 100% |
| **Multi-elezione** | Una alla volta | N elezioni per consultazione | Flessibilità |
| **Audit** | Log base | AuditLog completo con IP | Compliance GDPR |
| **Performance** | ~50 req/s | ~500 req/s (stima) | 10x improvement |
| **Offline** | Nessuno | Cache client + retry | Resilienza |
| **Incident** | Email manuale | Sistema integrato | Tracking completo |
| **Campagne RDL** | Google Form | Sistema integrato | Workflow completo |
| **Ballottaggio** | Manuale | Automatico per data | Automazione turni |

---

## 4. Architettura Tecnica

### 4.1 Stack Tecnologico

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  React 18.x          │  Componenti UI, routing, state          │
│  Client.js           │  API client con cache e retry           │
│  AuthContext.js      │  Gestione JWT Magic Link                │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTPS/JSON
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                  │
├─────────────────────────────────────────────────────────────────┤
│  Django 4.x          │  Framework web Python                   │
│  DRF 3.x             │  REST API, Serializers, Permissions     │
│  PostgreSQL 15       │  Database relazionale ACID              │
│  Redis 7.x           │  Caching, sessions                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                              │
├─────────────────────────────────────────────────────────────────┤
│  Docker Compose      │  Orchestrazione sviluppo                 │
│  Google Cloud Run    │  Container serverless produzione        │
│  Cloud SQL           │  PostgreSQL managed                      │
│  Cloud Storage       │  File statici e documenti               │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Struttura Django Apps

Il backend Django è organizzato in 11 applicazioni modulari:

```
backend_django/
├── config/                           # Configurazione Django
│   ├── settings.py                   # Settings principale
│   ├── urls.py                       # URL routing
│   └── wsgi.py                       # Entry point produzione
│
├── core/                             # "Utenti e Autenticazione"
│   ├── models.py                     # User, RoleAssignment, AuditLog
│   ├── views.py                      # Auth views (Magic Link)
│   └── permissions.py                # Custom permissions
│
├── territory/                        # "Territorio"
│   ├── models.py                     # Regione, Provincia, Comune, Municipio
│   │                                 # SezioneElettorale, TerritorialPartition*
│   └── views.py                      # Endpoints con filtri cascade
│
├── elections/                        # "Consultazioni elettorali"
│   ├── models.py                     # ConsultazioneElettorale, TipoElezione
│   │                                 # SchedaElettorale, ListaElettorale
│   │                                 # Candidato, *PartitionBinding
│   └── views.py                      # CRUD elezioni
│
├── delegations/                      # "Deleghe"
│   ├── models.py                     # DelegatoDiLista, SubDelega
│   │                                 # DesignazioneRDL, BatchGenerazione
│   ├── signals.py                    # Auto-provisioning utenti
│   └── views.py                      # API deleghe
│
├── campaign/                         # "Campagne e Registrazioni"
│   ├── models.py                     # CampagnaReclutamento, RdlRegistration
│   └── views.py                      # API campagne pubbliche
│
├── data/                             # "Raccolta Dati"
│   ├── models.py                     # SectionAssignment, DatiSezione
│   │                                 # DatiScheda, SectionDataHistory
│   ├── signals.py                    # Auto-creazione ruoli RDL
│   └── views.py                      # API sezioni e dati
│
├── incidents/                        # "Segnalazioni"
│   ├── models.py                     # IncidentReport, Comment, Attachment
│   └── views.py                      # CRUD segnalazioni
│
├── documents/                        # "Documenti e PDF"
│   ├── models.py                     # Template, GeneratedDocument
│   └── generators.py                 # Logica generazione PDF
│
├── resources/                        # "Risorse (Documenti e FAQ)"
│   ├── models.py                     # CategoriaDocumento, Documento
│   │                                 # CategoriaFAQ, FAQ
│   └── views.py                      # API risorse
│
├── kpi/                              # "Dashboard KPI"
│   └── views.py                      # Aggregazioni per dashboard
│
└── ai_assistant/                     # "Assistente AI"
    ├── models.py                     # KnowledgeSource, ChatSession, ChatMessage
    └── views.py                      # API chatbot
```

### 4.3 Tabella Riepilogativa Apps

| App | Verbose Name | Modelli Principali | Funzione |
|-----|--------------|-------------------|----------|
| **core** | Utenti e Autenticazione | User, RoleAssignment, AuditLog | Autenticazione Magic Link, RBAC, audit trail |
| **territory** | Territorio | Regione, Provincia, Comune, Municipio, SezioneElettorale, TerritorialPartition* | Gerarchia amministrativa italiana e partizioni elettorali |
| **elections** | Consultazioni elettorali | ConsultazioneElettorale, TipoElezione, SchedaElettorale, ListaElettorale, Candidato | Gestione consultazioni, schede, liste e candidati |
| **delegations** | Deleghe | DelegatoDiLista, SubDelega, DesignazioneRDL, BatchGenerazioneDocumenti | Catena completa delle deleghe |
| **campaign** | Campagne e Registrazioni | CampagnaReclutamento, RdlRegistration | Reclutamento RDL via campagne pubbliche |
| **data** | Raccolta Dati | SectionAssignment, DatiSezione, DatiScheda, SectionDataHistory | Mappatura RDL e raccolta voti |
| **incidents** | Segnalazioni | IncidentReport, IncidentComment, IncidentAttachment | Gestione problemi durante le elezioni |
| **documents** | Documenti e PDF | Template, GeneratedDocument | Generazione automatica PDF deleghe |
| **resources** | Risorse (Documenti e FAQ) | CategoriaDocumento, Documento, CategoriaFAQ, FAQ | Materiali formativi per RDL |
| **kpi** | Dashboard KPI | (solo views) | Aggregazioni e statistiche real-time |
| **ai_assistant** | Assistente AI | KnowledgeSource, ChatSession, ChatMessage | Chatbot per supporto utenti |

### 4.4 Flusso di Autenticazione (Magic Link)

L'autenticazione avviene esclusivamente tramite **Magic Link**, un sistema passwordless che semplifica l'accesso per tutti gli utenti, in particolare per gli RDL che potrebbero non avere dimestichezza con sistemi complessi.

```
┌──────────────────────────────────────────────────────────────────┐
│                    FLUSSO MAGIC LINK                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Utente: Inserisce la propria email                           │
│     (deve essere già registrato nel sistema)                     │
│                                                                  │
│  2. Frontend: POST /api/auth/magic-link/request/ {email}         │
│                                                                  │
│  3. Backend: Verifica che l'email sia associata a un utente      │
│     - Se non esiste, ritorna errore                              │
│     - Se esiste, genera token temporaneo (30 min TTL)            │
│                                                                  │
│  4. Backend: Invia email con link di accesso                     │
│     Link: https://app.rdl.m5s.it/auth?token=xxx                  │
│                                                                  │
│  5. Utente: Clicca il link ricevuto nell'email                   │
│                                                                  │
│  6. Frontend: POST /api/auth/magic-link/verify/ {token}          │
│                                                                  │
│  7. Backend: Valida il token                                     │
│     - Verifica non scaduto                                       │
│     - Verifica non già utilizzato (one-time)                     │
│     - Trova l'utente associato                                   │
│                                                                  │
│  8. Backend: Genera JWT tokens                                   │
│     - Access token (1 ora TTL)                                   │
│     - Refresh token (7 giorni TTL)                               │
│                                                                  │
│  9. Frontend: Salva tokens in localStorage                       │
│     - Utente è autenticato                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

VANTAGGI:
- Nessuna password da ricordare
- Nessun account Google richiesto
- Funziona con qualsiasi email
- Sicuro (token one-time, TTL breve)
- UX semplificata per utenti non tecnici
- L'email è già verificata (è il canale di autenticazione)
```

---

## 5. Data Model Completo

### 5.1 Diagramma ER Semplificato

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TERRITORIO                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Regione ◄──┬── Provincia ◄──┬── Comune ◄──┬── Municipio                   │
│    (20)     │     (107)      │    (7896)   │    (opzionale)                │
│             │                │             │                                │
│             │                │             └──► SezioneElettorale           │
│             │                │                    (~61.000)                 │
│             │                └─────────────────────────┘                    │
│                                                                             │
│  TerritorialPartitionSet ◄── TerritorialPartitionUnit                       │
│  (Circoscrizioni, Collegi)   (singola unità territoriale)                   │
│                                       │                                     │
│                                       ▼                                     │
│                          TerritorialPartitionMembership                     │
│                          (Comune → Unità)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              ELEZIONI                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ConsultazioneElettorale ◄── TipoElezione ◄── SchedaElettorale             │
│  "Elezioni 8 Giugno 2025"    REFERENDUM         "Quesito 1" (turno=1)      │
│                               EUROPEE            "Quesito 2" (turno=1)      │
│                               COMUNALI           "Sindaco" (turno=1)        │
│                               MUNICIPALI         "Sindaco" (turno=2)        │
│                                   │                  │                      │
│                                   │                  ▼                      │
│                                   │         ListaElettorale ◄── Candidato  │
│                                   │              M5S             Ferrara    │
│                                   │              PD              Rossi      │
│                                   │                                         │
│  ElectionPartitionBinding ────────┘                                        │
│  (consultazione → set partizioni)                                          │
│                                                                             │
│  BallotActivation (scheda → partizione)                                    │
│  CandidatePartitionEligibility (candidato → partizione)                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DELEGAZIONI                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DelegatoDiLista ◄─────── SubDelega ◄─────── DesignazioneRDL               │
│  (Deputato/Senatore)      (per territorio)    (per sezione)                │
│        │                        │                   │                       │
│        │                        │                   │                       │
│        ▼                        ▼                   ▼                       │
│     [User]                   [User]              [User]                     │
│                                                                             │
│  tipo_delega:                                                               │
│  - FIRMA_AUTENTICATA → designa direttamente (stato=CONFERMATA)             │
│  - MAPPATURA → prepara bozze (stato=BOZZA), Delegato approva               │
│                                                                             │
│  BatchGenerazioneDocumenti (generazione PDF in batch)                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       CAMPAGNE E REGISTRAZIONI                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CampagnaReclutamento ◄────── RdlRegistration                              │
│  (link pubblico)              (candidatura RDL)                            │
│        │                            │                                       │
│        │                            │ approve()                             │
│        │                            ▼                                       │
│        │                         [User]                                     │
│        │                                                                    │
│        └── territorio_regioni/province/comuni (filtro iscrizioni)          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATI SEZIONI                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SectionAssignment ───► SezioneElettorale                                  │
│  (mappatura operativa)                                                     │
│        │                                                                    │
│        ▼                                                                    │
│     [User]                                                                  │
│                                                                             │
│  SezioneElettorale ◄─── DatiSezione ◄─── DatiScheda                        │
│                         (affluenza)       (voti per scheda/turno)          │
│                                                                             │
│  SectionDataHistory (storico modifiche)                                    │
│                                                                             │
│  Esempio DatiScheda.voti (JSON):                                           │
│  - Referendum: {"si": 523, "no": 301}                                      │
│  - Europee: {"liste": {"M5S": 250, "PD": 180}, "preferenze": {...}}       │
│  - Comunali: {"sindaco": {...}, "liste": {...}}                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Modelli Dettagliati per App

#### 5.2.1 Core - Utenti e Autenticazione

```python
# User (custom, email-based authentication)
class User:
    email           = EmailField(unique=True)  # USERNAME_FIELD
    display_name    = CharField(max_length=255)
    first_name      = CharField(max_length=150)
    last_name       = CharField(max_length=150)
    phone_number    = CharField(max_length=20, blank=True)
    avatar_url      = URLField(blank=True)
    created_at      = DateTimeField(auto_now_add=True)
    updated_at      = DateTimeField(auto_now=True)
    last_login_ip   = GenericIPAddressField(null=True)

# RoleAssignment (RBAC con scope territoriale e consultazione)
class RoleAssignment:
    user            = ForeignKey(User)
    role            = CharField(choices=[
                        'ADMIN',        # Accesso totale
                        'DELEGATE',     # Delegato di Lista
                        'SUBDELEGATE',  # Sub-Delegato
                        'RDL',          # Responsabile Di Lista
                        'KPI_VIEWER',   # Solo dashboard
                        'OBSERVER'      # Solo lettura
                      ])

    # Scope territoriale
    scope_type      = CharField(choices=[
                        'GLOBAL', 'REGIONE', 'PROVINCIA',
                        'COMUNE', 'MUNICIPIO', 'SEZIONE'
                      ])
    scope_regione   = ForeignKey(Regione, null=True)
    scope_provincia = ForeignKey(Provincia, null=True)
    scope_comune    = ForeignKey(Comune, null=True)

    # Scope consultazione (null = tutte le consultazioni)
    consultazione   = ForeignKey(ConsultazioneElettorale, null=True)

    assigned_by     = ForeignKey(User)
    is_active       = BooleanField(default=True)
    valid_from      = DateField(null=True)
    valid_to        = DateField(null=True)

# AuditLog (tracking completo)
class AuditLog:
    user            = ForeignKey(User, null=True)
    action          = CharField(choices=['LOGIN', 'LOGOUT', 'CREATE', ...])
    target_model    = CharField(max_length=100)
    target_id       = CharField(max_length=100)
    details         = JSONField(default=dict)
    ip_address      = GenericIPAddressField(null=True)
    timestamp       = DateTimeField(auto_now_add=True)
```

#### 5.2.2 Territorio

```python
class Regione:
    codice_istat    = CharField(max_length=2, unique=True)
    nome            = CharField(max_length=100)
    statuto_speciale = BooleanField(default=False)

class Provincia:
    regione         = ForeignKey(Regione)
    codice_istat    = CharField(max_length=3, unique=True)
    sigla           = CharField(max_length=2)
    nome            = CharField(max_length=100)
    is_citta_metropolitana = BooleanField(default=False)

class Comune:
    provincia       = ForeignKey(Provincia)
    codice_istat    = CharField(max_length=6, unique=True)
    codice_catastale = CharField(max_length=4)
    nome            = CharField(max_length=100)
    popolazione     = IntegerField(null=True)

class Municipio:
    comune          = ForeignKey(Comune)
    numero          = IntegerField()
    nome            = CharField(max_length=100)

class SezioneElettorale:
    comune          = ForeignKey(Comune)
    municipio       = ForeignKey(Municipio, null=True)
    numero          = IntegerField()
    indirizzo       = CharField(max_length=255, blank=True)
    n_elettori      = IntegerField(null=True)
    is_attiva       = BooleanField(default=True)

# Partizioni territoriali (circoscrizioni, collegi)
class TerritorialPartitionSet:
    nome            = CharField(max_length=200)  # "Circoscrizioni Europee"
    tipo            = CharField(choices=['CIRCOSCRIZIONE', 'COLLEGIO', ...])
    anno_riferimento = IntegerField()

class TerritorialPartitionUnit:
    partition_set   = ForeignKey(TerritorialPartitionSet)
    codice          = CharField(max_length=50)
    nome            = CharField(max_length=200)

class TerritorialPartitionMembership:
    partition_unit  = ForeignKey(TerritorialPartitionUnit)
    comune          = ForeignKey(Comune)
```

#### 5.2.3 Elections - Consultazioni Elettorali

```python
class ConsultazioneElettorale:
    nome            = CharField(max_length=255)
    data_inizio     = DateField()
    data_fine       = DateField()
    is_attiva       = BooleanField(default=False)
    descrizione     = TextField(blank=True)

class TipoElezione:
    consultazione   = ForeignKey(ConsultazioneElettorale)
    tipo            = CharField(choices=[
                        'REFERENDUM', 'EUROPEE',
                        'POLITICHE_CAMERA', 'POLITICHE_SENATO',
                        'REGIONALI', 'COMUNALI', 'MUNICIPALI'
                      ])
    ambito_nazionale = BooleanField(default=True)
    regione         = ForeignKey(Regione, null=True)
    comuni          = ManyToManyField(Comune, blank=True)

class SchedaElettorale:
    tipo_elezione   = ForeignKey(TipoElezione)
    nome            = CharField(max_length=255)
    colore          = CharField(max_length=50)
    ordine          = IntegerField(default=0)
    turno           = IntegerField(default=1)  # 1=primo turno, 2=ballottaggio
    data_inizio_turno = DateField(null=True)   # per turno=2: data ballottaggio
    testo_quesito   = TextField(blank=True)    # per referendum
    schema_voti     = JSONField(default=dict)

class ListaElettorale:
    scheda          = ForeignKey(SchedaElettorale)
    nome            = CharField(max_length=255)
    nome_breve      = CharField(max_length=50)
    simbolo         = ImageField(blank=True)
    ordine_scheda   = IntegerField(default=0)
    coalizione      = ForeignKey('self', null=True)

class Candidato:
    lista           = ForeignKey(ListaElettorale, null=True)
    scheda          = ForeignKey(SchedaElettorale)
    nome            = CharField(max_length=100)
    cognome         = CharField(max_length=100)
    posizione_lista = IntegerField(null=True)
    is_sindaco      = BooleanField(default=False)
    is_presidente   = BooleanField(default=False)

# Binding elezione → partizioni
class ElectionPartitionBinding:
    consultazione   = ForeignKey(ConsultazioneElettorale)
    partition_set   = ForeignKey(TerritorialPartitionSet)

class BallotActivation:
    scheda          = ForeignKey(SchedaElettorale)
    partition_unit  = ForeignKey(TerritorialPartitionUnit)
    is_active       = BooleanField(default=True)

class CandidatePartitionEligibility:
    candidato       = ForeignKey(Candidato)
    partition_unit  = ForeignKey(TerritorialPartitionUnit)
    lista           = ForeignKey(ListaElettorale, null=True)
    posizione       = IntegerField(null=True)
```

#### 5.2.4 Delegations - Deleghe

```python
class DelegatoDiLista:
    consultazione   = ForeignKey(ConsultazioneElettorale)
    cognome         = CharField(max_length=100)
    nome            = CharField(max_length=100)
    data_nascita    = DateField()
    luogo_nascita   = CharField(max_length=100)
    carica          = CharField(choices=[
                        'DEPUTATO', 'SENATORE',
                        'CONSIGLIERE_REGIONALE', 'EURODEPUTATO'
                      ])
    territorio_regioni  = ManyToManyField(Regione, blank=True)
    territorio_province = ManyToManyField(Provincia, blank=True)
    territorio_comuni   = ManyToManyField(Comune, blank=True)
    email           = EmailField()
    user            = ForeignKey(User, null=True)

class SubDelega:
    delegato        = ForeignKey(DelegatoDiLista)
    tipo_delega     = CharField(choices=[
                        'FIRMA_AUTENTICATA',  # designa direttamente
                        'MAPPATURA'           # prepara bozze
                      ])
    cognome         = CharField(max_length=100)
    nome            = CharField(max_length=100)
    data_nascita    = DateField()
    regioni         = ManyToManyField(Regione, blank=True)
    province        = ManyToManyField(Provincia, blank=True)
    comuni          = ManyToManyField(Comune, blank=True)
    email           = EmailField()
    user            = ForeignKey(User, null=True)
    is_attiva       = BooleanField(default=True)

class DesignazioneRDL:
    delegato        = ForeignKey(DelegatoDiLista, null=True)
    sub_delega      = ForeignKey(SubDelega, null=True)
    sezione         = ForeignKey(SezioneElettorale)
    ruolo           = CharField(choices=['EFFETTIVO', 'SUPPLENTE'])
    cognome, nome   = CharField(...)
    email           = EmailField()
    user            = ForeignKey(User, null=True)
    stato           = CharField(choices=['BOZZA', 'CONFERMATA', 'REVOCATA'])

class BatchGenerazioneDocumenti:
    consultazione   = ForeignKey(ConsultazioneElettorale)
    stato           = CharField(choices=['PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'])
    totale_documenti = IntegerField()
    documenti_generati = IntegerField(default=0)
```

#### 5.2.5 Campaign - Campagne e Registrazioni

```python
class CampagnaReclutamento:
    consultazione   = ForeignKey(ConsultazioneElettorale)
    nome            = CharField(max_length=200)
    slug            = SlugField(unique=True)  # URL: /campagna/{slug}
    descrizione     = TextField(blank=True)
    stato           = CharField(choices=['BOZZA', 'ATTIVA', 'CHIUSA'])
    data_apertura   = DateTimeField()
    data_chiusura   = DateTimeField()
    territorio_regioni  = ManyToManyField(Regione, blank=True)
    territorio_province = ManyToManyField(Provincia, blank=True)
    territorio_comuni   = ManyToManyField(Comune, blank=True)
    richiedi_approvazione = BooleanField(default=True)
    max_registrazioni = IntegerField(null=True)
    delegato        = ForeignKey(DelegatoDiLista, null=True)
    sub_delega      = ForeignKey(SubDelega, null=True)
    created_by      = ForeignKey(User)

class RdlRegistration:
    email           = EmailField()
    nome            = CharField(max_length=100)
    cognome         = CharField(max_length=100)
    telefono        = CharField(max_length=20)
    comune          = ForeignKey(Comune)
    municipio       = ForeignKey(Municipio, null=True)
    consultazione   = ForeignKey(ConsultazioneElettorale)
    campagna        = ForeignKey(CampagnaReclutamento, null=True)
    status          = CharField(choices=['PENDING', 'APPROVED', 'REJECTED'])
    source          = CharField(choices=['SELF', 'IMPORT', 'MANUAL', 'CAMPAGNA'])
    user            = ForeignKey(User, null=True)
    approved_by     = ForeignKey(User, null=True)
```

#### 5.2.6 Sections - Raccolta Dati

```python
class SectionAssignment:
    sezione         = ForeignKey(SezioneElettorale)
    consultazione   = ForeignKey(ConsultazioneElettorale)
    user            = ForeignKey(User)
    role            = CharField(choices=['RDL', 'SUPPLENTE'])
    assigned_by     = ForeignKey(User)

class DatiSezione:
    sezione         = ForeignKey(SezioneElettorale)
    consultazione   = ForeignKey(ConsultazioneElettorale)
    elettori_maschi = IntegerField(default=0)
    elettori_femmine = IntegerField(default=0)
    votanti_maschi  = IntegerField(default=0)
    votanti_femmine = IntegerField(default=0)
    is_complete     = BooleanField(default=False)
    is_verified     = BooleanField(default=False)
    inserito_da     = ForeignKey(User, null=True)

class DatiScheda:
    dati_sezione    = ForeignKey(DatiSezione)
    scheda          = ForeignKey(SchedaElettorale)  # include turno
    schede_ricevute     = IntegerField(default=0)
    schede_autenticate  = IntegerField(default=0)
    schede_bianche      = IntegerField(default=0)
    schede_nulle        = IntegerField(default=0)
    schede_contestate   = IntegerField(default=0)
    voti            = JSONField(default=dict)
    errori_validazione = TextField(blank=True)

class SectionDataHistory:
    dati_sezione    = ForeignKey(DatiSezione)
    campo           = CharField(max_length=100)
    valore_precedente = TextField(blank=True)
    valore_nuovo    = TextField(blank=True)
    modificato_da   = ForeignKey(User)
    modificato_at   = DateTimeField(auto_now_add=True)
```

#### 5.2.7 Altri Modelli

```python
# incidents/models.py
class IncidentReport:
    sezione         = ForeignKey(SezioneElettorale)
    consultazione   = ForeignKey(ConsultazioneElettorale)
    categoria       = CharField(choices=['PROCEDURAL', 'ACCESS', ...])
    severita        = CharField(choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
    stato           = CharField(choices=['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'])
    descrizione     = TextField()
    segnalato_da    = ForeignKey(User)

class IncidentComment:
    incident        = ForeignKey(IncidentReport)
    autore          = ForeignKey(User)
    testo           = TextField()

class IncidentAttachment:
    incident        = ForeignKey(IncidentReport)
    file            = FileField()

# documents/models.py
class Template:
    nome            = CharField(max_length=100)
    tipo            = CharField(choices=['DELEGA', 'DESIGNAZIONE', ...])
    file_template   = FileField()

class GeneratedDocument:
    template        = ForeignKey(Template)
    contenuto       = JSONField()
    file_generato   = FileField()
    generato_da     = ForeignKey(User)

# resources/models.py
class CategoriaDocumento:
    nome            = CharField(max_length=100)
    ordine          = IntegerField(default=0)

class Documento:
    categoria       = ForeignKey(CategoriaDocumento)
    titolo          = CharField(max_length=200)
    file            = FileField()
    visibile_per_ruoli = JSONField(default=list)

class CategoriaFAQ:
    nome            = CharField(max_length=100)

class FAQ:
    categoria       = ForeignKey(CategoriaFAQ)
    domanda         = TextField()
    risposta        = TextField()
    ordine          = IntegerField(default=0)

# ai_assistant/models.py
class KnowledgeSource:
    nome            = CharField(max_length=200)
    tipo            = CharField(choices=['PDF', 'URL', 'MANUAL'])
    contenuto       = TextField()

class ChatSession:
    user            = ForeignKey(User)
    created_at      = DateTimeField(auto_now_add=True)

class ChatMessage:
    session         = ForeignKey(ChatSession)
    ruolo           = CharField(choices=['user', 'assistant'])
    contenuto       = TextField()
```

---

## 6. Nuove Funzionalità

### 6.1 Gestione Automatica Turni (Ballottaggio)

**Problema risolto**: Per le elezioni comunali con ballottaggio, gli RDL dovevano manualmente selezionare quale turno stessero inserendo.

**Soluzione 2026**: Il sistema determina automaticamente il turno in base alla data:

```python
# SchedaElettorale
turno = IntegerField(default=1)           # 1=primo turno, 2=ballottaggio
data_inizio_turno = DateField(null=True)  # data del ballottaggio

# Logica automatica
def get_scheda_turno_attivo(consultazione):
    today = date.today()

    # Se esiste una scheda turno=2 con data_inizio_turno <= oggi
    for scheda in schede.filter(turno=2):
        if scheda.data_inizio_turno and today >= scheda.data_inizio_turno:
            return scheda  # Mostra ballottaggio

    # Altrimenti primo turno
    return schede.filter(turno=1).first()
```

**Comportamento per l'RDL:**
- Prima del ballottaggio: vede e inserisce dati primo turno
- Dal giorno del ballottaggio: vede e inserisce dati secondo turno
- Banner visivo "BALLOTTAGGIO" quando attivo il secondo turno

### 6.2 Campagne di Reclutamento RDL

**Problema risolto**: Il reclutamento RDL avveniva via Google Form, con gestione manuale degli approvati e nessun controllo territoriale.

**Soluzione 2026**: Il **Delegato** ha il controllo completo del reclutamento nel suo territorio.

```
┌─────────────────────────────────────────────────────────────────┐
│          FLUSSO RECLUTAMENTO (gestito dal Delegato)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DELEGATO CREA LA CAMPAGNA                                   │
│     - Nome: "Cercasi RDL per Roma Nord"                         │
│     - Territorio: definisce comuni/municipi coperti             │
│     - Date: apertura e chiusura registrazioni                   │
│     → Sistema genera URL pubblica: /campagna/rdl-roma-nord      │
│                                                                 │
│  2. DIFFUSIONE                                                  │
│     - Gruppi WhatsApp, Social media, Email                      │
│                                                                 │
│  3. CITTADINI SI REGISTRANO                                     │
│     - Accedono al link pubblico (no login)                      │
│     - Compilano form con dati anagrafici                        │
│     → Sistema crea RdlRegistration (status=PENDING)             │
│                                                                 │
│  4. DELEGATO APPROVA                                            │
│     - APPROVED → Sistema crea User + ruolo RDL                  │
│     - REJECTED → con motivazione                                │
│                                                                 │
│  5. MAPPATURA SEZIONI                                           │
│     - Sub-Delegato assegna RDL alle sezioni                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Catena Digitale delle Deleghe

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUSSO DELEGA DIGITALE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Admin crea DelegatoDiLista nel sistema                      │
│     → Sistema crea automaticamente User + ruolo DELEGATE        │
│                                                                 │
│  2. Delegato accede e crea SubDelega                            │
│     - Sceglie tipo: FIRMA_AUTENTICATA o MAPPATURA               │
│     → Sistema crea User + ruolo SUBDELEGATE                     │
│                                                                 │
│  3. Sub-Delegato designa RDL                                    │
│     - Se FIRMA_AUTENTICATA: designazione → CONFERMATA           │
│     - Se MAPPATURA: bozza → Delegato approva → CONFERMATA       │
│                                                                 │
│  4. Sistema genera PDF con catena completa                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Sistema di Segnalazioni (Incidents)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CATEGORIE SEGNALAZIONI                       │
├─────────────────────────────────────────────────────────────────┤
│  PROCEDURAL    │ Violazioni procedurali                         │
│  ACCESS        │ Problemi di accesso al seggio                  │
│  MATERIALS     │ Materiale mancante/danneggiato                 │
│  INTIMIDATION  │ Intimidazioni o pressioni                      │
│  IRREGULARITY  │ Irregolarità nello scrutinio                   │
│  TECHNICAL     │ Problemi tecnici (app, connessione)            │
├─────────────────────────────────────────────────────────────────┤
│                    WORKFLOW                                     │
├─────────────────────────────────────────────────────────────────┤
│  OPEN → IN_PROGRESS → RESOLVED → CLOSED                         │
│            ↓                                                    │
│        ESCALATED (se critico)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.5 Partizioni Territoriali

Nuovo sistema per gestire circoscrizioni e collegi elettorali:

```
TerritorialPartitionSet: "Circoscrizioni Europee 2024"
├── TerritorialPartitionUnit: "Italia Nord-Occidentale"
│   └── TerritorialPartitionMembership: Piemonte, Lombardia, ...
├── TerritorialPartitionUnit: "Italia Nord-Orientale"
│   └── TerritorialPartitionMembership: Veneto, Friuli, ...
...

ElectionPartitionBinding: Europee 2024 → usa "Circoscrizioni Europee"
BallotActivation: Scheda Europee → attiva in tutte le circoscrizioni
CandidatePartitionEligibility: Ferrara → eleggibile in "Nord-Ovest"
```

---

## 7. Miglioramenti Tecnici

### 7.1 Da Google Sheets a PostgreSQL

| Aspetto | Google Sheets | PostgreSQL |
|---------|---------------|------------|
| **Throughput** | ~100 req/100s | ~10.000 req/s |
| **Latenza** | 100-500ms | 1-10ms |
| **Transazioni** | No | ACID completo |
| **Query complesse** | No | JOIN, subquery, aggregazioni |
| **Indici** | No | B-tree, GIN, GiST |
| **Concorrenza** | Lock manuale | MVCC |

### 7.2 Caching con Redis

```
┌─────────────────────────────────────────────────────────────────┐
│                    STRATEGIA CACHING                            │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: Client-side (Client.js)                               │
│  - Cache in-memory con TTL                                      │
│  - Retry con exponential backoff                                │
│                                                                 │
│  LAYER 2: Redis (server-side)                                   │
│  - Session storage                                              │
│  - Cache query frequenti                                        │
│  - Rate limiting                                                │
│                                                                 │
│  LAYER 3: Database (PostgreSQL)                                 │
│  - Query cache                                                  │
│  - Connection pooling                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 API REST Standardizzata

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONVENZIONI API                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AUTENTICAZIONE (Magic Link)                                    │
│  POST /api/auth/magic-link/request/  Richiedi magic link        │
│  POST /api/auth/magic-link/verify/   Verifica token             │
│  POST /api/auth/token/refresh/       Refresh JWT                │
│  GET  /api/auth/profile/             Profilo utente             │
│                                                                 │
│  TERRITORIO (read-only, cached)                                 │
│  GET /api/territorio/regioni/                                   │
│  GET /api/territorio/province/?regione={id}                     │
│  GET /api/territorio/comuni/?provincia={id}                     │
│  GET /api/territorio/sezioni/?comune={id}                       │
│                                                                 │
│  ELEZIONI (read-only)                                           │
│  GET /api/elections/consultazioni/                              │
│  GET /api/elections/consultazioni/attiva/                       │
│  GET /api/elections/consultazioni/{id}/                         │
│  GET /api/elections/schede/{id}/                                │
│  PATCH /api/elections/schede/{id}/     (admin)                  │
│                                                                 │
│  DELEGHE (RBAC-protected)                                       │
│  GET  /api/deleghe/mia-catena/                                  │
│  GET  /api/deleghe/sub-deleghe/                                 │
│  POST /api/deleghe/sub-deleghe/                                 │
│  GET  /api/deleghe/designazioni/                                │
│  POST /api/deleghe/designazioni/                                │
│  GET  /api/deleghe/campagne/                                    │
│  POST /api/deleghe/campagne/                                    │
│                                                                 │
│  SEZIONI E DATI (RBAC-protected)                                │
│  GET  /api/sections/own/                                        │
│  GET  /api/sections/assigned/                                   │
│  POST /api/sections/                                            │
│                                                                 │
│  CAMPAGNE (pubbliche)                                           │
│  GET  /api/campagna/{slug}/            Info campagna            │
│  POST /api/campagna/{slug}/registra/   Registrazione            │
│                                                                 │
│  RDL MANAGEMENT                                                 │
│  GET  /api/rdl/registrations/                                   │
│  POST /api/rdl/registrations/{id}/approve/                      │
│                                                                 │
│  KPI (KPI_VIEWER+)                                              │
│  GET /api/kpi/dashboard/                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Flussi Operativi

### 8.1 Setup Elezione

```
┌─────────────────────────────────────────────────────────────────┐
│        FASE 1: CONFIGURAZIONE INIZIALE (T-60 giorni)            │
│                     [AMMINISTRATORE]                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Admin crea ConsultazioneElettorale                          │
│  2. Admin crea TipoElezione per ogni tipo                       │
│  3. Admin crea schede nazionali (referendum, europee)           │
│  4. Admin inserisce i Delegati di Lista                         │
│     → Sistema crea User + ruolo DELEGATE                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│        FASE 2: CONFIGURAZIONE TERRITORIALE (T-45 giorni)        │
│                       [DELEGATO]                                │
├─────────────────────────────────────────────────────────────────┤
│  1. Delegato configura schede territoriali                      │
│     (comunali, regionali, circoscrizioni)                       │
│  2. Delegato crea SubDelega per collaboratori                   │
│  3. Delegato crea Campagne di reclutamento                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│        FASE 3: RECLUTAMENTO RDL (T-30 giorni)                   │
│                 [DELEGATO / SUB-DELEGATO]                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Campagne pubbliche raccolgono candidature                   │
│  2. Approvazione candidature → User + ruolo RDL                 │
│  3. Mappatura RDL → Sezioni                                     │
│  4. Designazioni formali + generazione PDF                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│        FASE 4: GIORNO DELLE ELEZIONI                            │
│                         [RDL]                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Login via Magic Link                                        │
│  2. Presenza al seggio                                          │
│  3. Inserimento dati scrutinio (turno automatico)               │
│  4. Verifica dati da parte dei referenti                        │
│  5. Dashboard KPI real-time                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│        FASE 5: EVENTUALE BALLOTTAGGIO (T+14 giorni)             │
│                         [RDL]                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Sistema mostra automaticamente schede turno=2               │
│  2. Banner "BALLOTTAGGIO" visibile                              │
│  3. RDL inserisce dati secondo turno                            │
│  4. Stessa mappatura del primo turno                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Sicurezza e Compliance

### 9.1 Autenticazione (Magic Link)

| Componente | Sicurezza | Descrizione |
|------------|-----------|-------------|
| Magic Link | Alta | Token one-time, 30 min TTL, verificato via email |
| JWT Access | Standard (HS256) | Token di sessione, 1 ora TTL |
| JWT Refresh | Standard (HS256) | Token di rinnovo, 7 giorni TTL |

### 9.2 Autorizzazione (RBAC con Consultazione)

```python
# RoleAssignment include consultazione
RoleAssignment(
    user=user,
    role='RDL',
    scope_type='COMUNE',
    scope_comune=roma,
    consultazione=referendum_2025  # Ruolo valido solo per questa consultazione
)
```

### 9.3 Protezione Dati (GDPR)

| Requisito | Implementazione |
|-----------|-----------------|
| Consenso | Checkbox esplicito in registrazione |
| Accesso | GET /api/auth/profile/ |
| Rettifica | PATCH /api/auth/profile/ |
| Cancellazione | Soft delete + anonimizzazione |
| Audit | AuditLog con retention 5 anni |

---

## 10. Deployment e Scalabilità

### 10.1 Ambiente di Sviluppo

```bash
# Docker Compose
docker-compose up

# Servizi attivi:
# - frontend: http://localhost:3000
# - backend: http://localhost:3001
# - postgres: localhost:5432
# - redis: localhost:6379
```

### 10.2 Produzione (Google Cloud)

```
Cloud CDN → Cloud Load Balancer
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   Cloud Run (N)         Cloud Run (N)
        │                     │
        └──────────┬──────────┘
                   ▼
          Cloud SQL (PostgreSQL)
          Cloud Memorystore (Redis)
          Cloud Storage (files)
```

---

## Appendice A: Glossario

| Termine | Definizione |
|---------|-------------|
| **RDL** | Responsabile Di Lista - presente al seggio per conto del partito |
| **Delegato** | Deputato/Senatore/etc. nominato dal partito per una consultazione |
| **Sub-Delega** | Atto con cui il Delegato delega poteri a un Sub-Delegato |
| **Firma Autenticata** | Sub-delega con firma autenticata da notaio/funzionario |
| **Mappatura** | Sub-delega senza firma autenticata (solo preparazione bozze) |
| **Consultazione** | Tornata elettorale (può includere più tipi di elezione) |
| **Sezione** | Unità di voto (500-1200 elettori) |
| **Scheda** | Documento cartaceo su cui l'elettore esprime il voto |
| **Turno** | Fase di votazione (1=primo turno, 2=ballottaggio) |
| **Campagna** | Link pubblico per reclutamento RDL |

---

## Appendice B: Riferimenti Normativi

- **DPR 361/1957** - Testo unico delle leggi per l'elezione della Camera
- **DPR 533/1993** - Regolamento per l'elezione diretta dei sindaci
- **L. 352/1970** - Norme sui referendum
- **D.Lgs. 196/2003** - Codice Privacy (come modificato da GDPR)
- **Regolamento UE 2016/679** - GDPR

---

*Documento generato il 3 Febbraio 2026*
*Versione: 2.1*
*Sistema RDL - Movimento 5 Stelle*
