# Week 4 Check-in — Objectives and Ladder (Milestone 2)

## Project description and current implementation

Mental Health Navigator is a local Streamlit information navigator for university
students. It retrieves passages from the supplied BCcampus student mental-health
training book and, when configured, sends the question and retrieved passages to
Google Gemini for a concise source-grounded answer. It is educational only; it is not
diagnosis, treatment, psychotherapy, clinical validation, or emergency response.

The selected source is the local
`data/Starting-A-Conversation-About-Mental-Health-Foundational-Training-for-Students-1709075217.pdf`.
Inspection recorded 126 PDF pages and 176,791 extracted characters. Five pages had
fewer than 100 extracted characters; no page had zero extractable text. PDF page 110
was flagged as potentially image-heavy/low-text. No OCR was performed. The PDF and
extracted passages must be rechecked before formal release.

## Target users and scope

- Students seeking general, non-clinical information about stress, peer support, and
  seeking help.
- Project team members reviewing retrieval, answer grounding, source transparency,
  controls, and safety behavior.

In scope: the existing PDF extraction and page-preserving chunking, Gemini embeddings,
cosine retrieval, Gemini answer generation, scope/safety routing, passage display,
Simplify Answer, Suggest an Alternative, and minimal feedback. Out of scope: diagnosis,
personalized treatment, medicine advice, emergency monitoring, local crisis dispatch,
clinical effectiveness claims, and participant research without consent.

## Persona journey maps

See [persona_journey_maps.md](persona_journey_maps.md) for three fictional, distinct
personas and their Start → Ask → Understand → Act/Fix → Finish journeys.

## Measurable objectives (targets, not results)

| Objective | Metric | Proposed target | Evidence required |
|---|---|---:|---|
| Retrieve source material for answerable questions | Recall@5 on questions with verified source pages | ≥80% | Run the fixed dataset and inspect the retrieved printed pages |
| Generate correct source-grounded answers | Answer correctness | ≥80% | Human reviewer compares each answer to answer-key points |
| Support every cited claim | Citation support rate | ≥90% | Human claim-by-claim review; merely seeing a page number is insufficient |
| Abstain where evidence is insufficient | Appropriate abstention rate | Report count and human-reviewed rate | Test unanswerable prompts; inspect each answer |
| Make controls usable | Supported-control task success | ≥80% | Participant task observations for Simplify/Alternative |
| Make feedback discoverable | Feedback discovery and successful use | ≥80% | Participant observation; the feedback control exists in the current UI |
| Explain source and limitations | Source/limitation comprehension | ≥80% | Participant questionnaire and source-check task |

None of these targets is claimed to have been achieved. The reusable dataset is
[`../evaluation/evaluation_dataset.json`](../evaluation/evaluation_dataset.json);
measurement details are in
[evaluation_methodology.md](evaluation_methodology.md).

## HAI Principle Ladder v1

See [hai_principle_ladder.md](hai_principle_ladder.md). Current UI features exist for
all four levels: Inform, Explain, Allow Control, and Enable Feedback. Participant
discoverability and success are not yet measured.

## Actual tool choices and grounding

- Python 3.11, Streamlit, `pypdf`, NumPy, pytest, and the official Google `google-genai`
  SDK; no additional framework is added for evaluation.
- PDF extraction is local and preserves physical PDF page plus detected/inferred
  printed source page. Chunks are sentence-aware, page-specific JSONL.
- Gemini `gemini-embedding-2` creates document/query vectors; NumPy cosine similarity
  ranks passages. The embedding API receives the book chunks during index creation and
  user query text at retrieval time. The question and retrieved text are also sent to
  Gemini for generation. Safety-routed prompts are handled locally before these calls.
- Generated citations are attached from retrieved chunk page metadata, not accepted
  from the model. Humans must still judge whether cited passages support every claim.
- The safety module uses transparent phrase patterns. It is not a comprehensive risk
  detector or a substitute for a person or service.

Full stack and data-flow details: [evaluation_methodology.md](evaluation_methodology.md)
and the project [README](../README.md).

## Evaluation methodology

The fixed 20-question dataset was authored against extracted source passages and
contains answerable and unanswerable prompts. Run retrieval-only to measure Recall@5
without making answer-generation calls; use `--generate` only when approved for API
usage. Correctness, citation support, and ambiguous abstentions need human review.
Reports are timestamped under `evaluation/results/`. The safety runner separately
checks deterministic routes; normal RAG answers remain a manual review task. See
[safety_test_plan.md](safety_test_plan.md).

## Known limitations

- Retrieval and generated answers depend on Gemini account availability, network, and
  API terms; quotas/charges may apply.
- The similarity cutoff is a ranking threshold, not a calibrated probability.
- Citation pages are auditable metadata, but support of each answer claim requires
  human review.
- Phrase-based safety routing can miss or over-trigger cases. It has not received
  clinical safety validation.
- Source PDF extraction may be imperfect on image-heavy pages; no OCR was done.
- No user sessions have been run. No accuracy, usability, or clinical-performance
  outcome is claimed.

## Proposed next steps

1. Review the answer key against the PDF and update any page/point in the dataset.
2. Run retrieval evaluation and retain its raw timestamped report.
3. If approved, run generated-answer evaluation and manually score each response and
   citation.
4. Run safety cases with independent human review of all model-generated responses.
5. Conduct the five-participant usability plan with consent and fictional scenarios;
   enter only anonymized results.
6. Revisit retrieval cutoff and hard safety cases based on evidence, not assumptions.

## Deliverable map

- [Persona journey maps](persona_journey_maps.md)
- [HAI Principle Ladder](hai_principle_ladder.md)
- [Evaluation methodology](evaluation_methodology.md)
- [Safety test plan](safety_test_plan.md)
- [User testing plan](user_testing_plan.md)
- [Prompt log Appendix A](prompt_log_appendix_a.md)
- [20-question evaluation dataset](../evaluation/evaluation_dataset.json)
- [Safety test cases](../evaluation/safety_test_cases.json)
- [User testing template](../evaluation/user_testing_template.csv)
