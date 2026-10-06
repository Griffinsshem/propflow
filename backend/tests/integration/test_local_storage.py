from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from flask import Flask

from app import create_app
from app.common.storage import LOCAL_UPLOAD_LIMIT_BYTES, LocalStorage
from app.extensions import db

KEY = "orgs/o1/requests/r1/pending/a1"


@pytest.fixture()
def local_app(migrated_database: None, tmp_path: Path) -> Iterator[Flask]:
    app = create_app(
        "test",
        overrides={
            "STORAGE_BACKEND": "local",
            "LOCAL_STORAGE_DIR": str(tmp_path),
            "FRONTEND_ORIGIN": "http://localhost:3000",
        },
    )
    yield app
    with app.app_context():
        db.engine.dispose()


def storage_of(app: Flask) -> LocalStorage:
    storage = app.extensions["storage"]
    assert isinstance(storage, LocalStorage)
    return storage


def relative(url: str) -> str:
    parts = urlsplit(url)
    assert parts.netloc == "localhost:3000"  # links go through the frontend origin
    return f"{parts.path}?{parts.query}"


def test_signed_upload_and_download_round_trip(local_app: Flask) -> None:
    storage, client = storage_of(local_app), local_app.test_client()
    upload = relative(storage.presigned_put(KEY, "image/png", 300))
    assert client.put(upload, data=b"png-bytes", content_type="image/png").status_code == 200
    assert storage.size(KEY) == len(b"png-bytes")

    download = client.get(relative(storage.presigned_get(KEY, 300)))
    assert download.status_code == 200
    assert download.data == b"png-bytes"
    assert download.mimetype == "image/png"


def test_uploads_larger_than_the_json_limit_are_accepted(local_app: Flask) -> None:
    storage, client = storage_of(local_app), local_app.test_client()
    photo = b"0" * (3 * 1024 * 1024)
    upload = relative(storage.presigned_put(KEY, "image/jpeg", 300))
    assert client.put(upload, data=photo, content_type="image/jpeg").status_code == 200
    assert storage.size(KEY) == len(photo)


def test_tampered_expired_reused_or_mismatched_links_are_refused(local_app: Flask) -> None:
    storage, client = storage_of(local_app), local_app.test_client()
    upload = relative(storage.presigned_put(KEY, "image/png", 300))
    attempts = [
        (upload.replace("signature=", "signature=0"), "image/png"),  # tampered signature
        (upload.replace(KEY, f"{KEY}x"), "image/png"),  # different key
        (upload, "image/jpeg"),  # content type other than the signed one
        (relative(storage.presigned_put(KEY, "image/png", -1)), "image/png"),  # expired
        (relative(storage.presigned_get(KEY, 300)), "image/png"),  # a download link
    ]
    for url, content_type in attempts:
        assert client.put(url, data=b"x", content_type=content_type).status_code == 403, url
    assert storage.size(KEY) is None


def test_oversized_uploads_are_refused(local_app: Flask) -> None:
    storage, client = storage_of(local_app), local_app.test_client()
    upload = relative(storage.presigned_put(KEY, "image/png", 300))
    too_big = b"0" * (LOCAL_UPLOAD_LIMIT_BYTES + 1)
    assert client.put(upload, data=too_big, content_type="image/png").status_code == 413
    assert storage.size(KEY) is None


def test_keys_cannot_escape_the_storage_directory(tmp_path: Path) -> None:
    storage = LocalStorage(str(tmp_path / "root"), "s" * 40, "http://localhost:3000")
    for key in ("../escape", "a/../../escape", "/etc/passwd"):
        with pytest.raises(ValueError):
            storage.write(key, b"x", "text/plain")
    assert not (tmp_path / "escape").exists()
