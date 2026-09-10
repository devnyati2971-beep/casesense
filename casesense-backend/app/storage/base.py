"""
Storage adapter interface — Blueprint §19 (Object Storage).

All reads go through the API (authz) and are served via short-lived pre-signed
URLs. Objects are never public.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """S3-compatible object storage abstraction."""

    @abstractmethod
    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        """Store a binary object at the given key."""

    @abstractmethod
    async def get_object(self, key: str) -> bytes:
        """Fetch a binary object by key."""

    @abstractmethod
    async def delete_object(self, key: str) -> None:
        """Delete an object by key (no-op when the key does not exist)."""

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> str:
        """Return a GET-only pre-signed URL valid for `expires_in` seconds."""