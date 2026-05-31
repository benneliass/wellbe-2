from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial

import boto3


class S3BlobStore:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        retention_days: int = 365,
        client: object | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._bucket = bucket
        self._retention_days = retention_days
        self._clock = clock or (lambda: datetime.now(UTC))
        self._client = (
            client
            if client is not None
            else boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        )

    async def upload_blob(
        self, key: str, data: bytes, content_hash: str
    ) -> str:
        resp = await asyncio.to_thread(
            partial(
                self._client.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=data,
                Metadata={"content-sha256": content_hash},
                ObjectLockMode="GOVERNANCE",
                ObjectLockRetainUntilDate=self._clock()
                + timedelta(days=self._retention_days),
            )
        )
        return resp.get("VersionId", "")

    async def get_blob(self, key: str) -> bytes:
        resp = await asyncio.to_thread(
            partial(
                self._client.get_object,
                Bucket=self._bucket,
                Key=key,
            )
        )
        body = resp["Body"]
        return await asyncio.to_thread(body.read)
