from __future__ import annotations

from pathlib import Path

import pytest

from src.pdf_processor import PDFProcessingError, extract_pdf


def _make_pdf(path: Path, page_texts: list[str]) -> None:
    objects: dict[int, bytes] = {}
    page_refs: list[str] = []
    for index, text in enumerate(page_texts):
        page_id = 3 + index * 3
        font_id = page_id + 1
        content_id = page_id + 2
        page_refs.append(f"{page_id} 0 R")
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
        objects[page_id] = (
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>\nendobj\n".encode("ascii")
        )
        objects[font_id] = (
            f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            "endobj\n".encode("ascii")
        )
        objects[content_id] = (
            f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream\nendobj\n"
        )
    objects[1] = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    objects[2] = (
        f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(page_refs)}] "
        f"/Count {len(page_refs)} >>\nendobj\n".encode("ascii")
    )
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0] * (max(objects) + 1)
    for number in sorted(objects):
        offsets[number] = len(pdf)
        pdf.extend(objects[number])
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(pdf)


def test_extracts_text_and_preserves_original_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    report_path = tmp_path / "report.json"
    text_path = tmp_path / "pages.jsonl"
    _make_pdf(
        pdf_path,
        ["First readable page | 17", "Second readable page", "Third readable page | 19"],
    )

    pages, report = extract_pdf(pdf_path, report_path, text_path)

    assert [page.page_number for page in pages] == [1, 2, 3]
    assert "First readable page" in pages[0].text
    assert "Second readable page" in pages[1].text
    assert "Third readable page" in pages[2].text
    assert pages[0].page_label == 17
    assert pages[1].page_label == 18
    assert pages[2].page_label == 19
    assert report["page_labels"] == [
        {"pdf_page": 1, "source_page": 17},
        {"pdf_page": 2, "source_page": 18},
        {"pdf_page": 3, "source_page": 19},
    ]
    assert report["page_count"] == 3
    assert report["total_extracted_characters"] > 0
    assert report["pages_with_images"] == []
    assert report_path.exists()
    assert len(text_path.read_text(encoding="utf-8").splitlines()) == 3


def test_empty_extraction_is_reported_and_not_silently_accepted(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    report_path = tmp_path / "report.json"
    _make_pdf(pdf_path, [""])

    with pytest.raises(PDFProcessingError, match="no extractable text"):
        extract_pdf(pdf_path, report_path)
    assert report_path.exists()


def test_missing_pdf_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(PDFProcessingError, match="not found"):
        extract_pdf(tmp_path / "missing.pdf")
