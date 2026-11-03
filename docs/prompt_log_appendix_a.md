# Week 4 Prompt Log — Appendix A

| Entry | Date | AI tool | Exact prompt actually used | Brief output summary | Team review | Changes made and rationale |
|---|---|---|---|---|---|---|
| A1 | 2026-10-26 | Copilot SDK in VS Code | The user supplied a read-only 268-line attachment beginning: “You are an AI evaluation engineer working on my existing HAI Term Project 2026: **Mental Health Navigator**.” The full prompt remains in the VS Code conversation attachment and is not reproduced verbatim in this file. **To complete before submission:** copy the exact attachment text from the conversation into this cell if a self-contained verbatim log is required. | Inspected existing application/source, created a source-grounded 20-question evaluation dataset, evaluation and safety runners, and Week 4 planning documents/tests. No participant evaluation or answer-quality labels were created. | Team review is pending. | No external LLM was used to author the answer key; key points were checked against extracted book passages. API answer-generation calls are opt-in in the evaluator because they send prompts/passages externally and may use quota. |

## Week 5 Entries (2026-11-03)

The excerpts below are copied from the actual user requests in this conversation. The first request asked for conversation-flow changes; the later request was one composite Week 5 prompt covering conversation flow, architecture, the Golden Rules, backend demonstration, and tests. The category excerpts were not separate prompts. The full composite attachment is not reproduced here; archive it verbatim if the course requires a standalone full transcript. The exact Copilot model/version was not surfaced in this log.

### A2 — Conversation-flow request

**AI tool:** GitHub Copilot in VS Code
**Exact prompt excerpts:**

> “Now implement ONLY the conversation flow improvements in the existing Streamlit application.”
>
> “Add a friendly greeting that explains what the chatbot does.”
>
> “Add clear quick-reply buttons for:
> - Simplify Answer
> - Suggest an Alternative
> - Show Sources”
>
> “Preserve all existing safety checks. Safety checks must happen before any Gemini model call.”
>
> “Improve error recovery: Handle Gemini API errors; Handle retrieval failures; Show a clear fallback message; Give the user a way to retry.”

**Output:** Existing app flow was centralized for safe routing and retry; source controls and focused tests were added.
**Review:** Automated tests only; team review pending.
**Rationale:** Reused the current retrieval, answer-generation, safety, and feedback modules. No live model call was made.

### A3 — Composite Week 5 request

**AI tool:** GitHub Copilot in VS Code
**Verbatim excerpts by topic:**

**Conversation flow design**

> “Implement and document a complete conversation flow.”
>
> “- Normal educational question.
> - Safety-related question.
> - Question containing private identifying information.
> - No relevant knowledge source found.
> - Gemini/API failure.
> - Invalid or empty user input.”

**System architecture**

> “Create a clear system architecture diagram using Mermaid.”
>
> “The diagram must include:
> 1. User.
> 2. Streamlit interface.
> 3. Python backend.
> 4. Safety checks.
> 5. PDF knowledge source.
> 6. PDF extraction.
> 7. Chunking.
> 8. Embedding generation.
> 9. Local vector index.
> 10. Retriever.
> 11. Gemini model/API.
> 12. Answer generation.
> 13. Citations and source passages.
> 14. Feedback storage.”
>
> “The architecture must reflect the actual implementation, not imaginary components.”

**Shneiderman's Eight Golden Rules**

> “Create: docs/shneiderman_golden_rules.md”
>
> “Include a checklist for all eight rules:
> 1. Strive for consistency.
> 2. Enable shortcuts.
> 3. Offer informative feedback.
> 4. Design dialogs that give closure.
> 5. Prevent errors and handle them simply.
> 6. Permit easy reversal of actions.
> 7. Support the user's sense of control.
> 8. Reduce short-term memory load.”
>
> “Do not mark a feature as implemented unless it actually exists in the code.”

**Backend model integration**

> “The goal is to demonstrate a real successful model response from our own Python backend, not from a public AI website.”
>
> “Run the request only if valid configuration and credentials are available.”
>
> “If credentials are missing, explain exactly how to configure them and leave the live demonstration marked PENDING.”

**Testing and refinement**

> “Inspect existing tests before adding new tests.”
>
> “Run: python -m pytest tests/test_app.py tests/test_safety.py tests/test_answer_generator.py -q”
>
> “Then run the complete test suite if the environment permits: python -m pytest -q”
>
> “If a test fails: Investigate the root cause. Fix the implementation if appropriate. Rerun the relevant tests. Report unresolved failures honestly.”

**Output and review:** Existing Streamlit code and safety wording were updated; focused tests and Week 5 design documents were added. The supplied PDF was inspected and a Gemini-embedded index was built and validated. One real backend generation call succeeded with `gemini-3.6-flash` at `2026-11-03T20:10:32.447407+00:00`, using the question “According to the source excerpt, what are the first three steps for supporting a peer?” The actual response is recorded in [docs/gemini_backend_demo.md](gemini_backend_demo.md). The full test suite passed (42 tests). Human review is pending.
**Rationale:** The implementation preserves source-grounded retrieval and the safety-first flow. The prompt excerpts are not presented as separate prompts; the actual response is recorded without credentials, and no human-review result is fabricated. A later redundant embedding rebuild attempt hit quota; the previously validated index remained available.

## Blank entry template

| Entry | Date | AI tool | Exact prompt actually used | Brief output summary | Team review | Changes made and rationale |
|---|---|---|---|---|---|---|
| A__ | YYYY-MM-DD | [tool/version] | [paste exact prompt; do not reconstruct from memory] | [what was produced] | [reviewer and findings] | [accepted/modified/rejected and why] |

No prompt, model result, or human review should be backfilled as if it happened when
it did not.
