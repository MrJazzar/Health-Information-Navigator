"""Recalculate human-review metrics from an annotated evaluation CSV or JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from evaluation.metrics import summarize_results


def _parse_binary(value: Any) -> Any:
    if value in (0, 1, False, True):
        return int(value)
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    return ""


def _read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.casefold() == ".csv":
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as source:
                records = list(csv.DictReader(source))
        except OSError as exc:
            raise ValueError(f"Could not read CSV results: {exc}") from exc
        for record in records:
            record["answerable"] = record.get("answerable", "").casefold() == "true"
            record["retrieval_success"] = (
                record.get("retrieval_success", "").casefold() == "true"
            )
            record["recall_at_5"] = _parse_binary(record.get("recall_at_5"))
            record["answer_correctness_human"] = _parse_binary(
                record.get("answer_correctness_human")
            )
            record["abstention_review_human"] = _parse_binary(
                record.get("abstention_review_human")
            )
            for field in (
                "expected_book_pages",
                "retrieved_top5_book_pages",
                "retrieved_top5_pdf_pages",
                "retrieved_top5_scores",
                "app_retrieved_book_pages",
                "citation_reviews",
            ):
                try:
                    record[field] = json.loads(record.get(field) or "[]")
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in CSV field '{field}'.") from exc
            if record.get("latency_ms"):
                record["latency_ms"] = float(record["latency_ms"])
        return records
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        records = document.get("results", document)
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise ValueError(f"Could not read JSON results: {exc}") from exc
    if not isinstance(records, list):
        raise ValueError("JSON results must be a list or contain a 'results' list.")
    return records


def score_file(path: Path) -> dict[str, Any]:
    records = _read_records(path)
    return {
        "input_file": str(path),
        "reviewed_results": len(records),
        "summary": summarize_results(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_file", type=Path)
    args = parser.parse_args()
    try:
        report = score_file(args.results_file)
    except ValueError as exc:
        print(f"Could not score evaluation results: {exc}")
        return 1
    output_path = args.results_file.with_name(
        args.results_file.stem + "_metrics.json"
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Metric report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
