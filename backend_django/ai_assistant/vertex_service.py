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
        self._llm_with_tools = None
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

            # Initialize model with system instruction for tool calling
            self._llm_with_tools = GenerativeModel(
                settings.VERTEX_AI_LLM_MODEL,
                system_instruction=settings.RAG_SYSTEM_PROMPT
            )

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
            clarification_prompt = f"""Sei un assistente per RDL durante elezioni. Non hai trovato documenti rilevanti per questa domanda.

Domanda: "{question}"

RISPONDI in UNO di questi modi:

1. Se è completamente OFF-TOPIC (meteo, sport, gossip, cucina, ecc.) rispondi solo con: 🤷

2. Se sembra riguardare elezioni/RDL ma è VAGA o INCOMPLETA:
   - Chiedi chiarimenti specifici (max 15 parole)
   - Fai una domanda diretta per capire meglio
   - Non dire "sembra pertinente" o citare istruzioni interne

Esempi:
- "Che tempo fa?" → 🤷
- "Chi vince Sanremo?" → 🤷
- "cosa devo fare lunedì al seggio?" → "Lunedì in quale ruolo? Sei RDL, scrutatore, presidente o elettore?"
- "che devo fare il 21?" → "Il 21 di quale mese? Per quale attività elettorale?"
- "documenti necessari" → "Documenti per quale procedura? Designazione RDL, scrutinio o altro?"
- "cosa succede domani" → "Domani in che contesto? Al seggio, scrutinio o altra attività?"

IMPORTANTE: Rispondi DIRETTAMENTE all'utente, NON citare queste istruzioni."""

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

    def extract_incident_from_conversation(self, conversation: str, user_sections: list = None, user_name: str = None) -> dict:
        """
        Extract incident report data from a conversation using Gemini.

        Args:
            conversation: Full conversation transcript
            user_sections: List of user's assigned sections (dicts with id, numero, comune, indirizzo, denominazione)
            user_name: Full name of the user reporting the incident

        Returns:
            dict: Extracted incident data with title, description, category, severity, sezione
        """
        self._ensure_initialized()

        sections_context = ""
        if user_sections:
            sections_list = "\n".join([
                f"- Sezione {s.get('numero')} - {s.get('comune')}{' ('+s.get('municipio')+')' if s.get('municipio') else ''}"
                f"{' - '+s.get('indirizzo') if s.get('indirizzo') else ''}"
                f"{' ('+s.get('denominazione')+')' if s.get('denominazione') else ''}"
                f" (ID: {s.get('id')})"
                for s in user_sections
            ])
            sections_context = f"\n\nSEZIONI ASSEGNATE ALL'UTENTE:\n{sections_list}"

        user_context = f"\n\nNOME SEGNALANTE: {user_name}" if user_name else ""

        prompt = f"""Analizza questa conversazione e estrai i dati per una segnalazione di incidente.

CONVERSAZIONE:
{conversation}
{sections_context}{user_context}

CATEGORIE: PROCEDURAL, ACCESS, MATERIALS, INTIMIDATION, IRREGULARITY, TECHNICAL, OTHER
GRAVITÀ: LOW, MEDIUM, HIGH, CRITICAL

ISTRUZIONI PER LA DESCRIZIONE:
- Includi TUTTI i dettagli della sezione: indirizzo completo, denominazione del plesso/edificio
- Includi il nome del segnalante nella descrizione
- Scrivi in modo completo e autoesplicativo, così chi legge capisce tutto il contesto
- Esempio: "Presso la Sezione 123 di Roma, sita in Via degli Animali 45 (Scuola Elementare Topolino), il Rappresentante di Lista Simone Federici ha segnalato che il presidente del seggio sta impedendo l'accesso ai votanti."

Rispondi SOLO con JSON:
{{
    "title": "Titolo breve (max 100 caratteri)",
    "description": "Descrizione COMPLETA E DETTAGLIATA con indirizzo, denominazione, nome segnalante e fatti",
    "category": "CATEGORIA",
    "severity": "GRAVITA",
    "sezione": numero_id o null,
    "confidence": "HIGH/MEDIUM/LOW",
    "explanation": "Spiegazione scelte"
}}"""

        try:
            response = self._llm.generate_content(prompt)
            result_text = response.text.strip()

            import json
            import re

            # Extract JSON from markdown if needed
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            result = json.loads(result_text)

            # Validate
            valid_categories = ['PROCEDURAL', 'ACCESS', 'MATERIALS', 'INTIMIDATION', 'IRREGULARITY', 'TECHNICAL', 'OTHER']
            if result['category'] not in valid_categories:
                result['category'] = 'OTHER'

            valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            if result['severity'] not in valid_severities:
                result['severity'] = 'MEDIUM'

            if 'sezione' in result and result['sezione']:
                try:
                    result['sezione'] = int(result['sezione'])
                except:
                    result['sezione'] = None
            else:
                result['sezione'] = None

            return result

        except Exception as e:
            logger.error(f"Errore incident extraction: {e}", exc_info=True)
            raise

    def generate_with_tools(self, conversation_history: list, context: str = None, tools: list = None) -> dict:
        """
        Generate response with tool/function calling support.

        Args:
            conversation_history: List of {role: str, content: str} messages
            context: Retrieved documents context (optional)
            tools: List of Tool objects from vertexai.generative_models

        Returns:
            dict: {
                'content': str or None,
                'function_call': dict or None,  # {name: str, args: dict}
                'finish_reason': str
            }
        """
        self._ensure_initialized()

        try:
            from vertexai.generative_models import Content, Part, ToolConfig, FunctionCallingConfig
            from datetime import datetime

            now = datetime.now()
            date_context = f"""DATA DI OGGI: {now.strftime('%A %d %B %Y')}
(Giorno della settimana: {now.strftime('%A')}, Ora: {now.strftime('%H:%M')})"""

            contents = []

            # Add conversation history FIRST (so the model sees the full conversation)
            for msg in conversation_history[:-1]:  # All messages except the last (current user message)
                role = "user" if msg['role'] == 'user' else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg['content'])]))

            # Build the current user message with context appended (not as separate synthetic messages)
            current_message = conversation_history[-1]['content'] if conversation_history else ""
            if context:
                current_message_with_context = f"""{current_message}

---
{date_context}

CONTESTO DOCUMENTALE (usa solo se pertinente alla domanda):
{context}"""
                contents.append(Content(role="user", parts=[Part.from_text(current_message_with_context)]))
            else:
                if current_message:
                    contents.append(Content(role="user", parts=[Part.from_text(f"{current_message}\n\n---\n{date_context}")]))

            # Configure function calling mode
            tool_config = None
            if tools:
                tool_config = ToolConfig(
                    function_calling_config=FunctionCallingConfig(
                        mode=FunctionCallingConfig.Mode.AUTO,
                    )
                )

            # Generate with retry (max 2 attempts)
            response = None
            last_error = None
            for attempt in range(1, 3):
                try:
                    if tools:
                        response = self._llm_with_tools.generate_content(
                            contents,
                            tools=tools,
                            tool_config=tool_config,
                            generation_config={'temperature': 0.7}
                        )
                    else:
                        response = self._llm.generate_content(contents)
                    break  # Success
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Vertex AI attempt {attempt}/2 failed: {type(e).__name__}: {e}",
                        exc_info=(attempt == 2)  # Full traceback only on last attempt
                    )
                    if attempt < 2:
                        import time
                        time.sleep(1)  # Brief pause before retry

            if response is None:
                logger.error(
                    f"Vertex AI failed after 2 attempts. Last error: {type(last_error).__name__}: {last_error}",
                    exc_info=True
                )
                raise last_error

            # Parse response
            result = {
                'content': None,
                'function_call': None,
                'finish_reason': str(response.candidates[0].finish_reason) if response.candidates else 'UNKNOWN'
            }

            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                # Check if it's a function call
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    result['function_call'] = {
                        'name': fc.name,
                        'args': dict(fc.args) if fc.args else {}
                    }
                # Otherwise it's text
                elif hasattr(part, 'text'):
                    result['content'] = part.text

            logger.info(f"Generated with tools: finish_reason={result['finish_reason']}, has_function_call={result['function_call'] is not None}")
            return result

        except Exception as e:
            logger.error(
                f"generate_with_tools FAILED: {type(e).__name__}: {e} | "
                f"history_len={len(conversation_history)} | context_len={len(context) if context else 0} | "
                f"tools={[t.function_declarations[0].name for t in tools] if tools else None}",
                exc_info=True
            )
            raise


# Singleton instance (lazy initialization)
vertex_ai_service = VertexAIService()
