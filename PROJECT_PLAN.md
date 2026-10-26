# Mental Health Navigator — Project Plan

## Problem statement

University students may want accessible, source-grounded information about stress,
wellbeing, peer support, and seeking help. This prototype makes one educational book
searchable and explains which passages were used, while making its limits and data
flow visible.

## Target users

University students seeking general educational information, plus a student project
team evaluating a small retrieval-augmented interface.

## Scope

- Local PDF text extraction, inspectable page-preserving chunks, and a persistent local
  retrieval index.
- Gemini-generated responses grounded in retrieved book passages, when a key and
  account-supported model are configured.
- Safety routing (including a local private-record refusal), source inspection, answer
  controls, minimal local feedback, and a reproducible manual evaluation plan.

## Non-scope

Diagnosis, psychotherapy, crisis monitoring, emergency dispatch, medication or
treatment recommendations, clinical validation, account/user profiling, OCR, and
production-grade privacy/security certification.

## Core user journey

1. Read the purpose, limitations, source, and data-flow notice.
2. Ask a general question without sharing identifying details.
3. Review a concise answer and citations to actual PDF pages.
4. Expand the explanation to inspect retrieved passages and ranking scores.
5. Simplify or request another source-supported approach.
6. Submit a minimal usefulness or issue signal, or delete local feedback.

## Tool choices and rationale

- **Python 3.11:** available in the implementation environment and familiar for a
  university prototype.
- **Streamlit:** concise local interface with built-in forms and expandable details.
- **pypdf:** local extraction while preserving PDF page positions; no OCR or external
  upload is initiated by extraction.
- **Google Gen AI SDK embeddings (default):** sends document chunks and queries to a
  configured Gemini embedding model, avoiding local model downloads. A local
  deterministic feature-hash fallback is available for offline tests or use without
  API credentials; it is a lexical baseline, not a contextual sentence model.
- **NumPy:** normalizes vectors and calculates cosine similarity locally after
  embeddings are received.
- **Google Gen AI SDK:** calls the account-configured Gemini generation model.
- **pytest:** small offline tests for extraction, chunking, retrieval, and safety.

## HAI Principle Ladder

| Level | Design choice | Measurable objective |
|---|---|---|
| Inform | Purpose, limitations, and privacy/data-flow notice near the question field | Human-reviewed source-supported answer rate; target ≥80% |
| Explain | Actual source-page citations and expandable retrieved-passage/debug view | Human-reviewed citation support rate; target ≥90% |
| Allow Control | Functional Simplify Answer and Suggest an Alternative actions | Proportion who discover and successfully use a requested control during task testing; target ≥80% |
| Enable Feedback | Helpful, Not Helpful, Report an Issue and deletion control | Proportion who discover and successfully use feedback during task testing; target ≥80% |

## Proposed objectives and evaluation

Targets are not results. The Week 4 definitions and evidence requirements are in
[docs/evaluation_methodology.md](docs/evaluation_methodology.md). Proposed targets:
answer correctness ≥80%, citation support ≥90%, retrieval Recall@5 ≥80%, task
completion ≥80%, control discoverability ≥80%, and feedback discoverability ≥80%.

## Source attribution and licensing

Primary source: UBC Student Health and Wellbeing Staff and named contributors,
_Starting a conversation about mental health: Foundational training for students_
(2021), BCcampus, <https://opentextbc.ca/studentmentalhealth/>. The official book page
states CC BY 4.0 for the book. Preserve attribution and the license link when reusing
book material. The cover image has separate credit and an Unsplash License; do not
assume it shares the book's license. Third-party content within the book may also have
separate rights. The source PDF is kept local and excluded from Git.

## Team roles

1. **Member 1 — Project coordination and HAI design:** [name to be completed].
2. **Member 2 — Data processing and retrieval:** [name to be completed].
3. **Member 3 — UI and safety review:** [name to be completed].
4. **Member 4 — Testing and evaluation:** [name to be completed].

Replace placeholders with the team's actual assignments; do not infer names or claim
user research that has not occurred.
