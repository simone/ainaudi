# 🗄️ Inizializzazione Database - Guida Rapida

Se hai resettato il database o lo stai configurando per la prima volta, segui questa guida.

---

## 🚀 Metodo Veloce (1 comando)

```bash
# Modalità interattiva (con conferme)
./scripts/init-db.sh

# Modalità automatica (salta tutte le conferme)
./scripts/init-db.sh --yes
```

**Cosa fa lo script:**
1. ✅ Esegue migrations Django
2. ✅ Carica **Regioni** (20) e **Province** (107) italiane
3. ✅ Carica **Referendum Costituzionale Giustizia 2026** attivo
3bis. ✅ Carica **5 Delegati Roma** (Pietracci, Federici, Meleo, Contardi, Riccardi)
4. ✅ Scarica e importa **7.896 Comuni** da CSV ISTAT (auto-download)
5. ✅ Genera **64 Municipi** per grandi città (Roma, Milano, Torino, Napoli, Bari, Palermo, Genova)
5bis. ✅ Imposta **flag > 15.000 abitanti** per 556 comuni (sistema elettorale)
6. ✅ Scarica e importa **61.543 Sezioni Elettorali** da Eligendo (auto-download)
6bis. ✅ **Matching sezioni → plessi SCUANA** (63.109 plessi scolastici → ~10k sezioni migliorate)
6ter. ✅ Aggiorna **2.601 Sezioni Roma** con indirizzi specifici comunali
7. ✅ Crea **Superuser** Django (opzionale, skippato con --yes)

**Tempo richiesto:** 3-5 minuti

**Flag --yes:**
- Salta tutte le conferme
- Risponde automaticamente SÌ a tutto
- Skips superuser (richiede input manuale)

---

## 📋 Cosa Viene Caricato

### Dati Territoriali

| Livello | Quantità | Copertura | Fonte |
|---------|----------|-----------|-------|
| **Regioni** | 20 | 100% | `fixtures/initial_data.json` |
| **Province** | 107 | 100% | `fixtures/initial_data.json` |
| **Comuni** | 7.896 | 100% | CSV ISTAT (auto-download) |
| └─ > 15.000 abitanti | 556 | Flag sistema elettorale | Auto-calcolato da sezioni |
| **Municipi** | 64 | 7 grandi città | Auto-generato (Roma, Milano, Torino, Napoli, Bari, Palermo, Genova) |
| **Sezioni** | 61.543 | 100% comuni | CSV Eligendo (auto-download) |
| └─ Con indirizzo | 61.508 | **99%** | Eligendo + matching SCUANA |
| └─ Con denominazione | 60.506 | **98%** | Eligendo + matching SCUANA |
| └─ Dati completi | 60.506 | **98%** | Pipeline completa |
| **Plessi scolastici** | 63.109 | Riferimento | File SCUANA (4 CSV) |

### Pipeline Qualità Dati

1. **Base Eligendo** → 61.543 sezioni con indirizzi (99%)
2. **Matching SCUANA** → +10.347 sezioni migliorate con plessi scolastici
3. **Update Roma** → 2.601 sezioni con dati comunali specifici

**Risultato finale:** Database completo al **98%** con indirizzi + denominazioni

### Consultazione Elettorale 2026

| Tipo Elezione | Schede | Dettagli |
|--------------|--------|----------|
| **REFERENDUM COSTITUZIONALE** | 1 | Riforma Giustizia (Separazione Carriere) |

**Data:** 22-23 Marzo 2026
**Tipo:** Referendum Costituzionale Confermativo (art. 138 Cost.)
**Quorum:** NON richiesto
**Stato:** Attiva (`is_attiva=True`)

**Orari:**
- Domenica 22/03: ore 7:00 - 23:00
- Lunedì 23/03: ore 7:00 - 15:00

---

## 🔧 Metodo Manuale (step-by-step)

Se preferisci controllare ogni step:

### 1. Migrations

```bash
# Con Docker
docker-compose exec backend python manage.py migrate

# Senza Docker
cd backend_django && python manage.py migrate
```

### 2. Regioni e Province

```bash
# Con Docker
docker-compose exec backend python manage.py loaddata fixtures/initial_data.json

# Senza Docker
cd backend_django && python manage.py loaddata fixtures/initial_data.json
```

**Risultato:** 20 Regioni + 107 Province

### 3. Consultazione Elettorale

```bash
# Con Docker
docker-compose exec backend python manage.py loaddata fixtures/referendum_giustizia_2026.json

# Senza Docker
cd backend_django && python manage.py loaddata fixtures/referendum_giustizia_2026.json
```

**Risultato:** Referendum Costituzionale Giustizia 2026 + 1 TipoElezione + 1 Scheda

### 3bis. Delegati Roma per Referendum 2026

```bash
# Con Docker
docker-compose exec backend python manage.py load_delegati_roma

# Senza Docker
cd backend_django && python manage.py load_delegati_roma
```

**Tempo:** ~1 secondo
**Risultato:** 5 Delegati per Roma con territorio assegnato

**Delegati caricati:**
1. **Daniela Pietracci** - danielapietracci@gmail.com
2. **Simone Federici** - s.federici@gmail.com
3. **Linda Meleo** - linda.meleo@movimento5stelle.eu
4. **Federica Contardi** - efsi2365@gmail.com
5. **Marina Riccardi** - marinariccardi961@gmail.com

**Territorio assegnato:** **SOLO Comune Roma** (non regione/provincia)

**Ruolo:** Rappresentante del Partito (RAPPRESENTANTE_PARTITO)
**Scope ruolo:** COMUNE (territorialmente limitato a Roma, non globale)

**Auto-provisioning:** Il comando crea automaticamente:
- User account per ogni delegato
- Assegnazione ruolo DELEGATE con scope COMUNE
- Aggiunta al gruppo Django "Delegato"
- Territorio limitato al solo comune (i delegati vedono solo sezioni di Roma)

### 4. Comuni (CSV ISTAT)

```bash
# Con Docker
docker-compose exec backend python manage.py import_comuni_istat --file fixtures/comuni_istat.csv

# Senza Docker
cd backend_django && python manage.py import_comuni_istat --file fixtures/comuni_istat.csv
```

**Tempo:** ~1-2 minuti
**Risultato:** 7.896 Comuni italiani con dati ISTAT

### 4bis. Municipi Grandi Città

```bash
# Con Docker
docker-compose exec backend python manage.py generate_municipi

# Senza Docker
cd backend_django && python manage.py generate_municipi

# Solo una città specifica
docker-compose exec backend python manage.py generate_municipi --city milano
```

**Tempo:** ~1 secondo
**Risultato:** 64 municipi per 7 grandi città

**Città supportate:**
- Roma (15 municipi)
- Milano (9 municipi)
- Torino (8 circoscrizioni)
- Napoli (10 municipalità)
- Bari (5 municipi)
- Palermo (8 circoscrizioni)
- Genova (9 municipi)

### 4ter. Flag Popolazione Comuni (> 15.000 abitanti)

```bash
# Con Docker
docker-compose exec backend python manage.py update_comuni_popolazione

# Senza Docker
cd backend_django && python manage.py update_comuni_popolazione
```

**Tempo:** ~2 secondi
**Risultato:** 556 comuni marcati come > 15.000 abitanti

**Scopo:** Determina il sistema elettorale comunale (turno unico vs doppio turno)

### 5. Sezioni Elettorali Nazionali (Auto-download da Eligendo)

```bash
# Con Docker
docker-compose exec backend python manage.py import_sezioni_italia --file fixtures/sezioni_eligendo.csv

# Senza Docker
cd backend_django && python manage.py import_sezioni_italia --file fixtures/sezioni_eligendo.csv
```

**Tempo:** ~1-2 minuti
**Risultato:** ~61.540 Sezioni elettorali nazionali

**Fonte:** https://elezionistorico.interno.gov.it/eligendo/opendata.php

### 5bis. Matching Sezioni → Plessi Scolastici (Migliora Qualità Dati)

```bash
# Con Docker
docker-compose exec backend python manage.py match_sezioni_plessi \
  --stat fixtures/SCUANAGRAFESTAT20252620250901.csv \
  --par fixtures/SCUANAGRAFEPAR20252620250901.csv \
  --aut-stat fixtures/SCUANAAUTSTAT20252620250901.csv \
  --aut-par fixtures/SCUANAAUTPAR20252620250901.csv \
  --threshold 0.6

# Senza Docker
cd backend_django && python manage.py match_sezioni_plessi \
  --stat fixtures/SCUANAGRAFESTAT20252620250901.csv \
  --par fixtures/SCUANAGRAFEPAR20252620250901.csv \
  --threshold 0.6
```

**Tempo:** ~2-3 minuti
**Risultato:** ~10.000 sezioni migliorate con dati dei plessi scolastici

**Cosa fa:**
- Carica 63.109 plessi scolastici dai 4 file SCUANA (Anagrafe Edilizia Scolastica)
- Fa fuzzy matching tra sezioni e plessi per comune
- Aggiorna denominazione e indirizzo dove il match è affidabile (score > 0.6)

### 5ter. Aggiorna Sezioni Roma con Indirizzi Dettagliati

```bash
# Con Docker
docker-compose exec backend python manage.py update_sezioni_dettagli "fixtures/ROMA - Sezioni.csv"

# Senza Docker
cd backend_django && python manage.py update_sezioni_dettagli "fixtures/ROMA - Sezioni.csv"
```

**Tempo:** ~10 secondi
**Risultato:** 2.601 Sezioni Roma con indirizzi specifici e municipi

### 6. Superuser

```bash
# Con Docker
docker-compose exec backend python manage.py createsuperuser

# Senza Docker
cd backend_django && python manage.py createsuperuser
```

---

## 🐛 Troubleshooting

### "File CSV non trovato"

I file CSV necessari sono:
- `comuni_istat.csv` (comuni italiani) - **Scaricato automaticamente** dall'ISTAT
- `sezioni_eligendo.csv` (sezioni elettorali) - **Scaricato automaticamente** da Eligendo
- `ROMA - Sezioni.csv` (dettagli Roma) - **Già incluso** in fixtures

**Lo script `init-db.sh` scarica automaticamente** entrambi i CSV.

Se il download automatico fallisce, scarica manualmente da:
- **Comuni:** https://www.istat.it/it/archivio/6789
- **Sezioni:** https://elezionistorico.interno.gov.it/eligendo/opendata.php (file: `elenco-sezioni-elettorali.csv`)

### "Constraint violation" o "Already exists"

Il database ha ancora dati vecchi. Reset completo:

```bash
# Con Docker
docker-compose down -v
docker-compose up -d
sleep 10
./scripts/init-db.sh

# Senza Docker
cd backend_django
rm db.sqlite3  # Solo se usi SQLite
dropdb ainaudi_db && createdb ainaudi_db  # Se usi PostgreSQL
python manage.py migrate
python manage.py loaddata fixtures/initial_data.json
...
```

### "Import troppo lento"

Se l'import dei comuni è lento:
1. Verifica connessione database
2. Usa PostgreSQL invece di SQLite (molto più veloce)
3. Import solo comuni specifici (vedi documentazione command)

### "Consultazione non attiva"

La consultazione viene caricata con `is_attiva=True` di default. Se serve disattivarla:

```bash
# Django shell
docker-compose exec backend python manage.py shell
>>> from elections.models import ConsultazioneElettorale
>>> c = ConsultazioneElettorale.objects.get(nome__contains="2026")
>>> c.is_attiva = False  # o True per riattivarla
>>> c.save()
```

Oppure dall'admin: http://localhost:3001/admin

---

## 📖 Management Commands Disponibili

| Command | Descrizione |
|---------|-------------|
| `import_comuni_istat <csv>` | Import comuni da CSV ISTAT |
| `import_sezioni_italia <csv>` | Import sezioni da CSV Eligendo (auto-detect formato) |
| `generate_municipi [--city]` | Genera municipi per grandi città (Roma, Milano, Torino, etc.) |
| `update_comuni_popolazione` | Imposta flag > 15.000 abitanti (sistema elettorale) |
| `match_sezioni_plessi` | Matching sezioni con plessi SCUANA (migliora qualità) |
| `update_sezioni_dettagli <csv>` | Aggiorna sezioni con CSV specifico (es. Roma) |
| `load_delegati_roma` | Carica 5 delegati per Roma Referendum 2026 |
| `loaddata <fixture>` | Carica fixture JSON (regioni, province) |

**Help per ogni comando:**

```bash
docker-compose exec backend python manage.py <command> --help
```

---

## 🎯 Quick Start per Test

Se vuoi testare velocemente **senza** import completo:

```bash
# Solo dati base (2 minuti)
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py loaddata fixtures/initial_data.json
docker-compose exec backend python manage.py loaddata fixtures/consultazione_multipla_2025.json
docker-compose exec backend python manage.py createsuperuser

# Poi aggiungi manualmente comuni/sezioni dall'admin
```

---

## 📚 Vedi Anche

- **Setup Docker:** `DOCKER_SETUP.md`
- **Configurazione:** `CONFIGURATION.md`
- **Architettura:** `CLAUDE.md`
