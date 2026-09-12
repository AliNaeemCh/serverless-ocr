import asyncio
import logging

from collections import deque

from config import config
from gemini import call_gemini
from pdf import iterate_pdf_as_images, get_pdf_page_count
from prompts import SYSTEM_PROMPT, USER_PROMPT
from websocket import send_websocket_message
from files import image_to_gemini_format


logger = logging.getLogger(__name__)


def on_progress(
    connection_id,
    page,
    completed,
    total,
):

    message = {
        "status": "progress",
        "page": page,
        "completed": completed,
        "total": total,
        "percent": round(
            completed / total * 100
        ),
    }

    logger.info(
        "Completed page %d (%d/%d)",
        page,
        completed,
        total,
    )

    send_websocket_message(
        connection_id,
        message,
    )


async def process_pdf_pages(
    file_path: str,
    connection_id: str,
):

    tasks = deque()
    results = []
    completed = 0

    total_pages = get_pdf_page_count(
        file_path
    )

    logger.info(
        "Processing PDF (pages=%d, max_concurrency=%d)",
        total_pages,
        config.MAX_CONCURRENCY,
    )

    for page_number, page_img in enumerate(
        iterate_pdf_as_images(
            file_path=file_path
        ),
        start=1,
    ):

        if len(tasks) >= config.MAX_CONCURRENCY:

            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:

                page_number_ = next(
                    page
                    for page, t in tasks
                    if t is task
                )

                result = await task

                results.append(
                    (page_number_, result)
                )

                completed += 1

                on_progress(
                    connection_id,
                    page_number_,
                    completed,
                    total_pages,
                )

            tasks = deque(
                (page, task)
                for page, task in tasks
                if task in pending
            )

        logger.info(
            "Started processing page %d",
            page_number,
        )

        task = asyncio.create_task(
            call_gemini(
                user_prompt=USER_PROMPT,
                system_prompt=SYSTEM_PROMPT,
                model=config.MODEL,
                fallback_model=config.FALLBACK_MODEL,
                image_base64=page_img,
            )
        )

        tasks.append(
            (page_number, task)
        )

    # Finish remaining tasks

    while tasks:

        done, pending = await asyncio.wait(
            [task for _, task in tasks],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:

            page_number = next(
                page
                for page, t in tasks
                if t is task
            )

            result = await task

            results.append(
                (page_number, result)
            )

            completed += 1

            on_progress(
                connection_id,
                page_number,
                completed,
                total_pages,
            )

        tasks = deque(
            (page, task)
            for page, task in tasks
            if task in pending
        )

    # Restore original page order

    results.sort(
        key=lambda x: x[0]
    )

    logger.info(
        "All PDF pages processed successfully"
    )

    return [
        result
        for _, result in results
    ]


async def process_document(
    file_path: str,
    connection_id: str,
) -> str:

    if file_path.lower().endswith(".pdf"):

        results = await process_pdf_pages(
            file_path,
            connection_id,
        )

        return "\n\n---\n\n".join(results)

    logger.info(
        "Processing image"
    )

    image, mime_type = image_to_gemini_format(
        file_path
    )

    return await call_gemini(
        user_prompt=USER_PROMPT,
        system_prompt=SYSTEM_PROMPT,
        model=config.MODEL,
        fallback_model=config.FALLBACK_MODEL,
        image_base64=image,
        mime_type=mime_type,
    )


async def mock_process_pdf_pages(
    file_path: str,
    connection_id: str,
):

    total_pages = (
        get_pdf_page_count(file_path)
        if file_path.endswith(".pdf")
        else 5
    )

    logger.info(
        "MOCK: Processing %d pages",
        total_pages,
    )

    results = []

    for page in range(
        1,
        total_pages + 1,
    ):

        await asyncio.sleep(0.5)

        on_progress(
            connection_id=connection_id,
            page=page,
            completed=page,
            total=total_pages,
        )

        results.append(
            f"## Page {page}\n"
            f"This is dummy extracted text from page {page}."
        )

    return results