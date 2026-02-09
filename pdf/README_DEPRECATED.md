# DEPRECATED

Questa directory contiene il vecchio sistema di generazione PDF asincrona (worker basato su Redis).

**Status**: OBSOLETO - Non più utilizzato

## Motivo della deprecazione

La generazione PDF è stata migrata a **sincrona** direttamente nel backend Django 
(`backend_django/delegations/views_processo.py`) per semplificare l'architettura.

## Nuovo sistema

- **Backend**: `views_processo.py` genera PDF sincroni usando ReportLab
- **Frontend**: `GestioneDesignazioni.js` gestisce il workflow di designazione
- **No più worker**: Eliminato servizio `pdf-worker` dal docker-compose

## Cosa rimaneva qui

- `worker.py` - Worker Redis per generazione asincrona
- `generate.py` - Logica di generazione PDF
- `email_sender.py` - Invio email con allegati
- `Dockerfile.worker` - Container per il worker

## Data deprecazione

Febbraio 2026 - Rimosso dal docker-compose.yml
