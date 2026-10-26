"""Replaceable local and Gemini embedding providers."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np

from config import (
    EMBEDDING_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
)
from src.gemini_errors import GeminiRequestError, classify_api_error

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class EmbeddingError(GeminiRequestError):
    """Raised when a configured embedding provider cannot embed text."""


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def identifier(self) -> str:
        """Stable identifier used to invalidate incompatible persisted vectors."""

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Return one vector per input, with a consistent vector size."""

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self.embed_texts(texts)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])


class LocalHashEmbedding(EmbeddingProvider):
    """Small deterministic feature-hash vectors; requires no downloaded model."""

    def __init__(self, dimensions: int = 1024) -> None:
        if dimensions < 32:
            raise ValueError("dimensions must be at least 32.")
        self.dimensions = dimensions

    @property
    def identifier(self) -> str:
        return f"local-hash-v1-{self.dimensions}"

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = _TOKEN_PATTERN.findall(text.casefold())
            features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
            for feature in features:
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
                value = int.from_bytes(digest, "little")
                index = value % self.dimensions
                sign = 1.0 if (value >> 16) & 1 else -1.0
                vectors[row, index] += sign
        return normalize_rows(vectors)


class GeminiEmbedding(EmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key or api_key.casefold().startswith("your_"):
            raise EmbeddingError("GEMINI_API_KEY is required for Gemini embeddings.")
        if not model or model.casefold().startswith("your_"):
            raise EmbeddingError(
                "Set GEMINI_EMBEDDING_MODEL to an embedding model supported by your API account."
            )
        try:
            from google import genai

            self._client = genai.Client(api_key=api_key)
        except Exception as exc:
            raise EmbeddingError(f"Could not initialize Gemini embeddings: {exc}") from exc
        self._api_key = api_key
        self._model = model

    @property
    def identifier(self) -> str:
        return f"gemini:{self._model}:task-format-v1"

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        vectors: list[list[float]] = []
        try:
            for text in texts:
                response = self._client.models.embed_content(
                    model=self._model, contents=text
                )
                embeddings = getattr(response, "embeddings", None)
                if not embeddings or len(embeddings) != 1:
                    raise EmbeddingError(
                        "Gemini did not return exactly one vector for an input text."
                    )
                vectors.append(list(embeddings[0].values))
        except EmbeddingError:
            raise
        except Exception as exc:
            message = str(exc).replace(self._api_key, "[redacted]")
            retryable, quota_exhausted = classify_api_error(exc)
            if quota_exhausted:
                safe_message = (
                    "Gemini embedding quota appears exhausted; evaluation paused "
                    "without retrying."
                )
            else:
                safe_message = f"Gemini embedding request failed: {message[:300]}"
            raise EmbeddingError(
                safe_message,
                retryable=retryable,
                quota_exhausted=quota_exhausted,
            ) from exc
        result = np.asarray(vectors, dtype=np.float32)
        if result.shape[0] != len(texts):
            raise EmbeddingError("Gemini returned an incomplete embedding result.")
        return normalize_rows(result)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        formatted = [f"title: none | text: {text}" for text in texts]
        return self.embed_texts(formatted)

    def embed_query(self, query: str) -> np.ndarray:
        formatted = f"task: question answering | query: {query}"
        return self.embed_texts([formatted])


def normalize_rows(vectors: np.ndarray) -> np.ndarray:
    if vectors.ndim != 2:
        raise ValueError("Embedding matrix must be two-dimensional.")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms != 0)


def create_embedding_provider() -> EmbeddingProvider:
    if EMBEDDING_PROVIDER == "local":
        return LocalHashEmbedding()
    if EMBEDDING_PROVIDER == "gemini":
        return GeminiEmbedding(GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL)
    raise EmbeddingError(
        "EMBEDDING_PROVIDER must be 'local' or 'gemini'."
    )
