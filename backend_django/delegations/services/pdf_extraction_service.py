"""
Servizio per estrazione pagine specifiche da PDF di designazione con caching.
"""
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from pathlib import Path
from django.conf import settings
import hashlib
import logging

from core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class PDFExtractionService:
    """
    Estrae pagine specifiche da PDF individuale per singolo RDL con caching.
    """

    CACHE_DIR = Path(settings.MEDIA_ROOT) / 'pdf_cache'

    @staticmethod
    def estrai_pagine_rdl(designazioni, user_email: str) -> bytes:
        """
        Estrae pagine del PDF individuale corrispondenti alle sezioni RDL con caching.

        NOTA: Estrae TUTTE le sezioni assegnate all'RDL, indipendentemente dal ruolo
        (effettivo/supplente), poiché l'RDL può avere entrambi i ruoli.

        Args:
            designazioni: QuerySet di DesignazioneRDL (tutte le sezioni dell'RDL)
            user_email: Email utente (per cache key)

        Returns:
            bytes del PDF estratto

        Raises:
            ValueError se nessun PDF individuale trovato
        """
        if not designazioni.exists():
            raise ValueError("Nessuna designazione fornita")

        processo = designazioni.first().processo

        if not processo.documento_individuale:
            raise ValueError("PDF individuale non disponibile per questo processo")

        # ===== CACHE CHECK =====
        # Cache key basata su processo + user_email (include TUTTE le sezioni dell'RDL)
        sezioni_ids = sorted([des.sezione_id for des in designazioni])
        cache_key = hashlib.md5(
            f"{processo.id}_{user_email}_{','.join(map(str, sezioni_ids))}".encode()
        ).hexdigest()

        # Check Redis cache (metadata) + filesystem cache
        r = get_redis_client()
        if r:
            redis_key = f"pdf_nomina:{cache_key}"
            cached_filename = r.get(redis_key)

            if cached_filename:
                cache_file = PDFExtractionService.CACHE_DIR / cached_filename
                if cache_file.exists():
                    logger.info(f"PDF cache HIT: {cache_key}")
                    return cache_file.read_bytes()

        logger.info(f"PDF cache MISS: {cache_key}, generando...")

        # ===== GENERA PDF =====
        # Mappa sezione_id -> indice pagina (0-based)
        # STRATEGIA: Pagine ordinate per numero sezione crescente (una sezione = una pagina)
        tutte_designazioni = list(
            processo.designazioni
            .filter(stato='CONFERMATA', is_attiva=True)
            .order_by('sezione__numero_sezione')
        )

        sezione_to_page = {
            des.sezione_id: idx
            for idx, des in enumerate(tutte_designazioni)
        }

        # IDs delle sezioni dell'RDL (può essere effettivo per alcune, supplente per altre)
        # NOTA: designazioni contiene TUTTE le DesignazioneRDL dove user_email compare
        # (come effettivo O come supplente), quindi sezioni_rdl include tutte le sezioni
        sezioni_rdl = [des.sezione_id for des in designazioni]

        # Rimuovi duplicati (se presenti) e ordina
        sezioni_rdl_unique = sorted(set(sezioni_rdl))

        # Indici delle pagine da estrarre
        pagine_da_estrarre = sorted([
            sezione_to_page[sezione_id]
            for sezione_id in sezioni_rdl_unique
            if sezione_id in sezione_to_page
        ])

        if not pagine_da_estrarre:
            raise ValueError("Nessuna pagina trovata per le sezioni specificate")

        # Leggi PDF originale
        reader = PdfReader(processo.documento_individuale.path)

        # Crea PDF di output con solo le pagine selezionate
        writer = PdfWriter()

        for page_idx in pagine_da_estrarre:
            if page_idx < len(reader.pages):
                writer.add_page(reader.pages[page_idx])
            else:
                logger.warning(f"Pagina {page_idx} non trovata nel PDF")

        # Scrivi PDF in memoria
        output_buffer = BytesIO()
        writer.write(output_buffer)
        pdf_bytes = output_buffer.getvalue()

        # ===== SALVA IN CACHE =====
        PDFExtractionService.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache_filename = f"{cache_key}.pdf"
        cache_file = PDFExtractionService.CACHE_DIR / cache_filename
        cache_file.write_bytes(pdf_bytes)

        # Salva metadata in Redis (TTL 7 giorni) se disponibile
        if r:
            r.setex(redis_key, 7 * 24 * 3600, str(cache_filename))

        logger.info(
            f"PDF estratto e cached: {len(pagine_da_estrarre)} pagine "
            f"per {len(sezioni_rdl)} sezioni"
        )

        return pdf_bytes
