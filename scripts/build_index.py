from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    CHUNKS_PATH,
    EXTRACTION_REPORT_PATH,
    EXTRACTED_TEXT_PATH,
    INDEX_PATH,
    PDF_PATH,
)
from src.chunking import chunk_pages
from src.embeddings import EmbeddingError, create_embedding_provider
from src.pdf_processor import PDFProcessingError, extract_pdf
from src.retriever import file_sha256, save_index


def main() -> int:
    try:
        pages, report = extract_pdf(PDF_PATH, EXTRACTION_REPORT_PATH, EXTRACTED_TEXT_PATH)
        chunks = chunk_pages(
            pages,
            PDF_PATH.name,
            chunk_size_chars=CHUNK_SIZE_CHARS,
            overlap_chars=CHUNK_OVERLAP_CHARS,
        )
        if not chunks:
            raise PDFProcessingError("No non-empty text chunks could be created from the PDF.")
        provider = create_embedding_provider()
        vectors = provider.embed_documents([chunk["text"] for chunk in chunks])
        save_index(
            INDEX_PATH,
            chunks,
            vectors,
            file_sha256(PDF_PATH),
            provider.identifier,
            {
                "chunk_size_chars": CHUNK_SIZE_CHARS,
                "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
            },
        )
        CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CHUNKS_PATH.open("w", encoding="utf-8") as output:
            for chunk in chunks:
                output.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    except (PDFProcessingError, EmbeddingError, OSError, ValueError) as exc:
        print(f"Index build failed: {exc}")
        return 1
    print(
        f"Indexed {len(chunks)} chunks from {report['page_count']} pages "
        f"using {provider.identifier}."
    )
    print(f"Index: {INDEX_PATH}")
    print(f"Readable chunks: {CHUNKS_PATH}")
    if report["warning"]:
        print(f"WARNING: {report['warning']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
