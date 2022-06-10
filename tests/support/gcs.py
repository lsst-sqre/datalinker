"""Mock Google Cloud Storage API for testing."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional
from unittest.mock import Mock

from google.cloud import storage


class MockBlob(Mock):
    def __init__(self, name: str) -> None:
        super().__init__(spec=storage.blob.Blob)
        self.name = name

    def generate_signed_url(
        self,
        *,
        version: str,
        expiration: timedelta,
        method: str,
        response_type: Optional[str] = None,
        credentials: Optional[Any] = None,
    ) -> str:
        assert version == "v4"
        assert expiration == timedelta(hours=1)
        assert method == "GET"
        return f"https://example.com/{self.name}"


class MockBucket(Mock):
    def __init__(self) -> None:
        super().__init__(spec=storage.bucket.Bucket)

    def blob(self, blob_name: str) -> Mock:
        return MockBlob(blob_name)


class MockStorageClient(Mock):
    def __init__(self) -> None:
        super().__init__(spec=storage.Client)

    def bucket(self, bucket_name: str) -> Mock:
        return MockBucket()
