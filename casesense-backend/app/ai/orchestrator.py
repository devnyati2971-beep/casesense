from typing import List, Optional
from app.core.config import settings
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.stub import StubAIProvider
from app.ai.providers.openai_compat import OpenAICompatProvider
from app.core.exceptions import AIError
from app.core.logging import get_logger

logger = get_logger(__name__)

TRANSLATE_PROMPT = """Translate the following Indian legal text into Hindi.
Preserve legal terminology; keep citations, section numbers and case names
transliterated as in the original. Output ONLY the Hindi translation.

Text:
{text}
"""


class AIOrchestrator:
    """Orchestrator for managing provider routing, model tiers, and fallbacks."""

    def __init__(self):
        # Development must not silently disable a configured provider. That
        # made every local search use the stub even when Gemini credentials
        # were supplied, leaving the research worker without structured output.
        if (
            settings.AI_PROVIDER == "stub"
            or not settings.AI_API_KEY
            or settings.AI_API_KEY.startswith("test_")
        ):
            self.provider: BaseAIProvider = StubAIProvider()
        else:
            self.provider = OpenAICompatProvider()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # Older deployments may still carry the retired text-embedding-004
        # environment value. Use Gemini's supported text embedding model until
        # that environment variable is updated.
        model = settings.AI_MODEL_EMBED or "gemini-embedding-001"
        if settings.AI_PROVIDER == "gemini" and model == "text-embedding-004":
            model = "gemini-embedding-001"
        return await self.provider.get_embeddings(texts=texts, model=model)

    async def translate_to_hindi(self, text: str) -> Optional[str]:
        """v2.2 — Translate to Hindi. Returns None when the provider can't."""
        try:
            result = await self.provider.generate_text(
                TRANSLATE_PROMPT.format(text=text), max_tokens=1024
            )
        except AIError:
            # Preserve provider status details so the HTTP route can distinguish
            # a quota limit from a genuine service outage.
            raise
        except Exception as exc:
            logger.warning("Hindi translation failed", error=str(exc))
            return None
        return (result or None) if isinstance(result, str) else None

    async def generate_json(self, prompt: str, max_tokens: int = 2048) -> Optional[str]:
        try:
            result = await self.provider.generate_text(prompt, max_tokens=max_tokens, is_json=True)
            return (result or None) if isinstance(result, str) else None
        except Exception as e:
            logger.warning(f"JSON generation failed: {e}")
            return None


_orchestrator: AIOrchestrator | None = None


def get_ai_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator
