import csv

from src.feedback import record_feedback


def test_feedback_does_not_store_question_text(tmp_path) -> None:
    path = tmp_path / "feedback.csv"
    record_feedback(path, "helpful", "random-session-id")

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["category"] == "helpful"
    assert "question" not in rows[0]
