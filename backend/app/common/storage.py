"""Object storage. Production uses an S3-compatible service (Cloudflare R2); tests use memory.

Browsers upload directly to storage with short-lived presigned PUT URLs, so file bytes never
pass through the API or the frontend proxy. Callers build keys only from server-generated IDs.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import quote, urlencode

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


# Above the 10 MB photo limit on purpose: oversize files still reach the API's own
# "too large" rejection at completion, exactly as they would with S3.
LOCAL_UPLOAD_LIMIT_BYTES = 12 * 1024 * 1024
_SIDECAR = ".content-type"


class LocalStorage:
    """Development and end-to-end tests only (production refuses it).

    Files live on local disk, shared by every process on the machine (unlike MemoryStorage).
    Upload and download URLs mirror S3 presigned URLs: they expire, and the method, key,
    content type and expiry are covered by an HMAC signature verified in constant time. URLs
    point at the frontend origin, so browsers reach them through the same proxy as the API.
    """

    def __init__(self, root: str, secret: str, public_origin: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._secret = secret.encode()
        self._origin = public_origin.rstrip("/")

    def path_for(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if path == self._root or not path.is_relative_to(self._root):
            raise ValueError("Invalid storage key.")
        if path.name.endswith((_SIDECAR, ".tmp")):
            raise ValueError("Invalid storage key.")
        return path

    def _signature(self, method: str, key: str, content_type: str, expires: int) -> str:
        message = f"{method}\n{key}\n{content_type}\n{expires}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def _signed_url(self, method: str, key: str, content_type: str, expires_in: int) -> str:
        expires = int(time.time()) + expires_in
        query = urlencode(
            {
                "expires": expires,
                "content_type": content_type,
                "signature": self._signature(method, key, content_type, expires),
            }
        )
        return f"{self._origin}/api/v1/local-storage/{quote(key)}?{query}"

    def verify(
        self, method: str, key: str, content_type: str, expires: int, signature: str
    ) -> bool:
        if expires < time.time():
            return False
        expected = self._signature(method, key, content_type, expires)
        return hmac.compare_digest(expected, signature)

    def presigned_put(self, key: str, content_type: str, expires_in: int) -> str:
        return self._signed_url("PUT", key, content_type, expires_in)

    def presigned_get(self, key: str, expires_in: int) -> str:
        return self._signed_url("GET", key, "", expires_in)

    def content_type(self, key: str) -> str:
        path = self.path_for(key)
        sidecar = path.with_name(path.name + _SIDECAR)
        return sidecar.read_text() if sidecar.is_file() else "application/octet-stream"

    def size(self, key: str) -> int | None:
        path = self.path_for(key)
        return path.stat().st_size if path.is_file() else None

    def read(self, key: str, max_bytes: int) -> bytes:
        with self.path_for(key).open("rb") as handle:
            return handle.read(max_bytes + 1)

    def write(self, key: str, data: bytes, content_type: str) -> None:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.tmp")
        temporary.write_bytes(data)
        temporary.replace(path)  # readers never see a half-written file
        path.with_name(path.name + _SIDECAR).write_text(content_type)

    def delete(self, key: str) -> None:
        path = self.path_for(key)
        path.unlink(missing_ok=True)
        path.with_name(path.name + _SIDECAR).unlink(missing_ok=True)

    def list_objects(self, prefix: str, max_keys: int) -> list[tuple[str, datetime]]:
        found: list[tuple[str, datetime]] = []
        for path in sorted(self._root.rglob("*")):
            if not path.is_file() or path.name.endswith((_SIDECAR, ".tmp")):
                continue
            key = path.relative_to(self._root).as_posix()
            if key.startswith(prefix):
                found.append((key, datetime.fromtimestamp(path.stat().st_mtime, UTC)))
                if len(found) >= max_keys:
                    break
        return found


def init_storage(app: Flask) -> None:
    if app.config["STORAGE_BACKEND"] == "memory":
        app.extensions["storage"] = MemoryStorage()
        return
    if app.config["STORAGE_BACKEND"] == "local":
        app.extensions["storage"] = LocalStorage(
            app.config["LOCAL_STORAGE_DIR"], app.config["SECRET_KEY"], app.config["FRONTEND_ORIGIN"]
        )
        from app.common.local_storage_routes import blp  # only exists for this backend

        app.register_blueprint(blp)
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
