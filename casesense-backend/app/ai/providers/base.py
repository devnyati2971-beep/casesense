from abc import ABC, abstractmethod
from typing import List, Optional


class BaseAIProvider(ABC):
    """Abstract interface for AI model execution."""

    @abstractmethod
    async def get_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate 1536-dimensional vector embeddings for a batch of strings."""
        pass

    async def generate_text(self, prompt: str, max_tokens: int = 1024) -> Optional[str]:
        """Optional text generation. Providers without chat support return None."""
        return None