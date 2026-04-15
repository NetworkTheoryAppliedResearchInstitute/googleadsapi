"""Centralized Google Ads API error handling with retry logic.

All service methods call handle_google_ads_exception() to convert
GoogleAdsException into clean FastAPI HTTP errors with actionable messages.
"""

from __future__ import annotations

import time
import random
from functools import wraps
from typing import Callable, TypeVar

from fastapi import HTTPException
from google.ads.googleads.errors import GoogleAdsException

F = TypeVar("F", bound=Callable)

# ── Error code → HTTP status mapping ─────────────────────────────────────────

_RETRYABLE_ERRORS = {
    "RESOURCE_TEMPORARILY_EXHAUSTED",  # QPS rate limit
    "INTERNAL_ERROR",
    "TRANSIENT_FAILURE",
    "DEADLINE_EXCEEDED",
}

_ERROR_HTTP_MAP: dict[str, int] = {
    "RESOURCE_EXHAUSTED": 429,           # daily quota
    "RESOURCE_TEMPORARILY_EXHAUSTED": 429,
    "AUTHENTICATION_ERROR": 401,
    "AUTHORIZATION_ERROR": 403,
    "REQUEST_ERROR": 400,
    "INTERNAL_ERROR": 500,
    "TOO_MANY_MUTATE_OPERATIONS": 400,
    "REQUEST_TOO_LARGE": 400,
    "INVALID_PAGE_SIZE": 400,
}


def handle_google_ads_exception(exc: GoogleAdsException) -> None:
    """Convert a GoogleAdsException into a FastAPI HTTPException.

    Extracts the first meaningful error and surfaces a clean message.
    Never returns — always raises.
    """
    errors = []
    retry_after: int | None = None

    for error in exc.failure.errors:
        code_name = error.error_code.WhichOneof("error_code") or "UNKNOWN"
        message = error.message
        errors.append(f"[{code_name}] {message}")

        # Parse retryAfterSeconds if present
        if hasattr(error, "details"):
            for detail in error.details:
                if hasattr(detail, "retry_delay"):
                    retry_after = int(detail.retry_delay.seconds)

    primary_code = ""
    if exc.failure.errors:
        primary_code = (
            exc.failure.errors[0].error_code.WhichOneof("error_code") or ""
        )

    http_status = _ERROR_HTTP_MAP.get(primary_code, 500)
    detail = "; ".join(errors) if errors else str(exc)

    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)

    raise HTTPException(
        status_code=http_status,
        detail=detail,
        headers=headers or None,
    )


# ── Retry decorator ───────────────────────────────────────────────────────────

def with_exponential_backoff(
    max_attempts: int = 5,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> Callable[[F], F]:
    """Decorator that retries a function on transient Google Ads API errors.

    Usage:
        @with_exponential_backoff()
        def my_api_call(): ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except GoogleAdsException as exc:
                    primary_code = ""
                    if exc.failure.errors:
                        primary_code = (
                            exc.failure.errors[0]
                            .error_code.WhichOneof("error_code")
                            or ""
                        )
                    if primary_code not in _RETRYABLE_ERRORS or attempt == max_attempts:
                        handle_google_ads_exception(exc)

                    sleep_time = delay + (random.uniform(0, 1) if jitter else 0)
                    sleep_time = min(sleep_time, max_delay)
                    time.sleep(sleep_time)
                    delay = min(delay * 2, max_delay)
        return wrapper  # type: ignore[return-value]
    return decorator


# ── Partial failure parser ────────────────────────────────────────────────────

def parse_partial_failures(response) -> list[dict]:
    """Extract per-operation errors from a mutate response with partial_failure=True.

    Returns a list of dicts with operation_index and error detail for failed ops.
    """
    from google.ads.googleads.errors import GoogleAdsException
    from google.protobuf import any_pb2

    failures = []
    if not response.partial_failure_error:
        return failures

    from google.ads.googleads.v20.errors.types import (
        google_ads_failure as gaf,
    )

    failure_bytes = response.partial_failure_error.details[0].value
    failure_msg = gaf.GoogleAdsFailure.deserialize(failure_bytes)

    for error in failure_msg.errors:
        location = error.location
        op_index = None
        if location.field_path_elements:
            op_index = location.field_path_elements[0].index

        failures.append(
            {
                "operation_index": op_index,
                "error_code": error.error_code.WhichOneof("error_code"),
                "message": error.message,
            }
        )
    return failures
