"""Environment-backed configuration for Mental Health Navigator."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if parsed < minimum:
        requirement = "non-negative" if minimum == 0 else "greater than zero"
        raise ValueError(f"{name} must be {requirement}.")
    return parsed


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not 0 <= parsed <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")
    return parsed


DATA_DIR = ROOT_DIR / "data"
STORAGE_DIR = ROOT_DIR / "storage"
INDEX_PATH = STORAGE_DIR / "index.json"
CHUNKS_PATH = STORAGE_DIR / "chunks.jsonl"
EXTRACTION_REPORT_PATH = STORAGE_DIR / "extraction_report.json"
EXTRACTED_TEXT_PATH = STORAGE_DIR / "extracted_text.jsonl"

_pdf_override = os.getenv("PDF_PATH", "").strip()
if _pdf_override:
    PDF_PATH = Path(_pdf_override).expanduser()
    if not PDF_PATH.is_absolute():
        PDF_PATH = ROOT_DIR / PDF_PATH
else:
    _standard_pdf = DATA_DIR / "mental_health_book.pdf"
    _existing_pdfs = sorted(DATA_DIR.glob("*.pdf"))
    PDF_PATH = _standard_pdf if _standard_pdf.exists() else (
        _existing_pdfs[0] if len(_existing_pdfs) == 1 else _standard_pdf
    )

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").strip().lower()
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "").strip()
RETRIEVAL_TOP_K = _int_env("RETRIEVAL_TOP_K", 3)
RETRIEVAL_MIN_SIMILARITY = _float_env("RETRIEVAL_MIN_SIMILARITY", 0.62)
CHUNK_SIZE_CHARS = _int_env("CHUNK_SIZE_CHARS", 2600)
CHUNK_OVERLAP_CHARS = _int_env("CHUNK_OVERLAP_CHARS", 400, minimum=0)
