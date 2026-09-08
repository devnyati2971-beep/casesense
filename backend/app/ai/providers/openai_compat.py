import http
from typing import List
from app.core.config import settings
from app.core.exceptions import InternalServerException
from app.ai.providers.base import BaseAIProvider


class OpenAICompatProvider(BaseAIProvider):
    """OpenAI-compatible embedding provider."""

    def __init__(self):
        self.base_url = settings.AI_PROVIDER_BASE_URL.rstrip("/")
        self.api_key = settings.AI_API_KEY

    async def get_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        if not self.api_key:
            raise InternalServerException("AI_API_KEY is not configured")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": model}

        async with http.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise InternalServerException(
                    f"AI provider embedding error: {response.status_code} - {response.text}"
                )
            data = response.json()
            # Sort by index to ensure positional order is preserved
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]