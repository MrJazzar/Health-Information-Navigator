import pytest

import src.answer_generator as generator
from src.answer_generator import AnswerGenerationError, UnsupportedQuestionError


def test_unsupported_question_does_not_call_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generator, "_generate", lambda _: pytest.fail("must not generate"))
    with pytest.raises(UnsupportedQuestionError):
        generator.generate_answer("unrelated", [])


def test_missing_api_key_is_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generator, "GEMINI_API_KEY", "")
    monkeypatch.setattr(generator, "GEMINI_MODEL", "some-configured-model")
    with pytest.raises(AnswerGenerationError, match="GEMINI_API_KEY"):
        generator._client()


def test_generated_answer_citations_use_actual_retrieved_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        generator,
        "_generate",
        lambda _: "A supported point [Source: book, p. 5]. An unsupported cite [Source: book, p. 99].",
    )
    answer = generator.generate_answer(
        "question", [{"page_start": 5, "text": "source passage"}]
    )
    assert "p. 5" in answer
    assert "p. 99" not in answer


def test_simplified_answer_keeps_only_verified_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        generator,
        "_generate",
        lambda _: "Simpler wording [Source: book, p. 99], and page 99.",
    )
    answer = generator.simplify_answer(
        "Original [Source: book, p. 5]",
        [{"page_start": 5, "text": "source passage"}],
    )
    assert "p. 5" in answer
    assert "p. 99" not in answer
    assert "page 99" not in answer
