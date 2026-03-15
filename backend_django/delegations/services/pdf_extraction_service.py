"""
Servizio per estrazione pagine specifiche da PDF di designazione con filesystem caching.
"""
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
import hashlib
import logging

logger = logging.getLogger(__name__)


def _open_file(file_field):
    """Apre un FileField usando default_storage (funziona con GCS e filesystem locale)."""
    return default_storage.open(file_field.name, 'rb')


class PDFExtractionService:
    """
    Estrae pagine specifiche da PDF individuale per singolo RDL con caching.
    """

    CACHE_DIR = Path(settings.MEDIA_ROOT) / 'pdf_cache'

    @staticmethod
    def estrai_pagine_rdl(designazioni, user_email: str) -> bytes:
        """
        Estrae pagine del PDF individuale corrispondenti alle sezioni RDL con caching.
        Prepende le pagine della nomina del delegato (se presente).

        Args:
            designazioni: QuerySet di DesignazioneRDL (tutte le sezioni dell'RDL)
            user_email: Email utente (per cache key)

        Returns:
            bytes del PDF estratto
        """
        if not designazioni.exists():
            raise ValueError("Nessuna designazione fornita")

        processo = designazioni.first().processo

        if not processo.documento_individuale:
            raise ValueError("PDF individuale non disponibile per questo processo")

        # Trova il delegato (dal processo)
        delegato = processo.delegato

        # Cache key include anche presenza documento_nomina delegato
        has_nomina = bool(delegato and delegato.documento_nomina)
        sezioni_ids = sorted([des.sezione_id for des in designazioni])
        cache_key = hashlib.md5(
            f"{processo.id}_{user_email}_{','.join(map(str, sezioni_ids))}_{has_nomina}".encode()
        ).hexdigest()

        cache_filename = f"{cache_key}.pdf"
        cache_file = PDFExtractionService.CACHE_DIR / cache_filename

        if cache_file.exists():
            logger.info(f"PDF cache HIT: {cache_key}")
            return cache_file.read_bytes()

        logger.info(f"PDF cache MISS: {cache_key}, generando...")

        # ===== GENERA PDF =====
        tutte_designazioni = list(
            processo.designazioni
            .filter(stato='CONFERMATA', is_attiva=True)
            .order_by('sezione__numero')
        )

        sezione_to_page = {
            des.sezione_id: idx
            for idx, des in enumerate(tutte_designazioni)
        }

        sezioni_rdl = [des.sezione_id for des in designazioni]
        sezioni_rdl_unique = sorted(set(sezioni_rdl))

        pagine_da_estrarre = sorted([
            sezione_to_page[sezione_id]
            for sezione_id in sezioni_rdl_unique
            if sezione_id in sezione_to_page
        ])

        if not pagine_da_estrarre:
            raise ValueError("Nessuna pagina trovata per le sezioni specificate")

        writer = PdfWriter()

        # 1. Prependi pagine nomina delegato (se presente)
        if has_nomina:
            try:
                with _open_file(delegato.documento_nomina) as f:
                    nomina_reader = PdfReader(f)
                    for page in nomina_reader.pages:
                        writer.add_page(page)
                logger.info(f"Aggiunta nomina delegato: {nomina_reader.pages.__len__()} pagine")
            except Exception as e:
                logger.warning(f"Impossibile aggiungere nomina delegato: {e}")

        # 2. Pagine designazione RDL
        with _open_file(processo.documento_individuale) as f:
            reader = PdfReader(f)
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
        cache_file.write_bytes(pdf_bytes)

        logger.info(
            f"PDF estratto e cached: {len(pagine_da_estrarre)} pagine designazione"
            f"{' + nomina delegato' if has_nomina else ''} "
            f"per {len(sezioni_rdl)} sezioni"
        )

        return pdf_bytes
