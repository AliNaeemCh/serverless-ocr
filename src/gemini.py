import json
import logging
import httpx

from config import config
from retry import async_retry_http


logger = logging.getLogger(__name__)


@async_retry_http()
async def call_gemini(
    user_prompt: str,
    system_prompt: str = "You are a helpful assistant",
    model: str = config.MODEL,
    fallback_model: str = config.FALLBACK_MODEL,
    image_base64: str | None = None,
    mime_type: str | None = "image/jpeg",
) -> str:

    logger.info(
        "Starting Gemini request (model=%s, has_image=%s)",
        model,
        bool(image_base64),
    )

    api_key = config.GEMINI_API_KEY

    parts = []

    if image_base64:

        logger.info(
            "Adding image to Gemini request (mime_type=%s)",
            mime_type,
        )

        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": image_base64,
            }
        })

    parts.append({
        "text": user_prompt
    })

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    model_in_use = model
    model_error = None

    while True:

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model_in_use}:generateContent"
        )

        logger.info(
            "Sending request to Gemini (model=%s)",
            model_in_use,
        )

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        logger.info(
            "Gemini response received (model=%s, status=%s)",
            model_in_use,
            response.status_code,
        )

        if response.is_error:

            logger.warning(
                "Gemini request failed (model=%s, status=%s)",
                model_in_use,
                response.status_code,
            )

            if model_in_use == model:

                try:
                    error_data = response.json()

                except ValueError:

                    error_data = {
                        "message": response.text,
                    }

                logger.warning(
                    "Primary Gemini model failed; "
                    "switching to fallback model=%s",
                    fallback_model,
                )

                model_error = json.dumps({
                    "status_code": response.status_code,
                    "error": error_data,
                })

                model_in_use = fallback_model

                continue

            logger.error(
                "Fallback Gemini model failed; "
                "raising previous model error"
            )

            raise RuntimeError(
                model_error
            )

        data = response.json()

        result = (
            data["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

        logger.info(
            "Gemini request successful (model=%s, response_chars=%s)",
            model_in_use,
            len(result),
        )

        return result