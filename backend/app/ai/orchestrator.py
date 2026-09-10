from typing import List
from app.core.config import settings
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.stub import StubAIProvider
from app.ai.providers.openai_compat import OpenAICompatProvider


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


_orchestrator: AIOrchestrator | None = None


def get_ai_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator