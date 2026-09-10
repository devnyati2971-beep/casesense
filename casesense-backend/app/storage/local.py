"""
Local filesystem storage adapter — used in development when no object storage
credentials are configured. Mirrors the S3 object-key layout on disk.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.storage.base import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, base_dir: str = ".casesense-storage") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Object keys are server-generated (matters/{uuid}/documents/{uuid}...);
        # guard against any path traversal attempt anyway.
        safe_key = key.replace("..", "_").lstrip("/")
        path = self.base_dir / safe_key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._path(key).write_bytes(data)

    async def get_object(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def delete_object(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass

    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> str:
        # Local dev: serve directly through the API download endpoint instead.
        # The token is opaque and only meaningful to this adapter.
        token = uuid.uuid4().hex
        return f"/api/v1/storage/local/{key}?token={token}&expires={expires_in}"