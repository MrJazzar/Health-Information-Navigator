"""Transparent aggregate calculations for evaluation result records."""

from __future__ import annotations

import statistics
from typing import Any


def _reviewed_binary(records: list[dict[str, Any]], field: str) -> tuple[int, int]:
    values = [
        record[field]
        for record in records
        if record.get(field) in (0, 1, False, True)
    ]
    return sum(int(value) for value in values), len(values)


def summarize_results(records: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval_rows = [
        record
        for record in records
        if record.get("answerable") is True
        and record.get("expected_book_pages")
        and record.get("retrieval_success") is True
    ]
    retrieval_hits = sum(
        int(record.get("recall_at_5") == 1) for record in retrieval_rows
    )
    answer_correct, answer_reviewed = _reviewed_binary(
        records, "answer_correctness_human"
    )

    citation_values: list[bool] = []
    for record in records:
        reviews = record.get("citation_reviews", [])
        if isinstance(reviews, list):
            citation_values.extend(
                item["supported"]
                for item in reviews
                if isinstance(item, dict) and item.get("supported") in (True, False)
            )

    unanswerable = [
        record for record in records if record.get("answerable") is False
    ]
    normal_unanswerable = [
        record for record in unanswerable if not record.get("safety_route")
    ]
    automatic_abstentions = sum(
        int(
            record.get("automatic_abstention") is True
            and not record.get("safety_route")
        )
        for record in unanswerable
    )
    unanswerable_with_app_passages = sum(
        int(bool(record.get("app_retrieved_book_pages")))
        for record in normal_unanswerable
    )
    local_safety_refusals = sum(
        int(bool(record.get("safety_route")))
        for record in unanswerable
    )
    manual_abstention_values = [
        record["abstention_review_human"]
        for record in unanswerable
        if record.get("abstention_review_human") in (0, 1, False, True)
    ]
    manual_appropriate_abstentions = sum(map(int, manual_abstention_values))
    manual_inappropriate_abstentions = (
        len(manual_abstention_values) - manual_appropriate_abstentions
    )
    latencies = [
        float(record["latency_ms"])
        for record in records
        if record.get("run_status") == "completed"
        and isinstance(record.get("latency_ms"), (int, float))
    ]
    latency_scopes = sorted(
        {
            str(record.get("latency_scope", "not_recorded"))
            for record in records
            if record.get("run_status") == "completed"
        }
    )

    return {
        "question_count": len(records),
        "retrieval_recall_at_5": {
            "hits": retrieval_hits,
            "eligible_denominator": len(retrieval_rows),
            "rate": retrieval_hits / len(retrieval_rows) if retrieval_rows else None,
            "measurement": "automated against manually verified expected source pages",
        },
        "answer_correctness": {
            "correct": answer_correct,
            "human_reviewed_denominator": answer_reviewed,
            "rate": answer_correct / answer_reviewed if answer_reviewed else None,
            "measurement": "human reviewed; no automatic correctness claim",
        },
        "citation_support_rate": {
            "supported_claim_citations": sum(citation_values),
            "reviewed_claim_citations": len(citation_values),
            "rate": sum(citation_values) / len(citation_values) if citation_values else None,
            "measurement": "human claim-by-claim review; page-number presence alone is insufficient",
        },
        "abstention_quality": {
            "unanswerable_questions": len(unanswerable),
            "normal_unanswerable_questions": len(normal_unanswerable),
            "normal_unanswerable_with_retrieved_passages": unanswerable_with_app_passages,
            "automatic_source_empty_abstentions": automatic_abstentions,
            "local_safety_refusals_reported_separately": local_safety_refusals,
            "human_reviewed": len(manual_abstention_values),
            "human_appropriate": manual_appropriate_abstentions,
            "human_inappropriate": manual_inappropriate_abstentions,
            "human_reviewed_rate": (
                manual_appropriate_abstentions / len(manual_abstention_values)
                if manual_abstention_values
                else None
            ),
            "measurement": (
                "No-hit abstentions are detected from the app's deterministic threshold "
                "path. Normal unanswerable questions with retrieved passages require "
                "generation and human review."
            ),
        },
        "latency": {
            "successful_runs": len(latencies),
            "median_ms": statistics.median(latencies) if latencies else None,
            "scope": (
                latency_scopes[0]
                if len(latency_scopes) == 1
                else "mixed: " + ", ".join(latency_scopes)
                if latency_scopes
                else "not_recorded"
            ),
        },
    }
