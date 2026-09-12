import os
import uuid
import base64
import mimetypes
import logging
import json


logger = logging.getLogger(__name__)


TMP_DIR = "/tmp"


def detect_file_type(
    file_bytes: bytes,
) -> str | None:

    if file_bytes.startswith(b"%PDF"):
        return "pdf"

    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if file_bytes.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return "image/png"

    if (
        file_bytes.startswith(b"RIFF")
        and file_bytes[8:12] == b"WEBP"
    ):
        return "image/webp"

    return None


def save_uploaded_file(
    event,
    filename=None,
) -> str:
    """
    Save uploaded PDF/image to Lambda's
    /tmp directory.

    Expected HTTP JSON body:

    {
        "filename": "document.pdf",
        "file": "<base64>",
        "connectionId": "..."
    }
    """

    logger.info(
        "Saving file to temporary storage"
    )

    body = event.get("body")

    if body is None:
        raise ValueError(
            "No request body found"
        )

    if event.get(
        "isBase64Encoded",
        False,
    ):

        try:

            body = base64.b64decode(
                body
            ).decode("utf-8")

        except Exception:

            raise ValueError(
                "Invalid base64 request body"
            )

    try:

        data = (
            json.loads(body)
            if isinstance(body, str)
            else body
        )

    except json.JSONDecodeError:

        raise ValueError(
            "Request body must be valid JSON"
        )

    file_base64 = data.get("file")

    if not file_base64:

        raise ValueError(
            "No file data found in request"
        )

    if filename is None:
        filename = data.get("filename")

    try:

        file_bytes = base64.b64decode(
            file_base64
        )

    except Exception:

        raise ValueError(
            "Invalid base64 file data"
        )

    if not file_bytes:

        raise ValueError(
            "Uploaded file is empty"
        )

    file_type = detect_file_type(
        file_bytes
    )

    if file_type is None:

        raise ValueError(
            "Unsupported file type. "
            "Only PDF and image files are allowed."
        )

    logger.info(
        "Uploaded file received "
        "(type=%s, size=%d bytes)",
        file_type,
        len(file_bytes),
    )

    if filename is None:

        extension = {
            "pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }[file_type]

        filename = (
            f"upload-{uuid.uuid4().hex}"
            f"{extension}"
        )

    # Prevent directory traversal

    filename = os.path.basename(
        filename
    )

    file_path = os.path.join(
        TMP_DIR,
        filename,
    )

    with open(
        file_path,
        "wb",
    ) as f:

        f.write(file_bytes)

    logger.info(
        "File [%s] saved to temporary storage "
        "(type=%s)",
        filename,
        file_type,
    )

    return file_path


def image_to_gemini_format(
    file_path: str,
) -> tuple[str, str]:

    with open(
        file_path,
        "rb",
    ) as f:

        image_bytes = f.read()

    base64_image = (
        base64.b64encode(
            image_bytes
        ).decode("utf-8")
    )

    mime_type, _ = mimetypes.guess_type(
        file_path
    )

    if mime_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:

        raise ValueError(
            "Unsupported image format"
        )

    return (
        base64_image,
        mime_type,
    )