"""Server-side image verification and sanitization. The upload is treated as hostile.

The browser's filename and MIME type are never trusted: Pillow decodes the actual bytes, the
detected format must match the declared type, and the image is re-encoded. Re-encoding drops
all metadata (EXIF GPS coordinates of a tenant's home included) and any non-image payload
appended to the file (polyglots).
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000  # bounds decode memory (decompression bombs)
MAX_EDGE = 2560  # stored images are downscaled to this longest edge
OUTPUT_QUALITY = 85

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ImageRejected(Exception):  # noqa: N818 - a domain outcome, not an error in our code
    """The upload is not an acceptable image. The message is safe to show to the user."""


def sanitize_image(data: bytes, declared_type: str) -> tuple[bytes, int, int]:
    """Returns (jpeg_bytes, width, height) or raises ImageRejected."""
    expected_format = ALLOWED_CONTENT_TYPES.get(declared_type)
    if expected_format is None:
        raise ImageRejected("This file type is not supported.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            if probe.format != expected_format:
                raise ImageRejected("The file content does not match its declared type.")
            if probe.width * probe.height > MAX_PIXELS:
                raise ImageRejected("The image dimensions are too large.")
            probe.verify()  # structural check; the probe is unusable afterwards
        with Image.open(io.BytesIO(data)) as source:
            source.draft("RGB", (MAX_EDGE, MAX_EDGE))  # JPEG: decode at reduced scale
            picture: Image.Image = ImageOps.exif_transpose(source)  # keep orientation
            picture = picture.convert("RGB")
            picture.thumbnail((MAX_EDGE, MAX_EDGE))
            output = io.BytesIO()
            picture.save(output, format="JPEG", quality=OUTPUT_QUALITY, optimize=True)
            return output.getvalue(), picture.width, picture.height
    except ImageRejected:
        raise
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise ImageRejected("The file is not a valid image.") from exc
