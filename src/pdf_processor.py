"""PDF extraction with explicit per-page reporting."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class PDFProcessingError(RuntimeError):
    """Raised when the source PDF cannot be read or contains no extractable text."""


@dataclass
class PageText:
    page_number: int
    text: str
    extraction_error: str | None = None
    page_label: str | int | None = None
    image_count: int = 0


def _printed_page_label(text: str) -> str | int | None:
    match = re.search(r"\|\s*([ivxlcdm]+|\d{1,3})\s*$", text.strip(), re.IGNORECASE)
    if not match:
        return None
    label = match.group(1)
    return int(label) if label.isdigit() else label.lower()


def _fill_missing_arabic_labels(pages: list[PageText]) -> None:
    offsets: dict[int, int] = {}
    for page in pages:
        if isinstance(page.page_label, int):
            offset = page.page_number - page.page_label
            offsets[offset] = offsets.get(offset, 0) + 1
    if not offsets:
        return
    offset = max(offsets, key=offsets.get)
    for page in pages:
        if page.page_number > offset and not (
            isinstance(page.page_label, str)
            and re.fullmatch(r"[ivxlcdm]+", page.page_label, re.IGNORECASE)
        ):
            page.page_label = page.page_number - offset


def extract_pdf(
    pdf_path: Path,
    report_path: Path | None = None,
    text_path: Path | None = None,
    low_text_threshold: int = 100,
) -> tuple[list[PageText], dict[str, Any]]:
    """Extract every page, preserving one-based printed PDF page positions."""
    if not pdf_path.is_file():
        raise PDFProcessingError(f"Source PDF not found: {pdf_path}")
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise PDFProcessingError("The PDF is encrypted and could not be opened.") from exc
        page_count = len(reader.pages)
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError(f"Could not open PDF: {exc}") from exc

    pages: list[PageText] = []
    image_inspection_errors: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            error = None
        except Exception as exc:
            text = ""
            error = f"{type(exc).__name__}: {exc}"
        try:
            image_count = len(page.images)
        except Exception as exc:
            image_count = 0
            image_inspection_errors.append(
                {"page": index, "error": f"{type(exc).__name__}: {exc}"}
            )
        pages.append(
            PageText(
                index,
                text,
                error,
                page_label=_printed_page_label(text),
                image_count=image_count,
            )
        )

    _fill_missing_arabic_labels(pages)
    no_text = [page.page_number for page in pages if not page.text.strip()]
    little_text = [
        page.page_number
        for page in pages
        if 0 < len(page.text.strip()) < low_text_threshold
    ]
    extraction_errors = [
        {"page": page.page_number, "error": page.extraction_error}
        for page in pages
        if page.extraction_error
    ]
    image_pages = [
        {"page": page.page_number, "image_count": page.image_count}
        for page in pages
        if page.image_count
    ]
    image_heavy_pages = [
        page.page_number
        for page in pages
        if page.image_count >= 3
        or (page.image_count > 0 and len(page.text.strip()) < low_text_threshold)
    ]
    total_chars = sum(len(page.text) for page in pages)
    report: dict[str, Any] = {
        "source_file": pdf_path.name,
        "page_count": page_count,
        "page_labels": [
            {"pdf_page": page.page_number, "source_page": page.page_label or page.page_number}
            for page in pages
        ],
        "total_extracted_characters": total_chars,
        "pages_with_no_text": no_text,
        "pages_with_little_text": little_text,
        "low_text_threshold_characters": low_text_threshold,
        "pages_with_extraction_errors": extraction_errors,
        "pages_with_images": image_pages,
        "pages_with_image_inspection_errors": image_inspection_errors,
        "pages_with_potential_scan_or_image_heavy_content": sorted(
            set(no_text + image_heavy_pages)
        ),
        "potentially_scanned_or_image_heavy": bool(no_text or image_heavy_pages),
        "ocr_performed": False,
        "warning": (
            "Some pages contain no/very little extractable text and/or multiple images. "
            "They may be scanned or image-heavy; OCR has not been run. Review those "
            "pages manually if they are needed."
            if no_text or image_heavy_pages
            else None
        ),
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if text_path:
        text_path.parent.mkdir(parents=True, exist_ok=True)
        with text_path.open("w", encoding="utf-8") as output:
            for page in pages:
                output.write(
                    json.dumps(asdict(page), ensure_ascii=False) + "\n"
                )
    if not any(page.text.strip() for page in pages):
        raise PDFProcessingError(
            "The PDF has no extractable text. It may be scanned; inspect the report "
            "and use a trusted local OCR workflow if appropriate. No OCR was run."
        )
    return pages, report
