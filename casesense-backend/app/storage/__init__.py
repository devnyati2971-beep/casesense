"""
Storage adapters — Blueprint §19 (Object Storage).

The application never touches storage directly; it uses the adapter returned by
`get_storage_adapter()`. In development (no credentials configured) a local
filesystem adapter is used so the full pipeline runs without OCI/minio.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageAdapter
from app.storage.local import LocalStorageAdapter
from app.storage.oci_object_storage import OCIObjectStorageAdapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    if settings.storage_enabled:
        return OCIObjectStorageAdapter(
            endpoint_url=settings.STORAGE_ENDPOINT_URL,
            access_key_id=settings.STORAGE_ACCESS_KEY_ID,
            secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY,
            bucket=settings.STORAGE_BUCKET_NAME,
            region=settings.STORAGE_REGION,
        )
    return LocalStorageAdapter(base_dir=".casesense-storage")


__all__ = ["StorageAdapter", "LocalStorageAdapter", "OCIObjectStorageAdapter", "get_storage_adapter"]