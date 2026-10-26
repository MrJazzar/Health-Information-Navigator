"""Classification for Gemini API failures without exposing credentials."""

from __future__ import annotations

import socket
from typing import Any


class GeminiRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        quota_exhausted: bool = False,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.quota_exhausted = quota_exhausted


def classify_api_error(exc: Exception) -> tuple[bool, bool]:
    """Return (retryable, quota_exhausted); unknown 429s stop rather than loop."""
    status: Any = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    status_text = str(getattr(exc, "status", "")).upper()
    message = str(exc).casefold()
    details = getattr(exc, "message", None)
    if details:
        message = f"{message} {details}".casefold()

    quota_markers = (
        "quota",
        "billing",
        "resource_exhausted",
        "resource exhausted",
        "daily limit",
        "per day",
        "limit: 0",
    )
    if any(marker in message for marker in quota_markers) or "RESOURCE_EXHAUSTED" in status_text:
        return False, True

    try:
        status_number = int(status)
    except (TypeError, ValueError):
        status_number = None

    if status_number in (500, 502, 503, 504) or any(
        marker in status_text for marker in ("INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED")
    ):
        return True, False

    rate_limit_markers = (
        "rate limit",
        "rate-limit",
        "too many requests",
        "requests per minute",
        "retry-after",
    )
    if status_number == 429 or "TOO MANY REQUESTS" in status_text:
        if any(marker in message for marker in rate_limit_markers):
            return True, False
        return False, True

    if isinstance(exc, (TimeoutError, socket.timeout)) or any(
        marker in message for marker in ("timed out", "timeout", "deadline exceeded")
    ):
        return True, False
    return False, False
