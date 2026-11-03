"""Streamlit front end for the locally indexed student mental health navigator."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from config import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    INDEX_PATH,
    PDF_PATH,
    RETRIEVAL_MIN_SIMILARITY,
    RETRIEVAL_TOP_K,
    STORAGE_DIR,
)
from src.answer_generator import (
    AnswerGenerationError,
    UnsupportedQuestionError,
    generate_answer,
    simplify_answer,
    suggest_alternative,
)
from src.embeddings import EmbeddingError, create_embedding_provider
from src.feedback import anonymous_session_id, delete_feedback, record_feedback
from src.pdf_processor import PDFProcessingError
from src.retriever import RetrievalError, file_sha256, load_index, retrieve
from src.safety import Route, assess_question

FEEDBACK_PATH = STORAGE_DIR / "feedback.csv"
NO_PASSAGES_MESSAGE = (
    "The available book does not provide enough relevant information to answer this "
    "question. Try asking in a different way, or consult a qualified professional or "
    "relevant official resource."
)
REQUEST_FAILURE_MESSAGE = (
    "I'm sorry, I couldn't generate a reliable answer right now. Please try again or "
    "consult an official mental health support resource. This chatbot provides "
    "educational information only; it does not provide diagnosis, treatment, or "
    "emergency assistance."
)


@st.cache_resource
def get_index():
    provider = create_embedding_provider()
    if not PDF_PATH.is_file():
        raise PDFProcessingError(f"Source PDF not found: {PDF_PATH}")
    chunks, vectors = load_index(
        INDEX_PATH,
        provider,
        expected_source_sha256=file_sha256(PDF_PATH),
        expected_chunking_config={
            "chunk_size_chars": CHUNK_SIZE_CHARS,
            "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
        },
    )
    return provider, chunks, vectors


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


def _request_error_message(error: Exception) -> str:
    if isinstance(error, (AnswerGenerationError, EmbeddingError)):
        return (
            "The Gemini service could not complete this request. Check that the local "
            "Gemini settings and service are available, then retry."
        )
    if isinstance(error, RetrievalError):
        return (
            "The local source index could not be used. Retry; if the problem continues, "
            "rebuild it with `python scripts/build_index.py`."
        )
    if isinstance(error, PDFProcessingError):
        return "The source PDF could not be read. Check the configured PDF, then retry."
    if isinstance(error, UnsupportedQuestionError):
        return NO_PASSAGES_MESSAGE
    return "A temporary problem prevented this request from completing. Please retry."


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

    decision = assess_question(question)
    if decision.route != Route.NORMAL:
        state["answer"] = decision.response
        state["passages"] = []
        state["safety_route"] = decision.route.value
        return

    try:
        provider, chunks, vectors = get_index()
        passages = retrieve(
            question,
            chunks,
            vectors,
            provider,
            top_k=RETRIEVAL_TOP_K,
            min_similarity=RETRIEVAL_MIN_SIMILARITY,
        )
        if not passages:
            state["answer"] = NO_PASSAGES_MESSAGE
            state["passages"] = []
            return

        state["answer"] = generate_answer(question, passages)
        state["passages"] = passages
    except (
        PDFProcessingError,
        RetrievalError,
        EmbeddingError,
        AnswerGenerationError,
        UnsupportedQuestionError,
        OSError,
    ) as exc:
        state["answer"] = REQUEST_FAILURE_MESSAGE
        state["passages"] = []
        state["request_error"] = _request_error_message(exc)


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
                st.session_state["simplified_answer"] = simplify_answer(answer, passages)
                st.session_state["control_error"] = ""
            except AnswerGenerationError as exc:
                st.session_state["control_error"] = _request_error_message(exc)
    if alternative_col.button("Suggest an Alternative", key="quick_alternative"):
        with st.spinner("Checking for another source-supported approach..."):
            try:
                st.session_state["alternative_answer"] = suggest_alternative(
                    st.session_state["question"], passages
                )
                st.session_state["control_error"] = ""
            except (AnswerGenerationError, UnsupportedQuestionError) as exc:
                st.session_state["control_error"] = _request_error_message(exc)
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
        "computer. With configured Gemini embeddings, book chunks and submitted questions "
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
