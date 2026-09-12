import asyncio
import json
import logging
import random

from functools import wraps


logger = logging.getLogger(__name__)


RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}


def _parse_error(
    exc: RuntimeError,
):

    try:

        return json.loads(
            str(exc)
        )

    except (
        json.JSONDecodeError,
        TypeError,
    ):

        logger.warning(
            "Failed to parse RuntimeError as JSON"
        )

        return None


def _is_daily_quota_exceeded(
    error_data: dict,
) -> bool:

    details = (
        error_data
        .get("error", {})
        .get("error", {})
        .get("details", [])
    )

    for detail in details:

        if not detail.get(
            "@type",
            "",
        ).endswith(
            "/QuotaFailure"
        ):
            continue

        for violation in detail.get(
            "violations",
            [],
        ):

            quota_id = violation.get(
                "quotaId",
                "",
            )

            if "PerDay" in quota_id:

                logger.warning(
                    "Gemini daily quota exceeded: %s",
                    quota_id,
                )

                return True

    return False


def _get_gemini_retry_delay(
    error_data: dict,
):

    details = (
        error_data
        .get("error", {})
        .get("error", {})
        .get("details", [])
    )

    for detail in details:

        if not detail.get(
            "@type",
            "",
        ).endswith(
            "/RetryInfo"
        ):
            continue

        retry_delay = detail.get(
            "retryDelay"
        )

        if not retry_delay:
            return None

        try:

            if retry_delay.endswith("ms"):
                return (
                    float(
                        retry_delay[:-2]
                    ) / 1000
                )

            if retry_delay.endswith("s"):
                return float(
                    retry_delay[:-1]
                )

            return float(
                retry_delay
            )

        except (
            ValueError,
            AttributeError,
        ):

            logger.warning(
                "Failed to parse Gemini retry delay: %s",
                retry_delay,
            )

            return None

    return None


def async_retry_http(
    max_attempts=3,
    base_delay=0.25,
    multiplier=2,
    max_delay=10,
    overall_timeout=float("inf"),
):

    def decorator(func):

        @wraps(func)
        async def wrapper(
            *args,
            **kwargs,
        ):

            loop = (
                asyncio.get_running_loop()
            )

            deadline = (
                loop.time()
                + overall_timeout
            )

            for attempt in range(
                max_attempts
            ):

                try:

                    return await func(
                        *args,
                        **kwargs
                    )

                except RuntimeError as exc:

                    error_data = _parse_error(
                        exc
                    )

                    if error_data is None:

                        logger.warning(
                            "Non-structured error in %s",
                            func.__name__,
                        )

                        raise

                    status_code = (
                        error_data.get(
                            "status_code"
                        )
                    )

                    logger.warning(
                        "%s failed with status %s "
                        "(attempt %s/%s)",
                        func.__name__,
                        status_code,
                        attempt + 1,
                        max_attempts,
                    )

                    if (
                        status_code
                        not in RETRYABLE_STATUS_CODES
                    ):

                        logger.warning(
                            "Status %s is not retryable",
                            status_code,
                        )

                        raise

                    if _is_daily_quota_exceeded(
                        error_data
                    ):

                        logger.warning(
                            "Daily quota exhausted; "
                            "not retrying"
                        )

                        raise

                    if (
                        attempt
                        == max_attempts - 1
                    ):

                        logger.warning(
                            "Maximum retry attempts reached"
                        )

                        raise

                    remaining = (
                        deadline
                        - loop.time()
                    )

                    if remaining <= 0:

                        logger.warning(
                            "Retry deadline exceeded; "
                            "not retrying"
                        )

                        raise TimeoutError(
                            "Retry deadline exceeded"
                        )

                    delay = (
                        _get_gemini_retry_delay(
                            error_data
                        )
                    )

                    if delay is not None:

                        logger.info(
                            "Using Gemini RetryInfo "
                            "delay: %.2fs",
                            delay,
                        )

                    if delay is None:

                        exponential = min(
                            max_delay,
                            base_delay
                            * (
                                multiplier
                                ** attempt
                            ),
                        )

                        delay = random.uniform(
                            0,
                            exponential,
                        )

                        logger.info(
                            "Using exponential backoff "
                            "delay: %.2fs",
                            delay,
                        )

                    delay = min(
                        delay,
                        remaining,
                    )

                    logger.info(
                        "Retrying %s in %.2fs",
                        func.__name__,
                        delay,
                    )

                    await asyncio.sleep(
                        delay
                    )

        return wrapper

    return decorator