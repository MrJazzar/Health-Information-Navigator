from src.chunking import chunk_pages
from src.pdf_processor import PageText


def test_chunks_respect_page_metadata_and_overlap() -> None:
    pages = [
        PageText(
            7,
            "Alpha beta gamma. Delta epsilon zeta. Eta theta iota. Kappa lambda mu.",
        )
    ]
    chunks = chunk_pages(
        pages, "book.pdf", chunk_size_chars=42, overlap_chars=10
    )

    assert len(chunks) > 1
    assert all(chunk["page_start"] == 7 and chunk["page_end"] == 7 for chunk in chunks)
    assert all(chunk["source_filename"] == "book.pdf" for chunk in chunks)
    assert chunks[0]["text"].split()[-1] in chunks[1]["text"]
    assert all(chunk["text"].strip() for chunk in chunks)


def test_empty_and_duplicate_page_content_is_not_added_twice() -> None:
    pages = [
        PageText(1, ""),
        PageText(2, "Repeated sentence."),
        PageText(3, "Repeated sentence."),
    ]

    chunks = chunk_pages(pages, "book.pdf", 100, 10)

    assert len(chunks) == 1
    assert chunks[0]["page_start"] == 2


def test_invalid_overlap_is_rejected() -> None:
    try:
        chunk_pages([PageText(1, "Text.")], "book.pdf", 10, 10)
    except ValueError as exc:
        assert "smaller than chunk size" in str(exc)
    else:
        raise AssertionError("Expected invalid overlap to fail.")
