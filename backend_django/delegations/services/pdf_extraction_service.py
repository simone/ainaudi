"""
Servizio per estrazione pagine specifiche da PDF di designazione.
Pre-genera PDF individuali per ogni RDL su GCS per download diretto.
"""
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import hashlib
import logging

logger = logging.getLogger(__name__)


def _open_file(file_field):
    """Apre un FileField usando default_storage (funziona con GCS e filesystem locale)."""
    return default_storage.open(file_field.name, 'rb')


class PDFExtractionService:
    """
    Estrae pagine specifiche da PDF individuale per singolo RDL.
    Supporta pre-generazione su GCS per download diretto.
    """

    @staticmethod
    def get_rdl_pdf_path(processo_id, email):
        """Path GCS per il PDF pre-generato di un RDL."""
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()[:12]
        return f'deleghe/processi/processo_{processo_id}/rdl/{email_hash}.pdf'

    @staticmethod
    def get_rdl_pdf_url(processo_id, email):
        """URL pubblico GCS per il PDF pre-generato di un RDL. None se non esiste."""
        path = PDFExtractionService.get_rdl_pdf_path(processo_id, email)
        if default_storage.exists(path):
            return default_storage.url(path)
        return None

    @staticmethod
    def pre_genera_pdf_rdl(processo):
        """
        Pre-genera PDF individuali per ogni RDL del processo e li salva su GCS.
        Scarica il PDF master UNA volta, poi estrae le pagine per ogni RDL.

        Returns:
            dict con {'generati': int, 'errori': int, 'dettagli': [...]}
        """
        from delegations.models import DesignazioneRDL

        if not processo.documento_individuale:
            raise ValueError("PDF individuale non disponibile")

        # Tutte le designazioni ordinate per sezione (come nel PDF)
        tutte_designazioni = list(
            processo.designazioni
            .filter(stato='CONFERMATA', is_attiva=True)
            .order_by('sezione__numero')
        )

        if not tutte_designazioni:
            raise ValueError("Nessuna designazione confermata")

        # Mappa sezione_id → indice pagina nel PDF
        sezione_to_page = {
            des.sezione_id: idx
            for idx, des in enumerate(tutte_designazioni)
        }

        # Raggruppa sezioni per email RDL (effettivo e supplente)
        rdl_sezioni = {}  # email → set di sezione_id
        for des in tutte_designazioni:
            if des.effettivo_email:
                rdl_sezioni.setdefault(des.effettivo_email, set()).add(des.sezione_id)
            if des.supplente_email:
                rdl_sezioni.setdefault(des.supplente_email, set()).add(des.sezione_id)

        logger.info(
            f"[PreGen] Processo {processo.id}: {len(tutte_designazioni)} designazioni, "
            f"{len(rdl_sezioni)} RDL distinti"
        )

        # Scarica PDF master UNA volta
        import tempfile, os
        tmp_path = os.path.join(tempfile.gettempdir(), f'master_{processo.id}.pdf')
        with _open_file(processo.documento_individuale) as f:
            with open(tmp_path, 'wb') as out:
                for chunk in iter(lambda: f.read(8192), b''):
                    out.write(chunk)

        reader = PdfReader(tmp_path)
        total_pages = len(reader.pages)
        logger.info(f"[PreGen] PDF master scaricato: {total_pages} pagine")

        # Pagine nomina delegato (se presente)
        nomina_pages = []
        delegato = processo.delegato
        if delegato and delegato.documento_nomina:
            try:
                with _open_file(delegato.documento_nomina) as f:
                    nomina_reader = PdfReader(f)
                    nomina_pages = list(nomina_reader.pages)
                logger.info(f"[PreGen] Nomina delegato: {len(nomina_pages)} pagine")
            except Exception as e:
                logger.warning(f"[PreGen] Errore nomina delegato: {e}")

        # Genera PDF per ogni RDL
        generati = 0
        errori = 0
        dettagli = []
        base_dir = f'deleghe/processi/processo_{processo.id}/rdl'

        for email, sezioni_ids in rdl_sezioni.items():
            try:
                pagine = sorted([
                    sezione_to_page[sid]
                    for sid in sezioni_ids
                    if sid in sezione_to_page
                ])

                if not pagine:
                    continue

                writer = PdfWriter()

                # Pagine designazione
                for page_idx in pagine:
                    if page_idx < total_pages:
                        writer.add_page(reader.pages[page_idx])

                # Pagine nomina delegato
                for page in nomina_pages:
                    writer.add_page(page)

                # Salva su GCS
                output = BytesIO()
                writer.write(output)

                gcs_path = PDFExtractionService.get_rdl_pdf_path(processo.id, email)
                if default_storage.exists(gcs_path):
                    default_storage.delete(gcs_path)
                default_storage.save(gcs_path, ContentFile(output.getvalue()))

                generati += 1
                if generati % 100 == 0:
                    logger.info(f"[PreGen] Processo {processo.id}: {generati}/{len(rdl_sezioni)} generati")

            except Exception as e:
                errori += 1
                dettagli.append(f"{email}: {str(e)}")
                logger.error(f"[PreGen] Errore per {email}: {e}")

        # Cleanup
        os.unlink(tmp_path)

        logger.info(
            f"[PreGen] Processo {processo.id}: completato. "
            f"{generati} generati, {errori} errori"
        )

        return {
            'generati': generati,
            'errori': errori,
            'totale_rdl': len(rdl_sezioni),
            'dettagli': dettagli
        }

    @staticmethod
    def estrai_pagine_rdl(designazioni, user_email: str) -> bytes:
        """
        Estrae pagine del PDF individuale per un RDL.
        Prima prova il PDF pre-generato su GCS, altrimenti estrae al volo.
        """
        if not designazioni.exists():
            raise ValueError("Nessuna designazione fornita")

        processo = designazioni.first().processo

        if not processo.documento_individuale:
            raise ValueError("PDF individuale non disponibile per questo processo")

        # Prova PDF pre-generato su GCS
        gcs_path = PDFExtractionService.get_rdl_pdf_path(processo.id, user_email)
        if default_storage.exists(gcs_path):
            logger.info(f"[PDFExtract] GCS cache HIT: {gcs_path}")
            with default_storage.open(gcs_path, 'rb') as f:
                return f.read()

        logger.info(f"[PDFExtract] GCS cache MISS per {user_email}, estrazione al volo...")

        # Fallback: estrazione al volo
        delegato = processo.delegato

        tutte_designazioni = list(
            processo.designazioni
            .filter(stato='CONFERMATA', is_attiva=True)
            .order_by('sezione__numero')
        )

        sezione_to_page = {
            des.sezione_id: idx
            for idx, des in enumerate(tutte_designazioni)
        }

        sezioni_rdl = sorted(set(des.sezione_id for des in designazioni))
        pagine_da_estrarre = sorted([
            sezione_to_page[sid]
            for sid in sezioni_rdl
            if sid in sezione_to_page
        ])

        if not pagine_da_estrarre:
            raise ValueError("Nessuna pagina trovata per le sezioni specificate")

        writer = PdfWriter()

        with _open_file(processo.documento_individuale) as f:
            reader = PdfReader(f)
            for page_idx in pagine_da_estrarre:
                if page_idx < len(reader.pages):
                    writer.add_page(reader.pages[page_idx])

        # Nomina delegato
        if delegato and delegato.documento_nomina:
            try:
                with _open_file(delegato.documento_nomina) as f:
                    nomina_reader = PdfReader(f)
                    for page in nomina_reader.pages:
                        writer.add_page(page)
            except Exception as e:
                logger.warning(f"Impossibile aggiungere nomina delegato: {e}")

        output_buffer = BytesIO()
        writer.write(output_buffer)
        return output_buffer.getvalue()
