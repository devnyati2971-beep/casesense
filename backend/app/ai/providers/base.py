from abc import ABC, abstractmethod
from typing import List


class BaseAIProvider(ABC):
    """Abstract interface for AI model execution."""

    @abstractmethod
    async def get_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate 1536-dimensional vector embeddings for a batch of strings."""
        pass