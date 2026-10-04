"""Object storage. Production uses an S3-compatible service (Cloudflare R2); tests use memory.

Browsers upload directly to storage with short-lived presigned PUT URLs, so file bytes never
pass through the API or the frontend proxy. Callers build keys only from server-generated IDs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, current_app

from app.common.errors import AppError

_MISSING_CODES = frozenset({"404", "NoSuchKey", "NotFound"})


class StorageUnavailableError(AppError):
    status_code = 503
    code = "STORAGE_UNAVAILABLE"
    message = "File storage is temporarily unavailable. Please try again."


class ObjectStorage(Protocol):
    def presigned_put(self, key: str, content_type: str, expires_in: int) -> str: ...
    def presigned_get(self, key: str, expires_in: int) -> str: ...
    def size(self, key: str) -> int | None: ...
    def read(self, key: str, max_bytes: int) -> bytes: ...
    def write(self, key: str, data: bytes, content_type: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def list_objects(self, prefix: str, max_keys: int) -> list[tuple[str, datetime]]: ...


class S3Storage:
    def __init__(
        self,
        *,
        endpoint_url: str | None,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        region: str,
    ) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                connect_timeout=3,
                read_timeout=10,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )

    def presigned_put(self, key: str, content_type: str, expires_in: int) -> str:
        # ContentType is signed: the upload must send exactly this Content-Type header.
        params = {"Bucket": self._bucket, "Key": key, "ContentType": content_type}
        return str(
            self._client.generate_presigned_url("put_object", Params=params, ExpiresIn=expires_in)
        )

    def presigned_get(self, key: str, expires_in: int) -> str:
        params = {"Bucket": self._bucket, "Key": key, "ResponseContentDisposition": "inline"}
        return str(
            self._client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)
        )

    def size(self, key: str) -> int | None:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in _MISSING_CODES:
                return None
            raise StorageUnavailableError() from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError() from exc
        return int(head["ContentLength"])

    def read(self, key: str, max_bytes: int) -> bytes:
        """Reads at most max_bytes + 1 bytes, so oversize files are detectable but bounded."""
        try:
            obj = self._client.get_object(
                Bucket=self._bucket, Key=key, Range=f"bytes=0-{max_bytes}"
            )
            return cast(bytes, obj["Body"].read(max_bytes + 1))
        except (BotoCoreError, ClientError) as exc:
            raise StorageUnavailableError() from exc

    def write(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageUnavailableError() from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageUnavailableError() from exc

    def list_objects(self, prefix: str, max_keys: int) -> list[tuple[str, datetime]]:
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            found: list[tuple[str, datetime]] = []
            pages = paginator.paginate(
                Bucket=self._bucket, Prefix=prefix, PaginationConfig={"MaxItems": max_keys}
            )
            for page in pages:
                found += [(item["Key"], item["LastModified"]) for item in page.get("Contents", [])]
            return found
        except (BotoCoreError, ClientError) as exc:
            raise StorageUnavailableError() from exc


class MemoryStorage:
    """Tests only. Not shared between processes, so useless for a real server."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.modified: dict[str, datetime] = {}

    def presigned_put(self, key: str, content_type: str, expires_in: int) -> str:
        return f"memory://upload/{key}"

    def presigned_get(self, key: str, expires_in: int) -> str:
        return f"memory://download/{key}"

    def size(self, key: str) -> int | None:
        stored = self.objects.get(key)
        return len(stored[0]) if stored is not None else None

    def read(self, key: str, max_bytes: int) -> bytes:
        return self.objects[key][0][: max_bytes + 1]

    def write(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)
        self.modified[key] = datetime.now(UTC)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.modified.pop(key, None)

    def list_objects(self, prefix: str, max_keys: int) -> list[tuple[str, datetime]]:
        keys = sorted(key for key in self.objects if key.startswith(prefix))[:max_keys]
        return [(key, self.modified[key]) for key in keys]


def init_storage(app: Flask) -> None:
    if app.config["STORAGE_BACKEND"] == "memory":
        app.extensions["storage"] = MemoryStorage()
        return
    app.extensions["storage"] = S3Storage(
        endpoint_url=app.config["S3_ENDPOINT_URL"],
        access_key_id=app.config["S3_ACCESS_KEY_ID"],
        secret_access_key=app.config["S3_SECRET_ACCESS_KEY"],
        bucket=app.config["S3_BUCKET"],
        region=app.config["S3_REGION"],
    )


def get_storage() -> ObjectStorage:
    return cast(ObjectStorage, current_app.extensions["storage"])
