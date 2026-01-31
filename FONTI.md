# Fonti Dati - RDL Referendum App

Documentazione delle fonti ufficiali utilizzate per i dati dell'applicazione.

---

## 1. Territorio Italiano

### Fonte Ufficiale ISTAT
- **ISTAT - Codici statistici unità amministrative**: https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
  - Elenco ufficiale comuni, province, regioni
  - Aggiornato al 1 gennaio 2026
  - 7.896 comuni (dal 22 gennaio 2024)

- **ISTAT CSV Comuni**: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
  - Download diretto CSV con tutti i comuni italiani
  - Colonne: codice regione, provincia, comune, denominazione, sigla, CAP, ecc.

- **ISTAT XLS Comuni**: https://www4.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xls
  - Stesso contenuto in formato Excel

### Codici ISTAT Regioni

| Codice | Regione | Statuto |
|--------|---------|---------|
| 01 | Piemonte | Ordinario |
| 02 | Valle d'Aosta | Speciale |
| 03 | Lombardia | Ordinario |
| 04 | Trentino-Alto Adige | Speciale |
| 05 | Veneto | Ordinario |
| 06 | Friuli-Venezia Giulia | Speciale |
| 07 | Liguria | Ordinario |
| 08 | Emilia-Romagna | Ordinario |
| 09 | Toscana | Ordinario |
| 10 | Umbria | Ordinario |
| 11 | Marche | Ordinario |
| 12 | Lazio | Ordinario |
| 13 | Abruzzo | Ordinario |
| 14 | Molise | Ordinario |
| 15 | Campania | Ordinario |
| 16 | Puglia | Ordinario |
| 17 | Basilicata | Ordinario |
| 18 | Calabria | Ordinario |
| 19 | Sicilia | Speciale |
| 20 | Sardegna | Speciale |

### Altre Fonti Territoriali
- **ADM (Agenzia Dogane e Monopoli)**: https://www.adm.gov.it/portale/documents/20182/900944/Codici+ISTAT+delle+regioni.pdf
- **DAIT (Dipartimento Affari Interni)**: https://dait.interno.gov.it/documenti/decreto-fl-24-06-2021-2-all-a.pdf
- **INAIL Open Data Province**: https://dati.inail.it/portale/it/dataset/infortuni-sul-lavoro/tipologiche/province-italiane.html
- **Garda Informatica DB Comuni**: https://www.gardainformatica.it/database-comuni-italiani
- **ANUSCA Codici ISTAT**: https://www.anusca.it/flex/cm/pages/ServeBLOB.php/L/IT/IDPagina/3999
- **Wikipedia Codice ISTAT**: https://it.wikipedia.org/wiki/Codice_ISTAT

### Note sui Codici
- I codici ISTAT usano un criterio geografico (nord-sud)
- I codici Agenzia delle Entrate usano un criterio alfabetico
- Dal 2015 le Città Metropolitane hanno codici 2xx (es. 201 Torino, 215 Roma)
- La Sardegna avrà nuovi assetti territoriali dal 1 gennaio 2026

---

## 2. Sistema Elettorale Italiano

### Normativa di Riferimento
- **Costituzione della Repubblica Italiana**
  - Art. 48: Diritto di voto
  - Art. 56-57: Elezione Camera e Senato
  - Art. 75: Referendum abrogativo
  - Art. 138: Referendum costituzionale confermativo

- **Testo Unico Elezioni (D.P.R. 361/1957)**
  - https://www.normattiva.it/uri-res/N2Ls?urn:nir:presidente.repubblica:decreto:1957-03-30;361

- **Legge elettorale Rosatellum (L. 165/2017)**
  - Sistema misto proporzionale-uninominale

### Circoscrizioni Europee
5 macro-circoscrizioni per le elezioni del Parlamento Europeo:
1. **Italia Nord-Occidentale**: Piemonte, Valle d'Aosta, Lombardia, Liguria
2. **Italia Nord-Orientale**: Trentino-AA, Veneto, Friuli-VG, Emilia-Romagna
3. **Italia Centrale**: Toscana, Umbria, Marche, Lazio
4. **Italia Meridionale**: Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria
5. **Italia Insulare**: Sicilia, Sardegna

---

## 3. Referendum Giustizia 2026

### Date e Orari
- **Date**: 22-23 marzo 2026
- **Orari**: Domenica 7:00-23:00, Lunedì 7:00-15:00

### Tipo
- **Referendum confermativo costituzionale** (art. 138 Cost.)
- **NON richiede quorum**: valido indipendentemente dall'affluenza

### Quesito Ufficiale
> "Approvate il testo della legge costituzionale concernente «Norme in materia di ordinamento giurisdizionale e di istituzione della Corte disciplinare» approvato dal Parlamento e pubblicato nella Gazzetta Ufficiale della Repubblica italiana – Serie generale – n. 253 del 30 ottobre 2025?"

### Articoli Costituzionali Modificati
- Art. 87 (Presidente della Repubblica)
- Art. 102 (Funzione giurisdizionale)
- Art. 104 (CSM)
- Art. 105 (Attribuzioni CSM)
- Art. 106 (Nomina magistrati)
- Art. 107 (Inamovibilità magistrati)
- Art. 110 (Ministro della giustizia)

### Fonti
- **Geopop**: https://www.geopop.it/il-referendum-sulla-giustizia-del-22-e-23-marzo-non-avra-il-quorum-cosa-significa-e-come-funzionera-il-voto/
- **Prefettura Venezia**: https://prefettura.interno.gov.it/it/prefetture/venezia/notizie/referendum-giustizia-vota-22-e-23-marzo
- **Pagella Politica**: https://pagellapolitica.it/articoli/testo-quesito-referendum-costituzionale-giustizia-separazione-carriere-magistrati
- **Ministero Giustizia**: https://firmereferendum.giustizia.it/referendum/open/dettaglio-open/5400034
- **Questione Giustizia**: https://www.questionegiustizia.it/articolo/data-referendum
- **Avvocato Ticozzi**: https://www.avvocatoticozzi.it/it/blog/414/referendum-giustizia-2026-separazione-carriere

### Quesiti Abrogativi (storici, per riferimento)
- **Sistema Penale**: https://www.sistemapenale.it/it/scheda/referendum-giustizia-guida-lettura-quesiti
- **Istituto Sike**: https://www.istitutosike.com/wp/referendum-sulla-giustizia-breve-guida-ai-quesiti/

---

## 4. Autenticazione e Sicurezza

### Google OAuth 2.0
- **Google Identity Services**: https://developers.google.com/identity
- **OAuth 2.0 per Web Server**: https://developers.google.com/identity/protocols/oauth2/web-server

### Django Allauth
- **Documentazione**: https://docs.allauth.org/
- **Provider Google**: https://docs.allauth.org/en/latest/socialaccount/providers/google.html

### Magic Link
- **Django Signing**: https://docs.djangoproject.com/en/5.0/topics/signing/
- **Best Practices**: pattern comune per auth passwordless

---

## 5. PDF Generation

### PyMuPDF (fitz)
- **Documentazione**: https://pymupdf.readthedocs.io/
- **GitHub**: https://github.com/pymupdf/PyMuPDF

### Template Delega
- Modelli Ministero dell'Interno per deleghe RDL

---

## 6. Deployment

### Google App Engine
- **Django su GAE**: https://cloud.google.com/python/django/appengine
- **Cloud SQL**: https://cloud.google.com/sql/docs/postgres

### Docker
- **Distroless Images**: https://github.com/GoogleContainerTools/distroless
- **Python Distroless**: gcr.io/distroless/python3-debian12

---

## Ultima Verifica

**Data**: 31 gennaio 2026
**Versione App**: 2.0 (Django)
