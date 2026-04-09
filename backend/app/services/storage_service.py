"""S3-compatible object storage client (works with MinIO in dev)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    """Thin async wrapper around boto3's S3 client.

    boto3 is synchronous, so all I/O calls are wrapped in
    ``asyncio.to_thread()`` to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",  # MinIO default
        )
        self._bucket = settings.s3_bucket

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/png",
    ) -> str:
        """Upload *data* to S3 under *key* and return the object URL."""

        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_put)

        url = f"{settings.s3_endpoint}/{self._bucket}/{key}"
        logger.info("Uploaded %s (%d bytes) -> %s", key, len(data), url)
        return url

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    async def download(self, key: str) -> bytes:
        """Download an object by *key* and return its bytes."""

        def _get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        data = await asyncio.to_thread(_get)
        logger.info("Downloaded %s (%d bytes)", key, len(data))
        return data

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, key: str) -> None:
        """Delete an object by *key*."""

        def _del() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        await asyncio.to_thread(_del)
        logger.info("Deleted %s", key)

    # ------------------------------------------------------------------
    # Presigned URL
    # ------------------------------------------------------------------

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL for *key*.

        Parameters
        ----------
        key:
            Object key in the bucket.
        expires_in:
            URL expiration time in seconds (default 1 hour).

        Returns
        -------
        str
            A presigned URL string.
        """
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    # ------------------------------------------------------------------
    # Bucket management
    # ------------------------------------------------------------------

    async def ensure_bucket(self, bucket_name: str | None = None) -> None:
        """Create the bucket if it does not already exist.

        Useful during local dev with MinIO.
        """
        target = bucket_name or self._bucket

        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=target)
                logger.info("Bucket %s already exists", target)
            except ClientError:
                self._client.create_bucket(Bucket=target)
                logger.info("Created bucket %s", target)

        await asyncio.to_thread(_ensure)
