from __future__ import annotations

from datetime import UTC, datetime

from wellbe_c2_vault.s3 import S3BlobStore


class _FakeS3Client:
    def __init__(self) -> None:
        self.put_object_kwargs: dict | None = None

    def put_object(self, **kwargs):
        self.put_object_kwargs = kwargs
        return {"VersionId": "version-1"}


async def test_upload_blob_sets_governance_object_lock_headers():
    client = _FakeS3Client()
    store = S3BlobStore(
        endpoint="http://minio:9000",
        access_key="minio",
        secret_key="minio",
        bucket="wellbe-raw-context",
        client=client,
        retention_days=30,
        clock=lambda: datetime(2026, 6, 1, tzinfo=UTC),
    )

    version_id = await store.upload_blob(
        "raw/patient/hash/event/event-id/blob",
        b"payload",
        "content-hash",
    )

    assert version_id == "version-1"
    assert client.put_object_kwargs is not None
    assert client.put_object_kwargs["ObjectLockMode"] == "GOVERNANCE"
    assert client.put_object_kwargs["ObjectLockRetainUntilDate"] == datetime(
        2026, 7, 1, tzinfo=UTC
    )
    assert client.put_object_kwargs["Metadata"] == {"content-sha256": "content-hash"}
