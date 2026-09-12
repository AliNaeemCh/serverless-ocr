import base64
import pymupdf


def iterate_pdf_as_images(
    file_path: str,
    dpi: int = 100,
):

    doc = pymupdf.open(file_path)

    try:

        for page in doc:

            pix = page.get_pixmap(
                dpi=dpi,
                alpha=False,
            )

            image_bytes = pix.tobytes(
                "jpeg"
            )

            yield base64.b64encode(
                image_bytes
            ).decode("ascii")

    finally:
        doc.close()


def get_pdf_page_count(
    file_path: str,
) -> int:

    doc = pymupdf.open(file_path)

    try:
        return len(doc)

    finally:
        doc.close()