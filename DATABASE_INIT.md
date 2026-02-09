# 🗄️ Inizializzazione Database - Guida Rapida

Se hai resettato il database o lo stai configurando per la prima volta, segui questa guida.

---

## 🚀 Metodo Veloce (1 comando)

```bash
./scripts/init-db.sh
```

**Cosa fa lo script:**
1. ✅ Esegue migrations Django
2. ✅ Carica **Regioni** (20) e **Province** (107) italiane
3. ✅ Carica **Consultazione Elettorale 2025** attiva
4. ✅ Importa **~8.000 Comuni** da CSV ISTAT
5. ✅ Importa **Sezioni** (opzionale, chiede conferma)
6. ✅ Crea **Superuser** Django (opzionale, chiede conferma)

**Tempo richiesto:** 2-5 minuti

---

## 📋 Cosa Viene Caricato

### Dati Territoriali

| Livello | Quantità | Fonte |
|---------|----------|-------|
| **Regioni** | 20 | `fixtures/initial_data.json` |
| **Province** | 107 | `fixtures/initial_data.json` |
| **Comuni** | ~8.000 | CSV ISTAT (automatic import) |
| **Municipi** | 15 (Roma) | `fixtures/roma_municipi.json` (optional) |
| **Sezioni** | ~60.000 | CSV ISTAT (optional, richiede tempo) |

### Consultazione Elettorale 2025

| Tipo Elezione | Schede | Dettagli |
|--------------|--------|----------|
| **REFERENDUM** | 5 | Cittadinanza, Lavoro, Giustizia, Autonomia, Jobs Act |
| **EUROPEE** | 1 | Elezioni Parlamento Europeo |
| **POLITICHE_CAMERA** | 1 | Camera (suppletiva) |
| **COMUNALI** | 1 | Vari comuni |

**Data:** 17 Giugno 2025
**Stato:** Attiva (`is_attiva=True`)

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
docker-compose exec backend python manage.py loaddata fixtures/consultazione_multipla_2025.json

# Senza Docker
cd backend_django && python manage.py loaddata fixtures/consultazione_multipla_2025.json
```

**Risultato:** Consultazione 2025 + 4 TipiElezione + 8 Schede

### 4. Comuni (CSV ISTAT)

```bash
# Con Docker
docker-compose exec backend python manage.py import_comuni_istat fixtures/SCUANAGRAFESTAT20252620250901.csv

# Senza Docker
cd backend_django && python manage.py import_comuni_istat fixtures/SCUANAGRAFESTAT20252620250901.csv
```

**Tempo:** ~1-2 minuti
**Risultato:** ~8.000 Comuni con dati ISTAT

### 5. Sezioni (Opzionale)

⚠️ **Attenzione:** Import di ~60.000 sezioni richiede **5-10 minuti**

```bash
# Con Docker
docker-compose exec backend python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv

# Senza Docker
cd backend_django && python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv
```

**Alternativa veloce:** Importa solo sezioni specifiche di un comune:

```bash
# Esempio: solo Roma
docker-compose exec backend python manage.py import_sezioni_italia fixtures/SCUANAGRAFESTAT20252620250901.csv --comune-codice 058091
```

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

I file CSV ISTAT sono già inclusi in `backend_django/fixtures/`:
- `SCUANAGRAFESTAT20252620250901.csv` (comuni + sezioni)
- `SCUANAGRAFEPAR20252620250901.csv` (partizioni)

Se mancano, scaricali da:
- https://dati.istat.it/Index.aspx?DataSetCode=DICA_COMDISTRICIRC

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

La consultazione viene caricata con `is_attiva=False` di default. Attivala:

```bash
# Django shell
docker-compose exec backend python manage.py shell
>>> from elections.models import ConsultazioneElettorale
>>> c = ConsultazioneElettorale.objects.get(nome__contains="2025")
>>> c.is_attiva = True
>>> c.save()
```

Oppure dall'admin: http://localhost:3001/admin

---

## 📖 Management Commands Disponibili

| Command | Descrizione |
|---------|-------------|
| `import_comuni_istat <csv>` | Import comuni da CSV ISTAT |
| `import_sezioni_italia <csv>` | Import sezioni da CSV ISTAT |
| `import_municipi <json>` | Import municipi (es. Roma) |
| `match_sezioni_scuole` | Match sezioni con scuole |
| `update_sezioni_dettagli` | Aggiorna dettagli sezioni |

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
