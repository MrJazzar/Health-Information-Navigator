from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from config import CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS
from evaluation import run_evaluation as evaluation_runner
from evaluation.metrics import summarize_results
from evaluation.run_evaluation import load_dataset
from evaluation.run_safety_tests import load_cases, run_cases
from evaluation.score_results import score_file
from src.answer_generator import AnswerGenerationError
from src.embeddings import EmbeddingProvider
from src.gemini_errors import classify_api_error


def test_evaluation_dataset_has_twenty_questions_with_verified_chunk_pages() -> None:
    questions = load_dataset()
    assert len(questions) == 20
    assert len({item["id"] for item in questions}) == 20

    chunks = [
        json.loads(line)
        for line in Path("storage/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    page_pairs = {
        (chunk["page_start"], chunk.get("pdf_page_start")) for chunk in chunks
    }
    for question in questions:
        if question["answerable"]:
            assert len(question["book_pages"]) == len(question["pdf_pages"])
            for book_page, pdf_page in zip(question["book_pages"], question["pdf_pages"]):
                assert (book_page, pdf_page) in page_pairs, question["id"]


def configure_mocked_generated_run(monkeypatch, tmp_path: Path) -> None:
    class FakeProvider(EmbeddingProvider):
        @property
        def identifier(self) -> str:
            return "test-vector"

        def embed_texts(self, texts):
            return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)

    source_pdf = tmp_path / "source.pdf"
    source_pdf.touch()
    ranked = [
        {
            "chunk_id": "test-chunk",
            "source_filename": "book.pdf",
            "page_start": 59,
            "page_end": 59,
            "pdf_page_start": 66,
            "pdf_page_end": 66,
            "text": "A source excerpt.",
            "similarity": 0.9,
        }
    ]
    monkeypatch.setattr(evaluation_runner, "PDF_PATH", source_pdf)
    monkeypatch.setattr(evaluation_runner, "create_embedding_provider", FakeProvider)
    monkeypatch.setattr(evaluation_runner, "file_sha256", lambda _: "source-hash")
    monkeypatch.setattr(
        evaluation_runner,
        "load_index",
        lambda *args, **kwargs: (
            [{"chunk_id": "test-chunk"}],
            np.asarray([[1.0, 0.0]], dtype=np.float32),
        ),
    )
    monkeypatch.setattr(evaluation_runner, "rank_chunks", lambda *args, **kwargs: ranked)


def test_generated_runner_retries_and_persists_each_result(
    monkeypatch, tmp_path: Path
) -> None:
    configure_mocked_generated_run(monkeypatch, tmp_path)
    monkeypatch.setattr(evaluation_runner.time, "sleep", lambda _: None)
    calls = []

    def fake_generate(question, passages):
        calls.append(question)
        if len(calls) < 3:
            raise AnswerGenerationError("temporary failure", retryable=True)
        return "Generated test answer."

    monkeypatch.setattr(evaluation_runner, "generate_answer", fake_generate)
    updates = []
    result = evaluation_runner.run_evaluation(
        [load_dataset()[0]],
        generate_answers=True,
        on_update=lambda records: updates.append(records[0]["result_status"]),
    )[0]

    assert len(calls) == 3
    assert result["result_status"] == "successful"
    assert result["answer_text"] == "Generated test answer."
    assert result["attempts"] == 3
    assert result["retrieved_sources"][0]["pdf_page_start"] == 66
    assert updates == ["pending", "successful"]


def test_generated_runner_resumes_success_and_stops_on_quota(
    monkeypatch, tmp_path: Path
) -> None:
    configure_mocked_generated_run(monkeypatch, tmp_path)
    questions = load_dataset()[:2]
    previous = evaluation_runner._empty_result(questions[0], generate=True)
    previous.update(
        {
            "run_status": "completed",
            "result_status": "successful",
            "answer_text": "Previously saved response.",
        }
    )
    calls = []

    def quota_failure(question, passages):
        calls.append(question)
        raise AnswerGenerationError(
            "Gemini quota exhausted.",
            quota_exhausted=True,
        )

    monkeypatch.setattr(evaluation_runner, "generate_answer", quota_failure)
    results = evaluation_runner.run_evaluation(
        questions,
        generate_answers=True,
        initial_results=[previous],
        retry_base_seconds=0,
    )

    assert len(calls) == 1
    assert results[0]["answer_text"] == "Previously saved response."
    assert results[0]["result_status"] == "successful"
    assert results[1]["result_status"] == "failed"
    assert results[1]["attempts"] == 1


def test_generated_result_writer_tracks_pending_failed_and_successful(
    tmp_path: Path,
) -> None:
    records = [
        {
            **evaluation_runner._empty_result(question, generate=True),
            "result_status": status,
        }
        for question, status in zip(load_dataset()[:3], ("successful", "failed", "pending"))
    ]
    json_path, csv_path = evaluation_runner.write_results(
        records, tmp_path, generate_answers=True
    )

    document = json.loads(json_path.read_text(encoding="utf-8"))
    assert document["status_counts"] == {
        "successful": 1,
        "failed": 1,
        "pending": 1,
    }
    assert "retrieved_sources" in csv_path.read_text(encoding="utf-8-sig").splitlines()[0]


def test_gemini_api_error_classification_distinguishes_quota_and_transients() -> None:
    class FakeApiError(Exception):
        def __init__(self, code, message, status=""):
            super().__init__(message)
            self.code = code
            self.status = status

    assert classify_api_error(
        FakeApiError(429, "Rate limit reached; too many requests")
    ) == (True, False)
    assert classify_api_error(
        FakeApiError(429, "RESOURCE_EXHAUSTED: quota exceeded")
    ) == (False, True)
    assert classify_api_error(FakeApiError(503, "Service unavailable")) == (True, False)


def test_retrieval_evaluator_reports_missing_pdf(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(evaluation_runner, "PDF_PATH", tmp_path / "missing.pdf")
    with pytest.raises(FileNotFoundError, match="Source PDF not found"):
        evaluation_runner.run_evaluation(load_dataset())


def test_retrieval_evaluator_computes_recall_without_generation(
    monkeypatch, tmp_path: Path
) -> None:
    class FakeProvider(EmbeddingProvider):
        @property
        def identifier(self) -> str:
            return "test-vector"

        def embed_texts(self, texts):
            return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)

    source_pdf = tmp_path / "source.pdf"
    source_pdf.touch()
    chunks = [
        {
            "chunk_id": "relevant",
            "source_filename": "book.pdf",
            "page_start": 75,
            "page_end": 75,
            "pdf_page_start": 82,
            "pdf_page_end": 82,
            "text": "Listen empathetically.",
        },
        {
            "chunk_id": "other",
            "source_filename": "book.pdf",
            "page_start": 10,
            "page_end": 10,
            "pdf_page_start": 17,
            "pdf_page_end": 17,
            "text": "Unrelated passage.",
        },
    ]
    monkeypatch.setattr(evaluation_runner, "PDF_PATH", source_pdf)
    monkeypatch.setattr(evaluation_runner, "create_embedding_provider", FakeProvider)
    monkeypatch.setattr(evaluation_runner, "file_sha256", lambda _: "source-hash")
    monkeypatch.setattr(
        evaluation_runner,
        "load_index",
        lambda *args, **kwargs: (
            chunks,
            np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        ),
    )
    sample = load_dataset()[8]

    result = evaluation_runner.run_evaluation([sample], generate_answers=False)[0]

    assert result["recall_at_5"] == 1
    assert result["retrieved_top5_book_pages"][0] == 75
    assert result["app_retrieved_book_pages"][0] == 75
    assert result["run_status"] == "completed"
    assert result["answer_text"] == ""
    assert result["latency_scope"] == "retrieval_only"


def test_safety_runner_checks_expected_routes_and_manual_review() -> None:
    results = run_cases(load_cases())
    assert len(results) >= 10
    assert all(result["route_check_passed"] for result in results)
    assert any(result["status"] == "NEEDS MANUAL REVIEW" for result in results)
    assert any(result["status"] == "PASS" for result in results)


def test_aggregate_metrics_use_actual_denominators_and_human_labels() -> None:
    records = [
        {
            "answerable": True,
            "expected_book_pages": [75],
            "retrieval_success": True,
            "recall_at_5": 1,
            "answer_correctness_human": 1,
            "citation_reviews": [
                {"supported": True},
                {"supported": False},
            ],
            "latency_ms": 100.0,
            "run_status": "completed",
            "latency_scope": "retrieval_only",
        },
        {
            "answerable": True,
            "expected_book_pages": [76],
            "retrieval_success": True,
            "recall_at_5": 0,
            "answer_correctness_human": "",
            "citation_reviews": [],
            "latency_ms": 300.0,
            "run_status": "completed",
            "latency_scope": "retrieval_only",
        },
        {
            "answerable": False,
            "expected_book_pages": [],
            "retrieval_success": True,
            "automatic_abstention": True,
            "safety_route": "",
            "app_retrieved_book_pages": [],
            "abstention_review_human": 1,
            "latency_ms": None,
            "run_status": "retrieval_only",
            "latency_scope": "retrieval_only",
        },
    ]

    summary = summarize_results(records)

    assert summary["retrieval_recall_at_5"] == {
        "hits": 1,
        "eligible_denominator": 2,
        "rate": 0.5,
        "measurement": "automated against manually verified expected source pages",
    }
    assert summary["answer_correctness"]["rate"] == 1.0
    assert summary["citation_support_rate"]["rate"] == 0.5
    assert summary["abstention_quality"]["automatic_source_empty_abstentions"] == 1
    assert summary["latency"]["median_ms"] == 200.0


def test_score_results_reads_annotated_csv(tmp_path: Path) -> None:
    path = tmp_path / "annotated.csv"
    path.write_text(
        "answerable,expected_book_pages,retrieval_success,recall_at_5,"
        "answer_correctness_human,citation_reviews,abstention_review_human,"
        "run_status,latency_ms,latency_scope\n"
        'true,"[75]",true,1,1,"[{""supported"": true}]",,completed,120,retrieval_only\n',
        encoding="utf-8",
    )

    report = score_file(path)

    assert report["reviewed_results"] == 1
    assert report["summary"]["answer_correctness"]["rate"] == 1.0
    assert report["summary"]["citation_support_rate"]["rate"] == 1.0
