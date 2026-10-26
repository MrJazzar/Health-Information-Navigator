from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.embeddings import GeminiEmbedding, LocalHashEmbedding
from src.retriever import RetrievalError, load_index, retrieve, save_index


def test_cosine_ranking_and_similarity_threshold() -> None:
    provider = LocalHashEmbedding(dimensions=128)
    chunks = [
        {
            "chunk_id": "one",
            "source_filename": "book.pdf",
            "page_start": 4,
            "page_end": 4,
            "text": "Students can listen actively and support a peer.",
        },
        {
            "chunk_id": "two",
            "source_filename": "book.pdf",
            "page_start": 8,
            "page_end": 8,
            "text": "The campus library offers research resources.",
        },
    ]
    vectors = provider.embed_texts([chunk["text"] for chunk in chunks])

    results = retrieve("listen and support a peer", chunks, vectors, provider, 2, 0.01)
    assert results[0]["chunk_id"] == "one"
    assert 0 <= results[0]["similarity"] <= 1
    assert retrieve("listen and support a peer", chunks, vectors, provider, 2, 0.99) == []


def test_index_round_trip_and_staleness(tmp_path: Path) -> None:
    provider = LocalHashEmbedding()
    chunks = [
        {
            "chunk_id": "one",
            "source_filename": "book.pdf",
            "page_start": 2,
            "page_end": 2,
            "text": "Source text.",
        }
    ]
    vectors = provider.embed_texts([chunks[0]["text"]])
    path = tmp_path / "index.json"
    chunking_config = {"chunk_size_chars": 200, "chunk_overlap_chars": 20}
    save_index(
        path, chunks, vectors, "source-hash", provider.identifier, chunking_config
    )

    loaded_chunks, loaded_vectors = load_index(
        path, provider, "source-hash", chunking_config
    )
    assert loaded_chunks == chunks
    assert loaded_vectors.shape == vectors.shape
    with pytest.raises(RetrievalError, match="Source PDF changed"):
        load_index(path, provider, "different-hash")
    with pytest.raises(RetrievalError, match="Chunking configuration changed"):
        load_index(path, provider, "source-hash", {"chunk_size_chars": 300})


def test_malformed_stored_index_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RetrievalError, match="Could not read stored index"):
        load_index(path, LocalHashEmbedding())


def test_gemini_embeddings_format_retrieval_tasks() -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.calls = []

        def embed_content(self, *, model: str, contents: str):
            self.calls.append((model, contents))
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[1.0, 2.0])]
            )

    fake_models = FakeModels()
    provider = GeminiEmbedding.__new__(GeminiEmbedding)
    provider._client = SimpleNamespace(models=fake_models)
    provider._model = "gemini-embedding-2"

    document_vectors = provider.embed_documents(["passage one", "passage two"])
    query_vector = provider.embed_query("a student question")

    assert fake_models.calls[0] == (
        "gemini-embedding-2",
        "title: none | text: passage one",
    )
    assert fake_models.calls[1] == (
        "gemini-embedding-2",
        "title: none | text: passage two",
    )
    assert fake_models.calls[2] == (
        "gemini-embedding-2",
        "task: question answering | query: a student question",
    )
    assert document_vectors.shape == (2, 2)
    assert query_vector.shape == (1, 2)


def test_gemini_embedding_returns_one_vector_per_request() -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.request_count = 0

        def embed_content(self, *, model: str, contents: str):
            self.request_count += 1
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[1.0, 0.0])]
            )

    fake_models = FakeModels()
    provider = GeminiEmbedding.__new__(GeminiEmbedding)
    provider._client = SimpleNamespace(models=fake_models)
    provider._model = "gemini-embedding-2"

    vectors = provider.embed_texts([f"text {index}" for index in range(3)])

    assert fake_models.request_count == 3
    assert vectors.shape == (3, 2)
