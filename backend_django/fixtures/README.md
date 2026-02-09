# 📁 Fixtures Directory - CSV ISTAT

## ⚠️ IMPORTANTE: CSV Corretti Necessari

I file CSV attualmente presenti (`SCUANA*.csv`) contengono dati delle **SCUOLE** (plessi scolastici), NON i comuni italiani.

Per inizializzare correttamente il database servono i CSV giusti dall'ISTAT.

---

## 🔽 Download CSV Corretti

### Metodo Automatico (Raccomandato)

```bash
cd ../..  # Torna alla root del progetto
./scripts/download-csv-istat.sh
```

### Metodo Manuale

#### 1. Comuni Italiani

**Fonte:** ISTAT - Elenco Comuni
**URL:** https://www.istat.it/it/archivio/6789

**Download:**
1. Vai sul sito ISTAT
2. Cerca "Elenco comuni italiani"
3. Scarica il CSV più recente
4. Salva come: `comuni_istat.csv`

**Formato atteso:**
```csv
Codice Regione,Codice Provincia,Codice Comune,Denominazione,Nome in italiano,...
01,001,001,AGLIE',Agliè,...
01,001,002,AIRASCA,Airasca,...
```

#### 2. Sezioni Elettorali

**Fonte:** Ministero dell'Interno - DAIT
**URL:** https://dait.interno.gov.it/

**Download:**
1. Vai su "Territorio e Autonomie Locali"
2. Cerca "Anagrafe Sezioni Elettorali"
3. Scarica il file (potrebbe essere XLS o CSV)
4. Se XLS, converti in CSV
5. Salva come: `sezioni_italia.csv`

**Formato atteso:**
```csv
Codice ISTAT,Comune,Sezione,Indirizzo,CAP,...
058091,ROMA,1,VIA DANIELE MANIN 72,00185,...
```

---

## 📋 File Necessari

| File | Descrizione | Dimensione | Obbligatorio |
|------|-------------|------------|--------------|
| `comuni_istat.csv` | Elenco comuni italiani | ~2-3 MB | ✅ SÌ |
| `sezioni_italia.csv` | Sezioni elettorali nazionali | ~5-10 MB | ⚠️ Raccomandato |
| `ROMA - Sezioni.csv` | Dettagli sezioni Roma | ~100 KB | ❌ Opzionale |
| `roma_municipi.json` | Municipi di Roma | ~2 KB | ❌ Opzionale |

---

## 🗂️ File Attuali (Da Sostituire)

I file `SCUANA*.csv` attualmente presenti sono:

- `SCUANAGRAFESTAT20252620250901.csv` (13MB) - **SCUOLE**, non comuni
- `SCUANAGRAFEPAR20252620250901.csv` (2.4MB) - Partizioni scuole
- `SCUANAAUTSTAT20252620250901.csv` (305KB) - Scuole autonome
- `SCUANAAUTPAR20252620250901.csv` (16KB) - Partizioni autonome

❌ **Questi NON servono** per l'import di comuni e sezioni.

---

## 🚀 Dopo il Download

Una volta scaricati i CSV corretti:

```bash
# Import comuni
docker-compose exec backend python manage.py import_comuni_istat --file fixtures/comuni_istat.csv

# Import sezioni (opzionale)
docker-compose exec backend python manage.py import_sezioni_italia --file fixtures/sezioni_italia.csv
```

Oppure usa lo script automatico:

```bash
./scripts/init-db.sh
```

---

## 📖 Documentazione

- **Guida completa import:** `../../SEZIONI_IMPORT.md`
- **Setup database:** `../../DATABASE_INIT.md`
- **Docker setup:** `../../DOCKER_SETUP.md`

---

## 🐛 Troubleshooting

### "CSV columns: ANNOSCOLASTICO,AREAGEOGRAFICA,..."

**Problema:** Stai usando il CSV delle scuole invece dei comuni

**Soluzione:** Scarica il CSV corretto dall'ISTAT (vedi sopra)

### "File CSV non trovato"

**Problema:** I CSV non sono stati scaricati

**Soluzione:** Esegui `./scripts/download-csv-istat.sh`

### "Download fallito" (script automatico)

**Problema:** URL ISTAT cambiato

**Soluzione:** Download manuale (vedi sezione sopra)

---

## 📞 Link Utili

- **ISTAT Open Data:** https://www.istat.it/it/archivio/6789
- **Ministero Interno DAIT:** https://dait.interno.gov.it/
- **ISTAT Codici Comuni:** https://www.istat.it/it/archivio/6789
- **Ministero Elezioni:** https://dait.interno.gov.it/elezioni

---

**Ultimo aggiornamento:** 9 febbraio 2026
