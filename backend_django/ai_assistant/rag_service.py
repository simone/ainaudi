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
    def answer_question(user_question: str, context_type: str = None, session=None) -> dict:
        """
        Answer user question using RAG pipeline.

        Args:
            user_question: User's question
            context_type: Optional context (e.g., "SCRUTINY", "INCIDENT")
            session: ChatSession instance (to check conversation history)

        Returns:
            dict: {
                'answer': str,
                'sources': list[dict],  # Sources cited
                'retrieved_docs': int,  # Number of docs retrieved
            }
        """
        try:
            # 0. Pre-filter: check if question is trivial
            # ONLY for first message in conversation (not in middle of chat)
            is_first_message = True
            if session:
                # Count messages BEFORE current one (exclude the just-saved user message)
                previous_messages = session.messages.count() - 1
                is_first_message = previous_messages == 0

            if is_first_message and vertex_ai_service.is_trivial_question(user_question):
                logger.info(f"Trivial question detected (first message): {user_question[:50]}")
                return {
                    'answer': "🤷",
                    'sources': [],
                    'retrieved_docs': 0,
                }

            # 1. Pre-filter: check if question is too short/vague
            if len(user_question.strip()) < 3:
                logger.info(f"Question too short: '{user_question}'")
                return {
                    'answer': "Puoi essere più specifico? La domanda è troppo breve.",
                    'sources': [],
                    'retrieved_docs': 0,
                }

            # 2. Generate query embedding
            query_embedding = vertex_ai_service.generate_embedding(user_question)

            # 3. Similarity search in pgvector
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

            # 4. Check if we have relevant context
            if len(similar_docs) == 0:
                # No relevant documents found - question likely off-topic
                logger.info(f"No relevant context found for: {user_question[:50]}")

                # Use minimal model call to clarify if question is pertinent
                clarification = vertex_ai_service.clarify_off_topic_question(user_question)

                return {
                    'answer': clarification,
                    'sources': [],
                    'retrieved_docs': 0,
                }

            # 5. Check if best match is too weak (even if above threshold)
            # If best document has similarity < 0.6, it's likely too vague/off-topic
            best_similarity = 1 - similar_docs[0].distance
            QUALITY_THRESHOLD = 0.6  # Higher than RAG_SIMILARITY_THRESHOLD for quality check

            if best_similarity < QUALITY_THRESHOLD:
                logger.info(
                    f"Best match too weak (similarity={best_similarity:.3f}): {user_question[:50]}"
                )
                # Use clarification for weak matches
                clarification = vertex_ai_service.clarify_off_topic_question(user_question)

                return {
                    'answer': clarification,
                    'sources': [],
                    'retrieved_docs': 0,
                }

            # 6. Build context from retrieved documents
            context_parts = []
            sources = []

            for doc in similar_docs:
                context_parts.append(f"[{doc.source_type}] {doc.title}\n{doc.content[:2000]}")  # Max 2k chars per doc
                sources.append({
                    'id': doc.id,
                    'title': doc.title,
                    'type': doc.source_type,
                    'similarity': 1 - doc.distance,  # Convert distance back to similarity
                    'url': doc.source_url if doc.source_url else None,
                })

            context = "\n\n---\n\n".join(context_parts)

            # 7. Generate response with Gemini + context
            answer = vertex_ai_service.generate_response(
                prompt=user_question,
                context=context
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
