from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EXTRACTION_REPORT_PATH, EXTRACTED_TEXT_PATH, PDF_PATH
from src.pdf_processor import PDFProcessingError, extract_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect source PDF text and page metadata.")
    parser.add_argument("--pages", type=int, default=3, help="Number of page excerpts to show.")
    args = parser.parse_args()
    try:
        pages, report = extract_pdf(PDF_PATH, EXTRACTION_REPORT_PATH, EXTRACTED_TEXT_PATH)
    except PDFProcessingError as exc:
        print(f"PDF inspection failed: {exc}")
        if EXTRACTION_REPORT_PATH.exists():
            print(f"See report: {EXTRACTION_REPORT_PATH}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for page in pages[: max(args.pages, 0)]:
        print(f"\n--- PDF page {page.page_number} ---\n{page.text[:1200]}")
    if report["warning"]:
        print(f"\nWARNING: {report['warning']}")
    print(f"\nExtracted page text: {EXTRACTED_TEXT_PATH}")
    print(f"Extraction report: {EXTRACTION_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
