"""
Vertex AI service wrapper for Gemini LLM and text embeddings.
"""
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class VertexAIService:
    """Service for interacting with Vertex AI models (lazy initialization)."""

    def __init__(self):
        self._initialized = False
        self._llm = None
        self._embedding_model = None
        self._initialization_error = None

    def _ensure_initialized(self):
        """Lazy initialization of Vertex AI models."""
        if self._initialized:
            return

        if self._initialization_error:
            raise self._initialization_error

        try:
            # Check if credentials exist
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and not os.path.isfile(credentials_path):
                raise FileNotFoundError(
                    f"Google Cloud credentials not found at: {credentials_path}\n"
                    f"Run: ./scripts/setup-vertex-ai.sh"
                )

            # Import here to avoid loading at module level
            import vertexai
            from vertexai.generative_models import GenerativeModel
            from vertexai.language_models import TextEmbeddingModel

            # Initialize Vertex AI
            vertexai.init(
                project=settings.VERTEX_AI_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )

            # Initialize models
            self._llm = GenerativeModel(settings.VERTEX_AI_LLM_MODEL)
            self._embedding_model = TextEmbeddingModel.from_pretrained(
                settings.VERTEX_AI_EMBEDDING_MODEL
            )

            self._initialized = True
            logger.info(
                f"✓ Vertex AI initialized: {settings.VERTEX_AI_PROJECT} "
                f"({settings.VERTEX_AI_LOCATION})"
            )

        except Exception as e:
            self._initialization_error = e
            logger.error(f"✗ Vertex AI initialization failed: {e}", exc_info=True)
            raise

    def generate_response(self, prompt: str, context: str = None) -> str:
        """
        Generate response using Gemini 1.5 Flash.

        Args:
            prompt: User question
            context: Retrieved documents context (optional)

        Returns:
            str: Generated response
        """
        self._ensure_initialized()

        try:
            # Build full prompt with context
            system_prompt = settings.RAG_SYSTEM_PROMPT

            if context:
                full_prompt = f"""{system_prompt}

CONTESTO DA DOCUMENTI:
{context}

DOMANDA DELL'RDL:
{prompt}
"""
            else:
                # No context available - use general knowledge
                full_prompt = f"""Sei un assistente esperto per Rappresentanti di Lista (RDL) del Movimento 5 Stelle durante le elezioni italiane.

DOMANDA:
{prompt}

ISTRUZIONI:
- Rispondi in italiano chiaro e professionale
- Fornisci informazioni generali basate sulla tua conoscenza
- Se la domanda richiede informazioni specifiche non disponibili, suggerisci di consultare la documentazione ufficiale
- Mantieni un tono professionale ma accessibile
"""

            # Generate response
            response = self._llm.generate_content(full_prompt)
            return response.text

        except Exception as e:
            logger.error(f"Errore Gemini generation: {e}", exc_info=True)
            raise

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate text embedding using text-embedding-004.

        Args:
            text: Text to embed

        Returns:
            list[float]: 768-dimensional embedding vector
        """
        self._ensure_initialized()

        try:
            embeddings = self._embedding_model.get_embeddings([text])
            return embeddings[0].values  # 768-dim vector

        except Exception as e:
            logger.error(f"Errore embedding generation: {e}", exc_info=True)
            raise

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            list[list[float]]: List of 768-dimensional embedding vectors
        """
        self._ensure_initialized()

        try:
            embeddings = self._embedding_model.get_embeddings(texts)
            return [emb.values for emb in embeddings]

        except Exception as e:
            logger.error(f"Errore batch embedding: {e}", exc_info=True)
            raise


# Singleton instance (lazy initialization)
vertex_ai_service = VertexAIService()
