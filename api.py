"""HTTP API for Mental Health Navigator's Python backend."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.answer_generator import AnswerGenerationError, UnsupportedQuestionError
from src.backend_service import (
    answer_action,
    answer_question,
    public_error_message,
)
from src.embeddings import EmbeddingError
from src.pdf_processor import PDFProcessingError
from src.retriever import RetrievalError

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Mental Health Navigator API",
    description="Local API for safety-first, source-grounded educational answers.",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1500)


class ActionRequest(QuestionRequest):
    action: Literal["simplify", "alternative"]
    answer: str | None = Field(default=None, max_length=12000)


class Passage(BaseModel):
    source_filename: str
    page_start: int | str
    pdf_page_start: int | str | None = None
    similarity: float
    text: str


class AnswerResponse(BaseModel):
    answer: str
    passages: list[Passage]
    safety_route: str | None


class ActionResponse(BaseModel):
    answer: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


def _raise_public_error(error: Exception) -> None:
    code, message = public_error_message(error)
    logger.warning("Backend request failed (%s): %s", code, type(error).__name__)
    status_code = 422 if code in {"unsupported_question", "invalid_action"} else 503
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    ) from error


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest) -> dict[str, Any]:
    if not request.question.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "empty_question", "message": "Enter a question to get started."},
        )
    try:
        return answer_question(request.question)
    except (
        AnswerGenerationError,
        EmbeddingError,
        PDFProcessingError,
        RetrievalError,
        UnsupportedQuestionError,
        OSError,
    ) as error:
        _raise_public_error(error)


@app.post("/api/action", response_model=ActionResponse)
def action(request: ActionRequest) -> ActionResponse:
    if not request.question.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "empty_question", "message": "Enter a question to get started."},
        )
    try:
        answer = answer_action(request.action, request.question, request.answer)
    except (
        AnswerGenerationError,
        EmbeddingError,
        PDFProcessingError,
        RetrievalError,
        UnsupportedQuestionError,
        ValueError,
        OSError,
    ) as error:
        _raise_public_error(error)
    return ActionResponse(answer=answer)
