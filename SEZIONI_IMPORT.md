# 🗳️ Import Sezioni Elettorali - Processo a Due Fasi

## 📖 Concetto Generale

L'import delle sezioni elettorali avviene in **DUE FASI** distinte:

### **Fase 1: Plessi Scolastici ISTAT (Nazionale)**
Import dei **plessi scolastici** da dati ufficiali ISTAT. Questi sono gli **edifici** (scuole, palestre, ecc.) dove si vota in tutta Italia.

### **Fase 2: Dettagli Sezioni Comunali (Specifico)**
Update con **indirizzi precisi** e dettagli delle sezioni rilasciati dal singolo comune (es. Roma).

---

## 🔄 Processo Completo

### Step 1: Import Comuni + Plessi Scolastici (ISTAT)

```bash
# Con Docker
docker-compose exec backend python manage.py import_comuni_istat --file fixtures/SCUANAGRAFESTAT20252620250901.csv

# Senza Docker
cd backend_django
python manage.py import_comuni_istat --file fixtures/SCUANAGRAFESTAT20252620250901.csv
```

**Cosa importa:**
- ~8.000 Comuni italiani con codici ISTAT
- ~60.000 Plessi scolastici (edifici) associati ai comuni
- Denominazioni generiche degli edifici

**File CSV:** `SCUANAGRAFESTAT20252620250901.csv` (13MB)

**Fonte:** [Dati ISTAT - Comuni e Sezioni](https://dati.istat.it/)

**Tempo:** 1-2 minuti per comuni, 5-10 minuti per sezioni

---

### Step 2: Import Sezioni Italiane (Opzionale)

```bash
# Con Docker
docker-compose exec backend python manage.py import_sezioni_italia --file fixtures/SCUANAGRAFESTAT20252620250901.csv

# Senza Docker
cd backend_django
python manage.py import_sezioni_italia --file fixtures/SCUANAGRAFESTAT20252620250901.csv
```

**Cosa importa:**
- ~60.000 Sezioni elettorali con associazione ai plessi
- Numero sezione per ogni plesso
- Collegamenti sezione → plesso → comune

**Nota:** Usa lo stesso CSV dello Step 1 (contiene sia comuni che sezioni)

---

### Step 3: Update Dettagli Specifici Comune (es. Roma)

```bash
# Con Docker
docker-compose exec backend python manage.py update_sezioni_dettagli "fixtures/ROMA - Sezioni.csv"

# Senza Docker
cd backend_django
python manage.py update_sezioni_dettagli "fixtures/ROMA - Sezioni.csv"
```

**Cosa aggiorna:**
- Indirizzi precisi delle sezioni (via, numero civico)
- Municipio di appartenenza
- Denominazione specifica del seggio
- Collegamenti sezione → indirizzo reale

**File CSV:** `ROMA - Sezioni.csv` (101KB)

**Formato CSV:**
```csv
SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO,
1,ROMA,3,"VIA DI SETTEBAGNI, 231",
2,ROMA,1,"VIA DANIELE MANIN, 72",
...
```

**Fonte:** Dati rilasciati dal Comune di Roma

**Tempo:** ~1 minuto

---

## 📊 Differenza tra Fase 1 e Fase 2

| Aspetto | Fase 1 (ISTAT) | Fase 2 (Comune) |
|---------|----------------|-----------------|
| **Fonte** | ISTAT (nazionale) | Comune (locale) |
| **Dati** | Plessi scolastici (edifici) | Indirizzi precisi sezioni |
| **Copertura** | Tutta Italia | Singolo comune |
| **Dettaglio** | Generico | Specifico |
| **Esempio** | "Scuola Primaria G. Mazzini" | "Via Daniele Manin, 72" |

---

## 🎯 Perché Serve Fase 2?

I dati ISTAT contengono solo le **denominazioni generiche** degli edifici scolastici:
- "Scuola Media Statale"
- "Istituto Comprensivo"
- "Plesso Scolastico"

**Ma NON contengono:**
- Indirizzi specifici
- Numeri civici
- Collegamenti precisi sezione → via

Il **Comune** (es. Roma) rilascia CSV specifici con:
- Sezione N → Via precisa con numero civico
- Municipio di appartenenza
- Denominazione esatta del seggio

---

## 📝 File Necessari

### Fase 1 (ISTAT)

File già presenti in `backend_django/fixtures/`:

```
SCUANAGRAFESTAT20252620250901.csv    # 13MB - Comuni + Sezioni (ISTAT)
SCUANAAUTSTAT20252620250901.csv      # 305KB - Autonomie speciali
SCUANAGRAFEPAR20252620250901.csv     # 2.4MB - Partizioni elettorali
SCUANAAUTPAR20252620250901.csv       # 16KB - Partizioni autonomie
```

### Fase 2 (Comune)

File specifici per comune:

```
ROMA - Sezioni.csv                   # 101KB - Sezioni Roma con indirizzi
<ALTRO_COMUNE> - Sezioni.csv         # Da richiedere al comune
```

**Come ottenere CSV del tuo comune:**
1. Contatta Ufficio Elettorale del comune
2. Richiedi CSV con formato: `SEZIONE, COMUNE, MUNICIPIO, INDIRIZZO`
3. Salva in `backend_django/fixtures/<COMUNE> - Sezioni.csv`
4. Esegui `update_sezioni_dettagli`

---

## 🚀 Script Automatico

Lo script `init-db.sh` gestisce tutto automaticamente:

```bash
./scripts/init-db.sh
```

**Ordine degli step:**
1. ✅ Migrations
2. ✅ Regioni e Province
3. ✅ Consultazione
4. ✅ Comuni (Fase 1 ISTAT)
5. ✅ Municipi Roma (richiede Fase 1)
6. ✅ Sezioni Italia (Fase 1 ISTAT)
7. ✅ Update Sezioni Roma (Fase 2 Comune)
8. ✅ Superuser

---

## 🐛 Troubleshooting

### "Roma non esiste nel database" (municipi)

**Problema:** Stai caricando municipi PRIMA dei comuni

**Soluzione:** Esegui prima Step 4 (comuni), poi Step 5 (municipi)

### "Sezioni non trovate" (update_sezioni_dettagli)

**Problema:** Le sezioni non sono state importate (Step 2)

**Soluzione:**
```bash
docker-compose exec backend python manage.py import_sezioni_italia --file fixtures/SCUANAGRAFESTAT20252620250901.csv
```

### "Import troppo lento"

**Problema:** Import di 60.000 sezioni richiede tempo

**Soluzioni:**
- Importa solo un comune specifico: `--comune-codice 058091` (Roma)
- Usa PostgreSQL invece di SQLite
- Esegui in background

### "File CSV non trovato"

**Verifica percorsi:**
- Con Docker: working dir è `/app` → path `fixtures/file.csv`
- Senza Docker: working dir è root progetto → path `backend_django/fixtures/file.csv`

---

## 📖 Management Commands Disponibili

| Command | Scopo | Fase |
|---------|-------|------|
| `import_comuni_istat` | Import comuni e plessi ISTAT | 1 |
| `import_sezioni_italia` | Import sezioni nazionali | 1 |
| `update_sezioni_dettagli` | Update indirizzi specifici | 2 |
| `match_sezioni_scuole` | Match sezioni → scuole | 2 |
| `import_municipi` | Import municipi (es. Roma) | Extra |

**Help comando:**
```bash
docker-compose exec backend python manage.py <command> --help
```

---

## 📚 Riferimenti

- **Database Init:** `DATABASE_INIT.md`
- **Docker Setup:** `DOCKER_SETUP.md`
- **Consultazione Attiva:** `CONSULTAZIONE_ATTIVA.md`
- **ISTAT Open Data:** https://dati.istat.it/
- **Ministero Interno:** https://dait.interno.gov.it/
