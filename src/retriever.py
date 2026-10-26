"""Cosine-similarity retrieval and validated local index persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.embeddings import EmbeddingProvider, normalize_rows

INDEX_VERSION = 1


class RetrievalError(RuntimeError):
    """Raised for unavailable, malformed, or incompatible retrieval indexes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_index(
    index_path: Path,
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    source_sha256: str,
    embedding_id: str,
    chunking_config: dict[str, int] | None = None,
) -> None:
    if len(chunks) != embeddings.shape[0]:
        raise RetrievalError("Chunk and embedding counts do not match.")
    if embeddings.ndim != 2 or not np.isfinite(embeddings).all():
        raise RetrievalError("Embedding matrix is malformed.")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": INDEX_VERSION,
        "source_sha256": source_sha256,
        "embedding_id": embedding_id,
        "chunking_config": chunking_config or {},
        "chunks": chunks,
        "embeddings": normalize_rows(embeddings).tolist(),
    }
    temporary = index_path.with_suffix(index_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(index_path)


def load_index(
    index_path: Path,
    provider: EmbeddingProvider,
    expected_source_sha256: str | None = None,
    expected_chunking_config: dict[str, int] | None = None,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    if not index_path.is_file():
        raise RetrievalError(
            f"Retrieval index is missing: {index_path}. Run scripts/build_index.py."
        )
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        chunks = payload["chunks"]
        embeddings = np.asarray(payload["embeddings"], dtype=np.float32)
        if payload["version"] != INDEX_VERSION:
            raise RetrievalError("Stored index version is unsupported; rebuild the index.")
        if payload["embedding_id"] != provider.identifier:
            raise RetrievalError("Embedding configuration changed; rebuild the index.")
        if expected_source_sha256 and payload["source_sha256"] != expected_source_sha256:
            raise RetrievalError("Source PDF changed; rebuild the index.")
        if (
            expected_chunking_config is not None
            and payload.get("chunking_config") != expected_chunking_config
        ):
            raise RetrievalError("Chunking configuration changed; rebuild the index.")
        if not isinstance(chunks, list) or not chunks:
            raise RetrievalError("Stored index contains no chunks; rebuild the index.")
        if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
            raise RetrievalError("Stored index vectors do not match the chunks.")
        if not np.isfinite(embeddings).all():
            raise RetrievalError("Stored index contains invalid vector values.")
        for chunk in chunks:
            if not all(
                key in chunk
                for key in ("chunk_id", "source_filename", "page_start", "page_end", "text")
            ):
                raise RetrievalError("Stored index has malformed chunk metadata.")
        return chunks, normalize_rows(embeddings)
    except RetrievalError:
        raise
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RetrievalError(f"Could not read stored index: {exc}") from exc


def retrieve(
    query: str,
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    provider: EmbeddingProvider,
    top_k: int = 3,
    min_similarity: float = 0.08,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    if not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between 0 and 1.")
    ranked = rank_chunks(query, chunks, embeddings, provider, top_k)
    return [
        result
        for result in ranked
        if float(result["similarity"]) >= min_similarity
    ]


def rank_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    provider: EmbeddingProvider,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return the unthresholded top-k rankings for evaluation and diagnostics."""
    if not query.strip():
        return []
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    if not chunks or embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
        raise RetrievalError("Chunks and stored embeddings are inconsistent.")
    query_vector = provider.embed_query(query)
    if query_vector.shape[1] != embeddings.shape[1]:
        raise RetrievalError("Query and index embedding dimensions do not match.")
    scores = normalize_rows(embeddings) @ normalize_rows(query_vector)[0]
    ranked = np.argsort(-scores)[:top_k]
    return [
        {**chunks[int(index)], "similarity": float(scores[int(index)])}
        for index in ranked
    ]
