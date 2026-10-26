"""Minimal, question-free local feedback storage."""

from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_FIELDS = (
    "timestamp_utc",
    "anonymous_session_id",
    "category",
    "technical_metadata",
)


def anonymous_session_id() -> str:
    return uuid.uuid4().hex


def record_feedback(
    path: Path,
    category: str,
    session_id: str,
    technical_metadata: str = "local-streamlit",
) -> None:
    if category not in {"helpful", "not_helpful", "report_issue"}:
        raise ValueError("Unsupported feedback category.")
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FEEDBACK_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "anonymous_session_id": session_id,
                "category": category,
                "technical_metadata": technical_metadata[:100],
            }
        )


def delete_feedback(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True
