from fastapi.testclient import TestClient

import api
from src.answer_generator import AnswerGenerationError
from src.retriever import RetrievalError

client = TestClient(api.app)


def test_health_endpoint_reports_backend_ready() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_endpoint_returns_answer_and_source_metadata(monkeypatch) -> None:
    expected = {
        "answer": "Grounded answer.",
        "passages": [
            {
                "source_filename": "book.pdf",
                "page_start": 5,
                "pdf_page_start": 7,
                "similarity": 0.9,
                "text": "A source passage.",
            }
        ],
        "safety_route": None,
    }
    monkeypatch.setattr(api, "answer_question", lambda _: expected)

    response = client.post(
        "/api/ask",
        json={"question": "How can a student support a peer?"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_ask_endpoint_rejects_empty_or_oversized_input() -> None:
    empty = client.post("/api/ask", json={"question": "  "})
    oversized = client.post("/api/ask", json={"question": "q" * 1501})

    assert empty.status_code == 422
    assert oversized.status_code == 422


def test_safety_routed_question_returns_local_response_without_index(
    monkeypatch,
) -> None:
    import src.backend_service as service

    monkeypatch.setattr(
        service,
        "get_index",
        lambda: (_ for _ in ()).throw(AssertionError("safety route must not load index")),
    )

    result = service.answer_question("I want to die.")

    assert result["safety_route"] == "urgent_support"
    assert "local emergency services" in result["answer"]
    assert result["passages"] == []


def test_safety_routed_answer_action_does_not_retrieve_or_call_model(
    monkeypatch,
) -> None:
    import src.backend_service as service

    monkeypatch.setattr(
        service,
        "_retrieve",
        lambda _: (_ for _ in ()).throw(
            AssertionError("safety-routed action must not retrieve")
        ),
    )

    response = client.post(
        "/api/action",
        json={
            "action": "alternative",
            "question": "I want to die.",
        },
    )

    assert response.status_code == 422
    assert "safety-routed" in response.json()["detail"]["message"]


def test_backend_error_response_is_safe(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "answer_question",
        lambda _: (_ for _ in ()).throw(
            RetrievalError("private path and sensitive details")
        ),
    )

    response = client.post("/api/ask", json={"question": "A normal question"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "index_unavailable"
    assert "private path" not in response.text


def test_action_endpoint_runs_answer_control_in_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "answer_action",
        lambda action, question, answer: f"{action}: {question}: {answer}",
    )

    response = client.post(
        "/api/action",
        json={
            "action": "simplify",
            "question": "How can I support a peer?",
            "answer": "A grounded answer.",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "simplify: How can I support a peer?: A grounded answer."
    )


def test_model_error_maps_to_safe_backend_response(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "answer_question",
        lambda _: (_ for _ in ()).throw(
            AnswerGenerationError("Gemini failed with key secret-value")
        ),
    )

    response = client.post("/api/ask", json={"question": "A normal question"})

    assert response.status_code == 503
    assert "secret-value" not in response.text
    assert "Gemini service" in response.json()["detail"]["message"]
