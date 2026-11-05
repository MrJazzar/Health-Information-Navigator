"""Question and answer operations shared by the HTTP backend."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from config import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    INDEX_PATH,
    PDF_PATH,
    RETRIEVAL_MIN_SIMILARITY,
    RETRIEVAL_TOP_K,
)
from src.answer_generator import (
    AnswerGenerationError,
    UnsupportedQuestionError,
    generate_answer,
    simplify_answer,
    suggest_alternative,
)
from src.embeddings import EmbeddingError, create_embedding_provider
from src.pdf_processor import PDFProcessingError
from src.retriever import RetrievalError, file_sha256, load_index, retrieve
from src.safety import Route, assess_question

NO_PASSAGES_MESSAGE = (
    "The available book does not provide enough relevant information to answer this "
    "question. Try asking in a different way, or consult a qualified professional or "
    "relevant official resource."
)


@lru_cache(maxsize=1)
def get_index():
    provider = create_embedding_provider()
    if not PDF_PATH.is_file():
        raise PDFProcessingError(f"Source PDF not found: {PDF_PATH}")
    chunks, vectors = load_index(
        INDEX_PATH,
        provider,
        expected_source_sha256=file_sha256(PDF_PATH),
        expected_chunking_config={
            "chunk_size_chars": CHUNK_SIZE_CHARS,
            "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
        },
    )
    return provider, chunks, vectors


def _retrieve(question: str) -> list[dict[str, Any]]:
    provider, chunks, vectors = get_index()
    return retrieve(
        question,
        chunks,
        vectors,
        provider,
        top_k=RETRIEVAL_TOP_K,
        min_similarity=RETRIEVAL_MIN_SIMILARITY,
    )


def answer_question(question: str) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("Enter a question to get started.")

    decision = assess_question(question)
    if decision.route != Route.NORMAL:
        return {
            "answer": decision.response or "",
            "passages": [],
            "safety_route": decision.route.value,
        }

    passages = _retrieve(question)
    if not passages:
        return {
            "answer": NO_PASSAGES_MESSAGE,
            "passages": [],
            "safety_route": None,
        }

    return {
        "answer": generate_answer(question, passages),
        "passages": passages,
        "safety_route": None,
    }


def answer_action(
    action: str,
    question: str,
    answer: str | None = None,
) -> str:
    if action not in {"simplify", "alternative"}:
        raise ValueError("Unsupported answer action.")
    if not question.strip():
        raise ValueError("Enter a question to get started.")
    if assess_question(question).route != Route.NORMAL:
        raise ValueError(
            "Answer controls are unavailable for safety-routed questions. "
            "Submit the question through the main question endpoint."
        )
    passages = _retrieve(question)
    if not passages:
        raise UnsupportedQuestionError(NO_PASSAGES_MESSAGE)
    if action == "simplify":
        if not answer or not answer.strip():
            raise ValueError("An answer is required to simplify.")
        return simplify_answer(answer, passages)
    return suggest_alternative(question, passages)


def public_error_message(error: Exception) -> tuple[str, str]:
    if isinstance(error, ValueError):
        return "invalid_action", str(error)
    if isinstance(error, (AnswerGenerationError, EmbeddingError)):
        return (
            "model_unavailable",
            "The Gemini service could not complete this request. Check the local "
            "Gemini settings and service, then retry.",
        )
    if isinstance(error, RetrievalError):
        return (
            "index_unavailable",
            "The local source index could not be used. Retry; if the problem continues, "
            "rebuild it with `python scripts/build_index.py`.",
        )
    if isinstance(error, PDFProcessingError):
        return (
            "source_unavailable",
            "The source PDF could not be read. Check the configured PDF, then retry.",
        )
    if isinstance(error, UnsupportedQuestionError):
        return "unsupported_question", NO_PASSAGES_MESSAGE
    return "backend_error", "A temporary problem prevented this request. Please retry."
