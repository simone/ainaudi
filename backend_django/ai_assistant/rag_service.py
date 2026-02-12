"""
RAG (Retrieval-Augmented Generation) service orchestration.
"""
from django.conf import settings
from .models import KnowledgeSource
from .vertex_service import vertex_ai_service
from pgvector.django import CosineDistance
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """RAG pipeline: retrieve → contextualize → generate."""

    @staticmethod
    def answer_question(user_question: str, context_type: str = None) -> dict:
        """
        Answer user question using RAG pipeline.

        Args:
            user_question: User's question
            context_type: Optional context (e.g., "SCRUTINY", "INCIDENT")

        Returns:
            dict: {
                'answer': str,
                'sources': list[dict],  # Sources cited
                'retrieved_docs': int,  # Number of docs retrieved
            }
        """
        try:
            # 1. Generate query embedding
            query_embedding = vertex_ai_service.generate_embedding(user_question)

            # 2. Similarity search in pgvector
            similar_docs = (
                KnowledgeSource.objects
                .filter(is_active=True)
                .annotate(
                    distance=CosineDistance('embedding', query_embedding)
                )
                .filter(distance__lte=(1 - settings.RAG_SIMILARITY_THRESHOLD))  # cosine distance = 1 - similarity
                .order_by('distance')
                [:settings.RAG_TOP_K]
            )

            # 3. Build context from retrieved documents
            context_parts = []
            sources = []

            for doc in similar_docs:
                context_parts.append(f"[{doc.source_type}] {doc.title}\n{doc.content[:2000]}")  # Max 2k chars per doc
                sources.append({
                    'id': doc.id,
                    'title': doc.title,
                    'type': doc.source_type,
                    'similarity': 1 - doc.distance,  # Convert distance back to similarity
                })

            context = "\n\n---\n\n".join(context_parts)

            # 4. Generate response with Gemini
            answer = vertex_ai_service.generate_response(
                prompt=user_question,
                context=context if context else None
            )

            logger.info(
                f"RAG answer generated: {len(similar_docs)} docs retrieved, "
                f"context={len(context)} chars"
            )

            return {
                'answer': answer,
                'sources': sources,
                'retrieved_docs': len(similar_docs),
            }

        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}", exc_info=True)
            return {
                'answer': "Mi dispiace, si è verificato un errore. Riprova più tardi.",
                'sources': [],
                'retrieved_docs': 0,
            }


# Singleton
rag_service = RAGService()
