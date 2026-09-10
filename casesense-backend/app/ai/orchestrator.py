from typing import List, Optional
from app.core.config import settings
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.stub import StubAIProvider
from app.ai.providers.openai_compat import OpenAICompatProvider

TRANSLATE_PROMPT = """Translate the following Indian legal text into Hindi.
Preserve legal terminology; keep citations, section numbers and case names
transliterated as in the original. Output ONLY the Hindi translation.

Text:
{text}
"""


class AIOrchestrator:
    """Orchestrator for managing provider routing, model tiers, and fallbacks."""

    def __init__(self):
        if (
            settings.APP_ENV in ("dev", "development", "test")
            or not settings.AI_API_KEY
            or settings.AI_API_KEY.startswith("test_")
        ):
            self.provider: BaseAIProvider = StubAIProvider()
        else:
            self.provider = OpenAICompatProvider()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = settings.AI_MODEL_EMBED or "text-embedding-3-small"
        return await self.provider.get_embeddings(texts=texts, model=model)

    async def translate_to_hindi(self, text: str) -> Optional[str]:
        """v2.2 — Translate to Hindi. Returns None when the provider can't."""
        try:
            result = await self.provider.generate_text(
                TRANSLATE_PROMPT.format(text=text), max_tokens=1024
            )
        except Exception:
            return None
        return (result or None) if isinstance(result, str) else None


_orchestrator: AIOrchestrator | None = None


def get_ai_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator
