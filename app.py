"""Streamlit front end for the locally indexed student mental health navigator."""

from __future__ import annotations

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
def _render_answer_controls() -> None:
    answer = st.session_state.get("answer")
    passages = st.session_state.get("passages", [])
    if not answer or not passages:
        return

    simplify_col, alternative_col = st.columns(2)
    if simplify_col.button("Simplify Answer"):
        with st.spinner("Simplifying while retaining citations..."):
            try:
                st.session_state["simplified_answer"] = simplify_answer(answer, passages)
                st.session_state["control_error"] = ""
            except AnswerGenerationError as exc:
                st.session_state["control_error"] = str(exc)
    if alternative_col.button("Suggest an Alternative"):
        with st.spinner("Checking for another source-supported approach..."):
            try:
                st.session_state["alternative_answer"] = suggest_alternative(
                    st.session_state["question"], passages
                )
                st.session_state["control_error"] = ""
            except (AnswerGenerationError, UnsupportedQuestionError) as exc:
                st.session_state["control_error"] = str(exc)
    if st.session_state.get("control_error"):
        st.warning(st.session_state["control_error"])
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
        "Explore general information about stress, emotional wellbeing, peer support, "
        "and seeking help, grounded in an educational book for students."
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
        st.session_state.pop("answer", None)
        st.session_state.pop("passages", None)
        st.session_state.pop("simplified_answer", None)
        st.session_state.pop("alternative_answer", None)
        st.session_state["safety_route"] = ""
        st.session_state["question"] = question.strip()
        if not question.strip():
            st.warning("Enter a question to get started.")
        else:
            decision = assess_question(question)
            if decision.route != Route.NORMAL:
                st.session_state["answer"] = decision.response
                st.session_state["passages"] = []
                st.session_state["safety_route"] = decision.route.value
            else:
                with st.spinner("Searching the book and preparing a grounded answer..."):
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
                            st.session_state["answer"] = (
                                "The available book does not provide enough relevant "
                                "information to answer this question. Consider asking a "
                                "qualified professional or a relevant official resource."
                            )
                            st.session_state["passages"] = []
                        else:
                            st.session_state["answer"] = generate_answer(question, passages)
                            st.session_state["passages"] = passages
                            st.session_state["safety_route"] = ""
                    except (
                        PDFProcessingError,
                        RetrievalError,
                        EmbeddingError,
                        AnswerGenerationError,
                        UnsupportedQuestionError,
                        OSError,
                    ) as exc:
                        st.session_state["answer"] = ""
                        st.error(f"Unable to answer right now: {exc}")
                        if not INDEX_PATH.exists():
                            st.info("Build the local index with `python scripts/build_index.py`.")

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
            with st.expander("How was this answer generated? Show sources"):
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
