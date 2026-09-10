import hashlib
import math
import random
from typing import List
from app.ai.providers.base import BaseAIProvider


class StubAIProvider(BaseAIProvider):
    """Deterministic 1536-dim normalized vector generator for zero-cost dev and CI testing."""

    async def get_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            # Deterministic pseudo-random seed from string hash
            hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(hash_bytes[:8], byteorder="big")
            rng = random.Random(seed)

            # Generate 1536 random values
            raw = [rng.gauss(0.0, 1.0) for _ in range(1536)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            unit_vector = [round(x / norm, 6) for x in raw]
            vectors.append(unit_vector)
        return vectors