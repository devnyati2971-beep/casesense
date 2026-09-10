"""
OCI Object Storage adapter (S3-compatible) — Blueprint §19.

Uses aioboto3 for the async path. When credentials are not configured the
factory falls back to the local adapter, so this file is only exercised in
environments with real storage configuration.
"""

from __future__ import annotations

import aioboto3
from botocore.config import Config as BotoConfig

from app.storage.base import StorageAdapter


class OCIObjectStorageAdapter(StorageAdapter):
    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        region: str,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket = bucket
        self.region = region

    def _session(self) -> aioboto3.Session:
        return aioboto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

    def _client_kwargs(self) -> dict:
        return {
            "endpoint_url": self.endpoint_url,
            "config": BotoConfig(s3={"addressing_style": "path"}),
        }

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        async with self._session().client("s3", **self._client_kwargs()) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

    async def get_object(self, key: str) -> bytes:
        async with self._session().client("s3", **self._client_kwargs()) as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            body = await response["Body"].read()
            return body

    async def delete_object(self, key: str) -> None:
        async with self._session().client("s3", **self._client_kwargs()) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> str:
        async with self._session().client("s3", **self._client_kwargs()) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )