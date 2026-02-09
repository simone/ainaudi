# 🗳️ Consultazione Attiva - Referendum Costituzionale 2026

## 📋 Informazioni Generali

**Nome:** Referendum Costituzionale Giustizia 2026

**Tipologia:** Referendum popolare confermativo (art. 138 Costituzione)

**Oggetto:** Legge costituzionale "Norme in materia di ordinamento giurisdizionale e di istituzione della Corte disciplinare"

**Fonte ufficiale:** [Ministero Affari Esteri](https://www.esteri.it/it/sala_stampa/archivionotizie/comunicati/2026/01/referendum-costituzionale-confermativo-dei-giorni-22-e-23-marzo-2026/)

---

## 📅 Date e Orari

**Domenica 22 marzo 2026:** ore 7:00 - 23:00
**Lunedì 23 marzo 2026:** ore 7:00 - 15:00

---

## 🎯 Oggetto del Referendum

Il referendum riguarda la **separazione delle carriere** tra magistrati giudicanti e requirenti, con modifiche sostanziali al sistema giudiziario italiano.

### Articoli Costituzionali Modificati

- Art. 87 - Presidente della Repubblica
- Art. 102 - Funzione giurisdizionale
- Art. 104 - Magistratura come ordine autonomo
- Art. 105 - Consiglio Superiore della Magistratura
- Art. 106 - Nomina dei magistrati
- Art. 107 - Inamovibilità dei magistrati
- Art. 110 - Alta Corte

### Novità Principale

**Istituzione della Corte Disciplinare** - nuovo organo separato per le questioni disciplinari dei magistrati.

---

## ⚖️ Caratteristiche Legali

### Tipo di Referendum

**Confermativo** ex art. 138 Cost. (non abrogativo)

### Quorum

❌ **NON richiesto**

Il referendum costituzionale confermativo NON richiede il raggiungimento del quorum. La maggioranza dei voti validamente espressi è sufficiente per l'approvazione o il rigetto della riforma.

### Pubblicazione

Gazzetta Ufficiale n. 253 del 30 ottobre 2025

---

## 🗳️ Scheda Elettorale

### Quesito

> "Approvate il testo della legge costituzionale concernente 'Norme in materia di ordinamento giurisdizionale e di istituzione della Corte disciplinare', approvato dal Parlamento e pubblicato nella Gazzetta Ufficiale n. 253 del 30 ottobre 2025?"

### Opzioni di Voto

- **SI** - Approva la riforma costituzionale
- **NO** - Rigetta la riforma costituzionale

### Colore Scheda

**Verde**

---

## 💻 Configurazione Tecnica

### Database

```python
# Consultazione
pk: 1
nome: "Referendum Costituzionale Giustizia 2026"
data_inizio: 2026-03-22
data_fine: 2026-03-23
is_attiva: True

# Tipo Elezione
pk: 1
tipo: "REFERENDUM"
ambito_nazionale: True

# Scheda Elettorale
pk: 1
nome: "Referendum Costituzionale - Riforma Giustizia"
colore: "verde"
schema_voti: {"tipo": "si_no", "options": ["SI", "NO"]}
```

### Fixture

File: `backend_django/fixtures/referendum_giustizia_2026.json`

Caricamento:
```bash
python manage.py loaddata fixtures/referendum_giustizia_2026.json
```

---

## 📊 Gestione App AInaudi

### Funzionalità Attive

- ✅ **Mappatura RDL** - Assegnazione rappresentanti di lista per sezione
- ✅ **Designazioni** - Generazione atti formali di designazione
- ✅ **Scrutinio** - Raccolta dati dai seggi
- ✅ **Dashboard KPI** - Monitoraggio copertura territoriale
- ✅ **Catena Deleghe** - Delegato → SubDelegato → RDL

### Scheda Compilazione

La scheda prevede raccolta di:
- Voti SI
- Voti NO
- Schede bianche
- Schede nulle
- Schede contestate

---

## 📖 Risorse

### Link Utili

- [Comunicato Ministero Esteri](https://www.esteri.it/it/sala_stampa/archivionotizie/comunicati/2026/01/referendum-costituzionale-confermativo-dei-giorni-22-e-23-marzo-2026/)
- [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/)
- [Dipartimento Affari Interni e Territoriali](https://dait.interno.gov.it/)

### Documentazione Tecnica

- `DATABASE_INIT.md` - Inizializzazione database
- `DOCKER_SETUP.md` - Setup ambiente sviluppo
- `CLAUDE.md` - Architettura sistema

---

## 🔄 Aggiornamenti

**Ultimo aggiornamento:** 9 febbraio 2026
**Stato:** Consultazione attiva e configurata
**Prossimo milestone:** Giorno della votazione (22-23 marzo 2026)

---

## ⚙️ Comandi Utili

```bash
# Verifica consultazione attiva
docker-compose exec backend python manage.py shell
>>> from elections.models import ConsultazioneElettorale
>>> c = ConsultazioneElettorale.objects.get(is_attiva=True)
>>> print(f"{c.nome} - {c.data_inizio} / {c.data_fine}")

# Conta sezioni assegnate
>>> from data.models import SectionAssignment
>>> print(SectionAssignment.objects.count())

# Verifica RDL registrati
>>> from campaign.models import RdlRegistration
>>> print(RdlRegistration.objects.filter(stato='APPROVATO').count())
```

---

**Per domande o supporto:** Consulta `CLAUDE.md` o `DATABASE_INIT.md`
