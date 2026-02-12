"""
Django signals for automatic knowledge base ingestion.

When FAQ or Documento is created/updated:
1. Extract content (text from FAQ, or download+extract from PDF/URL)
2. Generate embedding via Vertex AI
3. Save to KnowledgeSource with embedding
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FAQ, Documento
from ai_assistant.models import KnowledgeSource
from ai_assistant.vertex_service import vertex_ai_service
from ai_assistant.extractors import PDFExtractor, WebExtractor
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FAQ)
def ingest_faq_to_knowledge_base(sender, instance, created, **kwargs):
    """
    Auto-ingest FAQ into knowledge base with embedding.
    """
    try:
        # Combina domanda + risposta
        content = f"DOMANDA: {instance.domanda}\n\nRISPOSTA: {instance.risposta}"

        # Genera embedding
        embedding = vertex_ai_service.generate_embedding(content)

        # Crea o aggiorna KnowledgeSource
        ks, created = KnowledgeSource.objects.update_or_create(
            title=f"FAQ: {instance.domanda[:100]}",
            source_type='FAQ',
            defaults={
                'content': content,
                'embedding': embedding,
                'is_active': instance.is_attivo,
            }
        )

        action = "Created" if created else "Updated"
        logger.info(f"{action} KnowledgeSource from FAQ {instance.id}")

    except Exception as e:
        logger.error(f"Failed to ingest FAQ {instance.id}: {e}", exc_info=True)


@receiver(post_save, sender=Documento)
def ingest_documento_to_knowledge_base(sender, instance, created, **kwargs):
    """
    Auto-ingest Documento into knowledge base with text extraction + embedding.
    """
    try:
        # Estrai contenuto basato su tipo
        content = ""

        # Se è un PDF caricato o URL PDF
        if instance.file and instance.file.name.endswith('.pdf'):
            content = PDFExtractor.extract_text(instance.file.path)
        elif instance.url_esterno:
            url = instance.url_esterno
            if url.endswith('.pdf'):
                # PDF esterno: download + extract
                content = PDFExtractor.extract_text(url)
            else:
                # Web page: scraping
                content = WebExtractor.extract_text(url)

        if not content:
            logger.warning(f"No content extracted from Documento {instance.id}")
            return

        # Prepend titolo + descrizione
        header = f"DOCUMENTO: {instance.titolo}\n"
        if instance.descrizione:
            header += f"DESCRIZIONE: {instance.descrizione}\n\n"
        full_content = header + content

        # Genera embedding
        embedding = vertex_ai_service.generate_embedding(full_content)

        # Determina source_type (mappa da tipo_file)
        source_type_map = {
            'PDF': 'MANUAL',
            'Word': 'MANUAL',
            'PowerPoint': 'SLIDE',
            'Excel': 'MANUAL',
            'LINK': 'PROCEDURE',
        }
        source_type = source_type_map.get(instance.tipo_file, 'MANUAL')

        # Determina source_url per PDF preview
        source_url = ''
        if instance.file:
            # File caricato: usa URL del media file
            source_url = instance.file.url
        elif instance.url_esterno:
            # URL esterno
            source_url = instance.url_esterno

        # Crea o aggiorna KnowledgeSource
        ks, created = KnowledgeSource.objects.update_or_create(
            title=f"Doc: {instance.titolo[:100]}",
            source_type=source_type,
            defaults={
                'content': full_content,
                'embedding': embedding,
                'source_url': source_url,
                'is_active': instance.is_attivo,
            }
        )

        action = "Created" if created else "Updated"
        logger.info(f"{action} KnowledgeSource from Documento {instance.id}")

    except Exception as e:
        logger.error(f"Failed to ingest Documento {instance.id}: {e}", exc_info=True)
