"""Signed upload/download endpoints for STORAGE_BACKEND=local (development and tests only)."""

from __future__ import annotations

from flask import Blueprint, Response, abort, request, send_file

from app.common.storage import LOCAL_UPLOAD_LIMIT_BYTES, LocalStorage, get_storage

blp = Blueprint("local_storage", __name__, url_prefix="/api/v1/local-storage")


def _authorize(method: str, key: str, content_type: str) -> LocalStorage:
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        abort(404)
    try:
        expires = int(request.args.get("expires", ""))
        storage.path_for(key)
    except ValueError:
        abort(403)
    if not storage.verify(method, key, content_type, expires, request.args.get("signature", "")):
        abort(403)
    return storage


@blp.put("/<path:key>")
def upload(key: str) -> Response:
    signed_type = request.args.get("content_type", "")
    storage = _authorize("PUT", key, signed_type)
    if request.mimetype != signed_type:  # as with S3, the Content-Type is part of the signature
        abort(403)
    request.max_content_length = LOCAL_UPLOAD_LIMIT_BYTES  # photos exceed the 1 MB JSON limit
    storage.write(key, request.get_data(cache=False), signed_type)
    return Response(status=200)


@blp.get("/<path:key>")
def download(key: str) -> Response:
    storage = _authorize("GET", key, "")
    path = storage.path_for(key)
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype=storage.content_type(key), max_age=0)
