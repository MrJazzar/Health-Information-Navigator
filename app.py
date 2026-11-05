"""Streamlit front end for the locally indexed student mental health navigator."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from config import PDF_PATH, STORAGE_DIR
from src.backend_client import BackendClientError, ask_backend, run_backend_action
from src.feedback import anonymous_session_id, delete_feedback, record_feedback
from src.safety import Route

FEEDBACK_PATH = STORAGE_DIR / "feedback.csv"
REQUEST_FAILURE_MESSAGE = (
    "I'm sorry, I couldn't generate a reliable answer right now. Please try again or "
    "consult an official mental health support resource. This chatbot provides "
    "educational information only; it does not provide diagnosis, treatment, or "
    "emergency assistance."
)


def _feedback() -> None:
    st.markdown("**Was this answer useful?**")
    columns = st.columns(3)
    for column, label, category in zip(
        columns,
        ("Helpful", "Not Helpful", "Report an Issue"),
        ("helpful", "not_helpful", "report_issue"),
    ):
        if column.button(label, key=f"feedback_{category}"):
            record_feedback(
                FEEDBACK_PATH,
                category,
                st.session_state["anonymous_session_id"],
            )
            st.success("Thanks. Your feedback was saved without the question text.")


def _process_question(
    question: str,
    state: MutableMapping[str, Any] | None = None,
) -> None:
    state = state if state is not None else st.session_state
    question = question.strip()
    state["question"] = question
    for key in (
        "answer",
        "passages",
        "simplified_answer",
        "alternative_answer",
        "control_error",
        "safety_route",
        "request_error",
        "show_sources",
    ):
        state.pop(key, None)

    if not question:
        return

    try:
        result = ask_backend(question)
        state["answer"] = result["answer"]
        state["passages"] = result["passages"]
        if result.get("safety_route"):
            state["safety_route"] = result["safety_route"]
    except BackendClientError as exc:
        state["answer"] = REQUEST_FAILURE_MESSAGE
        state["passages"] = []
        state["request_error"] = str(exc)


def _retry_question() -> None:
    question = st.session_state.get("question", "")
    if question:
        _process_question(question)


def _toggle_sources(state: MutableMapping[str, Any] | None = None) -> None:
    state = state if state is not None else st.session_state
    state["show_sources"] = not state.get("show_sources", False)


def _render_answer_controls() -> None:
    answer = st.session_state.get("answer")
    passages = st.session_state.get("passages", [])
    if not answer or not passages:
        return

    simplify_col, alternative_col, sources_col = st.columns(3)
    if simplify_col.button("Simplify Answer", key="quick_simplify"):
        with st.spinner("Simplifying while retaining citations..."):
            try:
                st.session_state["simplified_answer"] = run_backend_action(
                    "simplify",
                    st.session_state["question"],
                    answer,
                )
                st.session_state["control_error"] = ""
            except BackendClientError as exc:
                st.session_state["control_error"] = str(exc)
    if alternative_col.button("Suggest an Alternative", key="quick_alternative"):
        with st.spinner("Checking for another source-supported approach..."):
            try:
                st.session_state["alternative_answer"] = run_backend_action(
                    "alternative",
                    st.session_state["question"],
                )
                st.session_state["control_error"] = ""
            except BackendClientError as exc:
                st.session_state["control_error"] = str(exc)
    if sources_col.button(
        "Hide Sources" if st.session_state.get("show_sources") else "Show Sources",
        key="quick_sources",
    ):
        _toggle_sources()
    if st.session_state.get("control_error"):
        st.warning(
            f"{st.session_state['control_error']} Use the related action button again to retry."
        )
    if st.session_state.get("simplified_answer"):
        st.markdown("#### Simplified answer")
        st.markdown(st.session_state["simplified_answer"])
    if st.session_state.get("alternative_answer"):
        st.markdown("#### Alternative approach")
        st.markdown(st.session_state["alternative_answer"])


def _sidebar() -> None:
    with st.sidebar:
        section = st.radio("Explore", ("Ask a question", "About", "Sources", "Limitations"))
        if section == "About":
            st.markdown(
                "This prototype helps students navigate general educational information "
                "about mental health and peer support. It does not diagnose or provide therapy."
            )
        elif section == "Sources":
            st.markdown(
                "Primary source: [Starting a Conversation About Mental Health: "
                "Foundational Training for Students](https://opentextbc.ca/studentmentalhealth/), "
                "BCcampus / UBC Student Health and Wellbeing Staff. CC BY 4.0 for the book. "
                "See README for attribution and third-party exclusions."
            )
        elif section == "Limitations":
            st.markdown(
                "The configured Gemini embedding API provides semantic vectors; similarity "
                "scores are rankings, not probabilities. Generated answers can be wrong. "
                "This app is not clinical "
                "care, diagnosis, treatment, or emergency monitoring."
            )
        if section != "Ask a question":
            st.caption("Choose **Ask a question** to return to the navigator.")


def main() -> None:
    st.set_page_config(page_title="Mental Health Navigator")
    _sidebar()
    if "anonymous_session_id" not in st.session_state:
        st.session_state["anonymous_session_id"] = anonymous_session_id()

    st.title("Mental Health Navigator")
    st.write(
        "Hi, I'm the Mental Health Navigator. I help students find general educational "
        "information in BCcampus's Starting a Conversation About Mental Health: "
        "Foundational Training for Students. Ask about stress, wellbeing, peer support, "
        "or finding help. I don't provide diagnosis or treatment."
    )
    st.warning(
        "Educational information only — not diagnosis, psychotherapy, treatment, or "
        "emergency response. If there is immediate danger, contact local emergency services."
    )
    st.info(
        "Privacy: PDF text, chunks, the saved index, and cosine ranking stay on this "
        "computer and are processed by the Python backend. With configured Gemini embeddings, book chunks and submitted questions "
        "are sent to Gemini for embeddings; ordinary questions and retrieved excerpts "
        "are also sent for answer generation. Feedback stores only a timestamp, random "
        "session ID, category, and generic technical label; it does not save question text."
    )

    with st.form("question_form"):
        question = st.text_area(
            "What would you like to know?",
            placeholder="For example: What are some ways students can support a peer?",
            max_chars=1500,
        )
        st.caption(
            "Example topics: stress, wellbeing, peer support, or how to seek help. "
            "Avoid sharing identifying or sensitive personal details."
        )
        submitted = st.form_submit_button("Find information")

    if submitted:
        if not question.strip():
            _process_question(question)
            st.warning("Enter a question to get started.")
        else:
            with st.spinner("Checking your question and preparing a grounded answer..."):
                _process_question(question)

    if st.session_state.get("request_error"):
        st.error(st.session_state["request_error"])
        st.button("Retry", key="retry_question", on_click=_retry_question)

    answer = st.session_state.get("answer")
    if answer:
        st.markdown("### Answer")
        st.markdown(answer)
        if st.session_state.get("safety_route") in {
            Route.URGENT_SUPPORT.value,
            Route.PROFESSIONAL_SUPPORT.value,
            Route.PRIVACY_PROTECTION.value,
            Route.LOCAL_EMERGENCY_INFORMATION.value,
        }:
            st.info("This request was handled locally; it was not sent to Gemini.")
        if st.session_state.get("passages"):
            _render_answer_controls()
            with st.expander(
                "How was this answer generated? Show sources",
                expanded=st.session_state.get("show_sources", False),
            ):
                st.caption(
                    "Retrieved passages are evidence excerpts. Similarity scores are "
                    "ranking aids, not probabilities or calibrated confidence."
                )
                for passage in st.session_state["passages"]:
                    st.markdown(
                        f"**{passage['source_filename']} — book page "
                        f"{passage['page_start']} (PDF page "
                        f"{passage.get('pdf_page_start', passage['page_start'])})** · similarity "
                        f"`{passage['similarity']:.3f}`"
                    )
                    st.write(passage["text"])
            _feedback()

    with st.expander("Privacy and local data controls"):
        st.write(
            f"The source PDF is read from `{PDF_PATH}`. Index files and question-free "
            f"feedback are stored under `{STORAGE_DIR}`. Delete `feedback.csv` there, or "
            "use the delete button below. Index/cache files can be removed and rebuilt "
            "with `python scripts/build_index.py`."
        )
        if st.button("Delete locally stored feedback"):
            removed = delete_feedback(FEEDBACK_PATH)
            st.info(
                "Local feedback deleted."
                if removed
                else "No local feedback file was found."
            )


if __name__ == "__main__":
    main()
