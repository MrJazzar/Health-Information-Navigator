"""HTTP client used by the Streamlit interface to call the Python backend."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 120


class BackendClientError(RuntimeError):
    """Raised when the local Python backend cannot complete an HTTP request."""


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{BACKEND_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("detail", {})
            message = detail.get("message", "") if isinstance(detail, dict) else ""
        except (UnicodeDecodeError, json.JSONDecodeError):
            message = ""
        if not message:
            message = "The backend rejected the request. Check the question and retry."
        raise BackendClientError(message) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise BackendClientError(
            "The Python backend is unavailable. Start it with "
            "`python -m uvicorn api:app --host 127.0.0.1 --port 8000`, then retry."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackendClientError("The Python backend returned an invalid response.") from exc

    if not isinstance(result, dict):
        raise BackendClientError("The Python backend returned an invalid response.")
    return result


def ask_backend(question: str) -> dict[str, Any]:
    result = _post("/api/ask", {"question": question})
    if (
        not isinstance(result.get("answer"), str)
        or not isinstance(result.get("passages"), list)
        or (
            result.get("safety_route") is not None
            and not isinstance(result.get("safety_route"), str)
        )
        or any(not isinstance(passage, dict) for passage in result["passages"])
    ):
        raise BackendClientError("The Python backend returned an invalid answer.")
    return result


def run_backend_action(
    action: str,
    question: str,
    answer: str | None = None,
) -> str:
    result = _post(
        "/api/action",
        {"action": action, "question": question, "answer": answer},
    )
    value = result.get("answer")
    if not isinstance(value, str) or not value:
        raise BackendClientError("The Python backend returned an invalid response.")
    return value
