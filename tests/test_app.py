from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import app
from src.backend_client import BackendClientError
from src.safety import Route


def test_greeting_and_quick_replies_render() -> None:
    app_test = AppTest.from_file(str(Path(app.__file__).resolve()))
    app_test.session_state["answer"] = "Grounded answer."
    app_test.session_state["question"] = "How can a student support a peer?"
    app_test.session_state["passages"] = [
        {
            "source_filename": "book.pdf",
            "page_start": 5,
            "pdf_page_start": 7,
            "similarity": 0.9,
            "text": "A source passage.",
        }
    ]

    app_test.run()

    assert not app_test.exception
    assert any(
        "Hi, I'm the Mental Health Navigator" in item.value
        and "BCcampus's Starting a Conversation About Mental Health" in item.value
        for item in app_test.markdown
    )
    labels = {item.label for item in app_test.button}
    assert {
        "Simplify Answer",
        "Suggest an Alternative",
        "Show Sources",
        "Helpful",
        "Not Helpful",
        "Report an Issue",
    } <= labels


def test_retry_button_renders_after_a_request_failure() -> None:
    app_test = AppTest.from_file(str(Path(app.__file__).resolve()))
    app_test.session_state["question"] = "How can a student support a peer?"
    app_test.session_state["answer"] = app.REQUEST_FAILURE_MESSAGE
    app_test.session_state["passages"] = []
    app_test.session_state["request_error"] = "The local source index could not be used."

    app_test.run()

    assert not app_test.exception
    assert "Retry" in {item.label for item in app_test.button}


def test_show_sources_toggle_changes_visibility_state() -> None:
    state: dict[str, object] = {}

    app._toggle_sources(state)
    assert state["show_sources"] is True

    app._toggle_sources(state)
    assert state["show_sources"] is False


def test_safety_route_from_backend_is_shown_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda _: {
            "answer": "Contact local emergency services.",
            "passages": [],
            "safety_route": Route.URGENT_SUPPORT.value,
        },
    )
    state: dict[str, object] = {}

    app._process_question("I want to die.", state)

    assert state["safety_route"] == Route.URGENT_SUPPORT.value
    assert "local emergency services" in str(state["answer"])


def test_contact_detail_route_from_backend_is_shown_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda _: {
            "answer": "Please remove contact details; this was not sent to Gemini.",
            "passages": [],
            "safety_route": Route.PRIVACY_PROTECTION.value,
        },
    )
    state: dict[str, object] = {}

    app._process_question("Email me at student@example.edu", state)

    assert state["safety_route"] == Route.PRIVACY_PROTECTION.value
    assert "not sent to Gemini" in str(state["answer"])


def test_backend_error_has_retry_message_and_retry_can_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def ask_backend(_question: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise BackendClientError("The local source index could not be used. Retry.")
        return {
            "answer": "Grounded answer.",
            "passages": [{"page_start": 5, "text": "A source passage."}],
            "safety_route": None,
        }

    monkeypatch.setattr(app, "ask_backend", ask_backend)
    state: dict[str, object] = {}

    app._process_question("How can a student support a peer?", state)

    assert "source index could not be used" in state["request_error"]
    assert "try again" in state["answer"].lower()

    app._process_question(state["question"], state)

    assert state["answer"] == "Grounded answer."
    assert state["passages"] == [{"page_start": 5, "text": "A source passage."}]
    assert "request_error" not in state


def test_unavailable_backend_error_can_be_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda _: (_ for _ in ()).throw(
            BackendClientError("The Gemini service could not complete this request.")
        ),
    )
    state: dict[str, object] = {}

    app._process_question("How can a student support a peer?", state)

    assert "Gemini service" in state["request_error"]
    assert "try again" in state["answer"].lower()
    assert "official mental health support resource" in state["answer"]
    assert "does not provide diagnosis, treatment, or emergency assistance" in state["answer"]

    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda _: {
            "answer": "Grounded answer.",
            "passages": [{"page_start": 5, "text": "A source passage."}],
            "safety_route": None,
        },
    )
    app._process_question(state["question"], state)

    assert state["answer"] == "Grounded answer."
    assert "request_error" not in state


def test_empty_retrieval_shows_fallback_without_generating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda _: {
            "answer": "The available book does not provide enough relevant information.",
            "passages": [],
            "safety_route": None,
        },
    )
    state: dict[str, object] = {}

    app._process_question("How can a student support a peer?", state)

    assert "not provide enough relevant information" in state["answer"]
    assert state["passages"] == []


def test_empty_question_does_not_access_index_or_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app,
        "ask_backend",
        lambda *_: pytest.fail("empty input must not call the backend"),
    )
    state: dict[str, object] = {}

    app._process_question("  ", state)

    assert state["question"] == ""
    assert "answer" not in state