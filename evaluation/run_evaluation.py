"""Run the source-grounded evaluation dataset against the existing RAG pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    INDEX_PATH,
    PDF_PATH,
    RETRIEVAL_MIN_SIMILARITY,
    RETRIEVAL_TOP_K,
)
from evaluation.metrics import summarize_results  # noqa: E402
from src.answer_generator import (  # noqa: E402
    AnswerGenerationError,
    UnsupportedQuestionError,
    generate_answer,
)
from src.embeddings import EmbeddingError, create_embedding_provider  # noqa: E402
from src.retriever import RetrievalError, file_sha256, load_index, rank_chunks  # noqa: E402
from src.safety import Route, assess_question  # noqa: E402

DATASET_PATH = Path(__file__).with_name("evaluation_dataset.json")
RESULTS_DIR = Path(__file__).with_name("results")
CSV_FIELDS = [
    "question_id",
    "question",
    "answerable",
    "category",
    "embedding_provider",
    "expected_answer_points",
    "expected_behavior_if_insufficient",
    "expected_book_pages",
    "expected_pdf_pages",
    "retrieved_top5_book_pages",
    "retrieved_top5_pdf_pages",
    "retrieved_top5_scores",
    "retrieved_sources",
    "app_retrieved_book_pages",
    "recall_at_5",
    "retrieval_success",
    "retrieval_latency_ms",
    "run_status",
    "result_status",
    "attempts",
    "safety_route",
    "latency_ms",
    "latency_scope",
    "answer_text",
    "automatic_abstention",
    "answer_correctness_human",
    "citation_reviews",
    "abstention_review_human",
    "reviewer",
    "review_notes",
    "error",
]


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        questions = payload["questions"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Could not load evaluation dataset '{path}': {exc}") from exc
    if not isinstance(questions, list) or len(questions) != 20:
        raise ValueError("Evaluation dataset must contain exactly 20 questions.")
    ids = [question.get("id") for question in questions]
    if len(set(ids)) != len(ids) or any(not isinstance(item, str) for item in ids):
        raise ValueError("Evaluation dataset question IDs must be unique strings.")
    required = {
        "question",
        "expected_answer_points",
        "book_pages",
        "pdf_pages",
        "answerable",
        "expected_behavior_if_insufficient",
        "category",
    }
    for question in questions:
        missing = required - question.keys()
        if missing:
            raise ValueError(
                f"{question.get('id', 'unknown')} is missing fields: {sorted(missing)}"
            )
        if question["answerable"] and not question["book_pages"]:
            raise ValueError(
                f"{question['id']} is answerable but has no verified source pages."
            )
        if not question["answerable"] and question["book_pages"]:
            raise ValueError(
                f"{question['id']} is unanswerable but claims supporting source pages."
            )
        if question["answerable"] and len(question["book_pages"]) != len(question["pdf_pages"]):
            raise ValueError(
                f"{question['id']} must provide one verified PDF page for each book page."
            )
    return questions


def _empty_result(question: dict[str, Any], generate: bool) -> dict[str, Any]:
    return {
        "question_id": question["id"],
        "question": question["question"],
        "answerable": question["answerable"],
        "category": question["category"],
        "expected_answer_points": question["expected_answer_points"],
        "expected_behavior_if_insufficient": question[
            "expected_behavior_if_insufficient"
        ],
        "expected_book_pages": question["book_pages"],
        "expected_pdf_pages": question["pdf_pages"],
        "retrieved_top5_book_pages": [],
        "retrieved_top5_pdf_pages": [],
        "retrieved_top5_scores": [],
        "retrieved_sources": [],
        "app_retrieved_book_pages": [],
        "recall_at_5": None,
        "retrieval_success": False,
        "retrieval_latency_ms": None,
        "run_status": "pending",
        "result_status": "pending",
        "attempts": 0,
        "safety_route": "",
        "latency_ms": None,
        "latency_scope": "retrieval_plus_generation" if generate else "retrieval_only",
        "answer_text": "",
        "automatic_abstention": None,
        "answer_correctness_human": "",
        "citation_reviews": [],
        "abstention_review_human": "",
        "reviewer": "",
        "review_notes": "",
        "error": "",
    }


def run_evaluation(
    questions: list[dict[str, Any]],
    generate_answers: bool = False,
    top_k: int = 5,
    *,
    initial_results: list[dict[str, Any]] | None = None,
    limit: int | None = None,
    selected_question_ids: set[str] | None = None,
    on_update: Any = None,
    max_retries: int = 2,
    retry_base_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"Source PDF not found: {PDF_PATH}")
    provider = create_embedding_provider()
    chunks, vectors = load_index(
        INDEX_PATH,
        provider,
        expected_source_sha256=file_sha256(PDF_PATH),
        expected_chunking_config={
            "chunk_size_chars": CHUNK_SIZE_CHARS,
            "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
        },
    )
    previous = {
        record.get("question_id"): record
        for record in (initial_results or [])
        if isinstance(record, dict) and record.get("question_id")
    }
    results = [
        {**_empty_result(question, generate_answers), **previous.get(question["id"], {})}
        for question in questions
    ]
    for record in results:
        if (
            record.get("run_status") == "completed"
            and record.get("answer_text")
            and record.get("result_status") == "pending"
        ):
            record["result_status"] = "successful"
        record["embedding_provider"] = provider.identifier
    if on_update:
        on_update(results)

    successful_ids = {
        record["question_id"]
        for record in results
        if record.get("result_status") == "successful"
        or (
            record.get("run_status") == "completed"
            and record.get("latency_scope") == "retrieval_plus_generation"
            and bool(record.get("answer_text"))
        )
    }
    selected_indices = [
        index
        for index, record in enumerate(results)
        if record["question_id"] not in successful_ids
        and (
            selected_question_ids is None
            or record["question_id"] in selected_question_ids
        )
    ]
    if limit is not None:
        selected_indices = selected_indices[:limit]

    for index in selected_indices:
        question = questions[index]
        record = results[index]
        record.update(_empty_result(question, generate_answers))
        started = time.perf_counter()
        stop_after_failure = False
        for attempt in range(1, max_retries + 2):
            record["attempts"] = attempt
            try:
                safety_decision = assess_question(question["question"])
                if safety_decision.route is not Route.NORMAL:
                    record["safety_route"] = safety_decision.route.value
                    record["answer_text"] = safety_decision.response or ""
                    record["run_status"] = "completed"
                    record["result_status"] = "successful"
                    record["latency_ms"] = round(
                        (time.perf_counter() - started) * 1000, 2
                    )
                    record["latency_scope"] = "local_safety_route"
                    break

                ranked = rank_chunks(
                    question["question"], chunks, vectors, provider, top_k=top_k
                )
                retrieval_done = time.perf_counter()
                record["retrieval_success"] = True
                record["retrieval_latency_ms"] = round(
                    (retrieval_done - started) * 1000, 2
                )
                record["retrieved_top5_book_pages"] = [
                    passage["page_start"] for passage in ranked
                ]
                record["retrieved_top5_pdf_pages"] = [
                    passage.get("pdf_page_start") for passage in ranked
                ]
                record["retrieved_top5_scores"] = [
                    round(float(passage["similarity"]), 6) for passage in ranked
                ]
                if question["answerable"]:
                    record["recall_at_5"] = int(
                        any(
                            page in question["book_pages"]
                            for page in record["retrieved_top5_book_pages"]
                        )
                    )
                app_passages = [
                    passage
                    for passage in ranked[:RETRIEVAL_TOP_K]
                    if passage["similarity"] >= RETRIEVAL_MIN_SIMILARITY
                ]
                record["app_retrieved_book_pages"] = [
                    passage["page_start"] for passage in app_passages
                ]
                record["retrieved_sources"] = [
                    {
                        "chunk_id": passage.get("chunk_id"),
                        "source_filename": passage.get("source_filename"),
                        "book_page_start": passage.get("page_start"),
                        "book_page_end": passage.get("page_end"),
                        "pdf_page_start": passage.get("pdf_page_start"),
                        "pdf_page_end": passage.get("pdf_page_end"),
                        "similarity": round(float(passage["similarity"]), 6),
                    }
                    for passage in app_passages
                ]
                if not app_passages:
                    record["answer_text"] = (
                        "The available book does not provide enough relevant information "
                        "to answer this question."
                    )
                    record["automatic_abstention"] = True
                    record["latency_ms"] = record["retrieval_latency_ms"]
                elif generate_answers:
                    record["answer_text"] = generate_answer(
                        question["question"], app_passages
                    )
                    record["latency_ms"] = round(
                        (time.perf_counter() - started) * 1000, 2
                    )
                else:
                    record["latency_ms"] = record["retrieval_latency_ms"]
                record["run_status"] = "completed"
                record["result_status"] = "successful"
                break
            except (
                EmbeddingError,
                RetrievalError,
                AnswerGenerationError,
                UnsupportedQuestionError,
            ) as exc:
                record["run_status"] = "error"
                record["result_status"] = "failed"
                record["error"] = str(exc)[:400]
                if getattr(exc, "quota_exhausted", False):
                    stop_after_failure = True
                    break
                if getattr(exc, "retryable", False) and attempt <= max_retries:
                    time.sleep(retry_base_seconds * (2 ** (attempt - 1)))
                    continue
                break
            except Exception as exc:
                record["run_status"] = "error"
                record["result_status"] = "failed"
                api_key = getattr(provider, "_api_key", "")
                message = str(exc).replace(api_key, "[redacted]") if api_key else str(exc)
                record["error"] = f"{type(exc).__name__}: {message[:350]}"
                break
        else:
            record["run_status"] = "error"
            record["result_status"] = "failed"

        if on_update:
            on_update(results)
        if stop_after_failure:
            break
    return results


def write_results(
    records: list[dict[str, Any]],
    output_dir: Path = RESULTS_DIR,
    generate_answers: bool = False,
    top_k: int = 5,
    *,
    json_path: Path | None = None,
    csv_path: Path | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mode = "generated" if generate_answers else "retrieval"
    json_path = json_path or output_dir / f"evaluation_{timestamp}_{mode}.json"
    csv_path = csv_path or output_dir / f"evaluation_{timestamp}_{mode}.csv"
    status_counts = {
        status: sum(record.get("result_status") == status for record in records)
        for status in ("successful", "failed", "pending")
    }
    document = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "latency_scope": (
            "retrieval_plus_generation" if generate_answers else "retrieval_only"
        ),
        "source_pdf": PDF_PATH.name,
        "embedding_provider": records[0].get("embedding_provider") if records else None,
        "top_k": top_k,
        "status_counts": status_counts,
        "retrieval_threshold_for_app_behavior": RETRIEVAL_MIN_SIMILARITY,
        "target_metrics_are_not_results": True,
        "summary": summarize_results(records),
        "results": records,
    }
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    csv_tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    json_tmp.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with csv_tmp.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    **record,
                    "expected_book_pages": json.dumps(record["expected_book_pages"]),
                    "expected_pdf_pages": json.dumps(record["expected_pdf_pages"]),
                    "expected_answer_points": json.dumps(
                        record["expected_answer_points"], ensure_ascii=False
                    ),
                    "retrieved_top5_book_pages": json.dumps(
                        record["retrieved_top5_book_pages"]
                    ),
                    "retrieved_top5_pdf_pages": json.dumps(
                        record["retrieved_top5_pdf_pages"]
                    ),
                    "retrieved_top5_scores": json.dumps(
                        record["retrieved_top5_scores"]
                    ),
                    "retrieved_sources": json.dumps(
                        record["retrieved_sources"], ensure_ascii=False
                    ),
                    "app_retrieved_book_pages": json.dumps(
                        record["app_retrieved_book_pages"]
                    ),
                    "citation_reviews": json.dumps(
                        record["citation_reviews"], ensure_ascii=False
                    ),
                }
            )
    os.replace(json_tmp, json_path)
    os.replace(csv_tmp, csv_path)
    return json_path, csv_path


def _load_resume_results(path: Path, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read resume file '{path}': {exc}") from exc
    if document.get("mode") != "generated" or not isinstance(document.get("results"), list):
        raise ValueError("Resume file must be a generated evaluation JSON report.")
    known_ids = {question["id"] for question in questions}
    records = [
        row for row in document["results"]
        if isinstance(row, dict) and row.get("question_id") in known_ids
    ]
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        action="store_true",
        help=(
            "Also call Gemini answer generation for retrieved items. This sends the "
            "dataset questions and retrieved excerpts to Gemini and may incur API usage."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many pending questions (use --limit 3 for a pilot).",
    )
    parser.add_argument(
        "--question-ids",
        help="Comma-separated question IDs to process (for a representative pilot).",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        help="Resume a generated run from its JSON results file, updating that run in place.",
    )
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")
    if args.max_retries < 0:
        parser.error("--max-retries must be non-negative.")
    if args.resume_from and not args.generate:
        parser.error("--resume-from requires --generate.")
    try:
        questions = load_dataset()
        selected_ids = (
            {item.strip() for item in args.question_ids.split(",") if item.strip()}
            if args.question_ids else None
        )
        known_ids = {question["id"] for question in questions}
        if selected_ids is not None and not selected_ids:
            raise ValueError("--question-ids must include at least one question ID.")
        unknown_ids = (selected_ids or set()) - known_ids
        if unknown_ids:
            raise ValueError(f"Unknown question IDs: {', '.join(sorted(unknown_ids))}")
        initial_results = (
            _load_resume_results(args.resume_from, questions)
            if args.resume_from else None
        )
        if args.resume_from:
            json_path = args.resume_from
            csv_path = args.resume_from.with_suffix(".csv")
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            mode = "generated" if args.generate else "retrieval"
            json_path = args.output_dir / f"evaluation_{stamp}_{mode}.json"
            csv_path = args.output_dir / f"evaluation_{stamp}_{mode}.csv"

        def persist(records: list[dict[str, Any]]) -> None:
            write_results(
                records,
                args.output_dir,
                generate_answers=args.generate,
                top_k=args.top_k,
                json_path=json_path,
                csv_path=csv_path,
            )

        results = run_evaluation(
            questions,
            generate_answers=args.generate,
            top_k=args.top_k,
            initial_results=initial_results,
            limit=args.limit,
            selected_question_ids=selected_ids,
            on_update=persist,
            max_retries=args.max_retries,
        )
    except (ValueError, FileNotFoundError, EmbeddingError, RetrievalError) as exc:
        print(f"Evaluation could not start: {exc}")
        return 1
    summary = summarize_results(results)
    recall = summary["retrieval_recall_at_5"]
    latency = summary["latency"]
    statuses = {
        status: sum(record.get("result_status") == status for record in results)
        for status in ("successful", "failed", "pending")
    }
    print(
        f"Questions: {len(results)}; mode: "
        f"{'generated' if args.generate else 'retrieval-only'}; "
        f"successful: {statuses['successful']}; failed: {statuses['failed']}; "
        f"pending: {statuses['pending']}"
    )
    print(
        f"Recall@5: {recall['hits']}/{recall['eligible_denominator']} "
        f"({recall['rate'] if recall['rate'] is not None else 'not measured'})"
    )
    print(
        f"Successful runs: {latency['successful_runs']}; median latency: "
        f"{latency['median_ms'] if latency['median_ms'] is not None else 'not measured'} ms "
        f"({latency['scope']})"
    )
    print(
        "Review generated answers manually; unanswerable-question abstention "
        "is not auto-scored."
    )
    print(f"JSON results: {json_path}")
    print(f"CSV results: {csv_path}")
    return 0 if statuses["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
