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

    def is_trivial_question(self, question: str) -> bool:
        """
        Check if question is trivial/silly using minimal model call.

        Returns True if question is: greeting, joke, nonsense, off-topic
        """
        # Quick pattern matching for obvious cases (no API call)
        question_lower = question.lower().strip()

        # Obvious greetings
        greetings = ['ciao', 'salve', 'buongiorno', 'buonasera', 'hey', 'hello', 'hi']
        if question_lower in greetings or len(question_lower) < 5:
            return True

        # Test patterns
        test_patterns = ['test', 'prova', 'asdf', '???', '!!!']
        if any(pattern in question_lower for pattern in test_patterns) and len(question_lower) < 15:
            return True

        self._ensure_initialized()

        try:
            classification_prompt = f"""Classifica come SERIA o BANALE.

SERIA = elezioni, scrutinio, procedure RDL, normative
BANALE = saluti, battute, nonsense, off-topic

"{question}"

Rispondi: SERIA o BANALE"""

            response = self._llm.generate_content(classification_prompt)
            result = response.text.strip().upper()

            return 'BANALE' in result

        except Exception as e:
            logger.warning(f"Classification failed, assuming serious: {e}")
            return False  # In caso di errore, tratta come seria

    def clarify_off_topic_question(self, question: str) -> str:
        """
        Handle questions without relevant RAG context (likely off-topic).

        Returns a brief clarification or shrug emoji.
        """
        self._ensure_initialized()

        try:
            clarification_prompt = f"""La domanda non ha documenti rilevanti nella KB RDL (elezioni/scrutinio).

Domanda: "{question}"

Se è CHIARAMENTE off-topic (meteo, sport, gossip, cucina) → 🤷

Se menziona date/numeri/procedure ma è vaga → chiedi chiarimento (max 10 parole)

Se sembra pertinente RDL ma incompleta → chiedi dettagli (max 10 parole)

Esempi:
- "Che tempo fa?" → 🤷
- "Chi vince Sanremo?" → 🤷
- "che devo fare il 21?" → "Il 21 di quale mese? Per quale attività (voto/scrutinio)?"
- "documenti necessari" → "Documenti per quale procedura? Designazione, scrutinio, contestazioni?"
- "cosa succede domani" → "Domani in quale contesto? Seggio, scrutinio, altro?"
"""

            response = self._llm.generate_content(clarification_prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Clarification failed: {e}", exc_info=True)
            return "Non ho capito la domanda. Puoi essere più specifico?"

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
            # Get current date info for temporal context
            from datetime import datetime
            import locale
            try:
                locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
            except:
                pass  # Fallback to default if Italian locale not available

            now = datetime.now()
            date_context = f"""DATA DI OGGI: {now.strftime('%A %d %B %Y')}
(Giorno della settimana: {now.strftime('%A')}, Ora: {now.strftime('%H:%M')})"""

            # Build full prompt with context
            system_prompt = settings.RAG_SYSTEM_PROMPT

            if context:
                full_prompt = f"""{system_prompt}

{date_context}

CONTESTO DA DOCUMENTI:
{context}

DOMANDA DELL'RDL:
{prompt}
"""
            else:
                # No context available - use general knowledge
                full_prompt = f"""Sei un assistente per RDL del M5S durante elezioni.

{date_context}

DOMANDA:
{prompt}

ISTRUZIONI:
- Rispondi breve e chiaro
- Usa conoscenza generale RDL
- Tono professionale diretto
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
