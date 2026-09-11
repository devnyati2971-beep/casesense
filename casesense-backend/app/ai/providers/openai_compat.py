import math

import httpx
from typing import List, Optional
from app.core.config import settings
from app.core.exceptions import AIError
from app.ai.providers.base import BaseAIProvider


class OpenAICompatProvider(BaseAIProvider):
    """OpenAI-compatible embedding and text generation provider."""

    def __init__(self):
        # Gemini exposes an OpenAI-compatible endpoint. Use the documented
        # endpoint when the deployment selected Gemini but did not redundantly
        # set an override URL.
        self.base_url = settings.AI_API_BASE_URL.rstrip("/") or (
            "https://generativelanguage.googleapis.com/v1beta/openai"
            if settings.AI_PROVIDER == "gemini"
            else ""
        )
        self.api_key = settings.AI_API_KEY

    async def get_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        if not self.api_key:
            raise AIError("AI_API_KEY is not configured")
        if not self.base_url:
            raise AIError("AI_API_BASE_URL is not configured")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": model}
        # All vector columns are declared as Vector(1536). Gemini supports
        # controllable dimensions, so request a compatible, recommended size
        # rather than letting indexing fail later during the database write.
        if settings.AI_PROVIDER == "gemini":
            payload["dimensions"] = 1536

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise AIError(
                    f"AI provider embedding error: {response.status_code} - {response.text}"
                )
            data = response.json()
            # Sort by index to ensure positional order is preserved
            # Gemini's compatible response omits ``index`` for a single input;
            # preserve response order in that case.
            items = sorted(
                data["data"], key=lambda item: item.get("index", data["data"].index(item))
            )
            embeddings = [item["embedding"] for item in items]
            if any(len(embedding) != 1536 for embedding in embeddings):
                raise AIError("AI provider returned embeddings with an unsupported dimension")

            # Gemini embedding-001 requires normalization when requesting a
            # non-default dimensionality; pgvector cosine search expects the
            # normalized representation for consistent relevance ranking.
            if settings.AI_PROVIDER == "gemini" and model == "gemini-embedding-001":
                normalized: List[List[float]] = []
                for embedding in embeddings:
                    magnitude = math.sqrt(sum(value * value for value in embedding))
                    normalized.append(
                        [value / magnitude for value in embedding] if magnitude else embedding
                    )
                return normalized
            return embeddings

    async def generate_text(self, prompt: str, max_tokens: int = 1024, is_json: bool = False) -> Optional[str]:
        if not self.api_key:
            raise AIError("AI_API_KEY is not configured")
        if not self.base_url:
            raise AIError("AI_API_BASE_URL is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        model = settings.AI_MODEL_STRONG

        # Gemini 3.x "thinking" models consume thinking tokens from max_tokens.
        # A low limit produces truncated output. Use at least 4096.
        effective_max_tokens = max(max_tokens, 4096)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": effective_max_tokens,
            "temperature": 0.1,
        }

        if is_json:
            payload["response_format"] = {"type": "json_object"}

        # Retry up to 3 times on transient errors (503, 429)
        import asyncio
        max_retries = 3
        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code in (503, 429) and attempt < max_retries - 1:
                        wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                        await asyncio.sleep(wait)
                        continue
                    if response.status_code != 200:
                        raise AIError(
                            f"AI provider generation error: {response.status_code} - {response.text}"
                        )
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    # Guard against truncated responses (finish_reason != "stop")
                    finish_reason = data["choices"][0].get("finish_reason", "stop")
                    if finish_reason == "length":
                        raise AIError("AI response was truncated (max_tokens too low)")
                    return content
                except AIError:
                    raise
                except Exception as exc:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** (attempt + 1))
                        continue
                    raise AIError(f"Failed to generate text: {exc}") from exc
        return None

