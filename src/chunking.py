"""Sentence-aware, page-preserving text chunking."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from src.pdf_processor import PageText

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


def _split_long_sentence(sentence: str, limit: int) -> list[str]:
    words = sentence.split()
    result: list[str] = []
    current: list[str] = []
    size = 0
    for word in words:
        added = len(word) + (1 if current else 0)
        if current and size + added > limit:
            result.append(" ".join(current))
            current = []
            size = 0
        current.append(word)
        size += len(word) + (1 if len(current) > 1 else 0)
    if current:
        result.append(" ".join(current))
    return result


def chunk_pages(
    pages: list[PageText],
    source_filename: str,
    chunk_size_chars: int = 2600,
    overlap_chars: int = 400,
) -> list[dict[str, Any]]:
    if chunk_size_chars < 1:
        raise ValueError("chunk_size_chars must be positive.")
    if overlap_chars < 0 or overlap_chars >= chunk_size_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than chunk size.")

    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        sentences: list[str] = []
        for sentence in _SENTENCE_BOUNDARY.split(text):
            sentence = " ".join(sentence.split())
            if sentence:
                sentences.extend(_split_long_sentence(sentence, chunk_size_chars))
        if not sentences:
            continue

        start = 0
        while start < len(sentences):
            end = start
            current: list[str] = []
            char_count = 0
            while end < len(sentences):
                sentence = sentences[end]
                added = len(sentence) + (1 if current else 0)
                if current and char_count + added > chunk_size_chars:
                    break
                current.append(sentence)
                char_count += added
                end += 1
            body = " ".join(current).strip()
            normalized = " ".join(body.casefold().split())
            if body and normalized not in seen:
                seen.add(normalized)
                chunks.append(
                    {
                        "chunk_id": f"chunk-{len(chunks) + 1:05d}",
                        "source_filename": source_filename,
                        "page_start": page.page_label or page.page_number,
                        "page_end": page.page_label or page.page_number,
                        "pdf_page_start": page.page_number,
                        "pdf_page_end": page.page_number,
                        "text": body,
                    }
                )
            if end >= len(sentences):
                break
            overlap_size = 0
            next_start = end
            while next_start > start and overlap_size < overlap_chars:
                next_start -= 1
                overlap_size += len(sentences[next_start]) + 1
            start = max(start + 1, next_start)
    return chunks


def chunk_fingerprint(chunks: list[dict[str, Any]]) -> str:
    content = "\n".join(
        f"{chunk['source_filename']}|{chunk['page_start']}|{chunk['text']}"
        for chunk in chunks
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
