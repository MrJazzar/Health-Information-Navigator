# Prompt Log — Appendix A

| Date | AI tool | Exact prompt used | Output or change produced | Human review | Why accepted, rejected, or modified |
|---|---|---|---|---|---|
| 2026-10-26 | Copilot SDK in VS Code | User-provided attachment titled **“Project Brief: Mental Health Navigator — HAI Term Project 2026”**. The verbatim source is the 399-line conversation attachment; its full text has not been copied into this repository. **Human completion required:** paste/archive the exact attachment text here before submitting if the course requires a self-contained verbatim prompt record. | Workspace inspected; Python/Streamlit RAG prototype, safety routing, documentation, and tests created. No fabricated study or evaluation results were added. | Implementation and generated artifacts require team review; no API-backed answer quality or participant testing has yet been reviewed. | Used as implementation scope. Source page and local PDF should be checked by the team; replace role placeholders and verify sample evaluation questions before submission. |
| 2026-11-03 | GitHub Copilot in VS Code; exact model/version not surfaced | A conversation-flow request followed by one composite Week 5 implementation request. Verbatim topical excerpts are recorded in [docs/prompt_log_appendix_a.md](docs/prompt_log_appendix_a.md#week-5-entries-2026-11-03); these were sections of the submitted requests, not separate prompts. | Updated the existing Streamlit conversation flow and tests; added Week 5 diagrams/checklist; corrected evaluation page references; built and validated a Gemini-embedded index; and completed one real backend generation call. Full output and status are in [docs/gemini_backend_demo.md](docs/gemini_backend_demo.md). | The full automated test suite passed. Human review of the generated answer and project changes is still pending. | Preserved the existing RAG architecture and safety-first routing. One later redundant embedding rebuild attempt hit Gemini quota; the previously validated Gemini index remains intact. No API key was recorded. |

## Team completion checklist

- [ ] Add the original user prompt verbatim if a standalone exact-prompt appendix is
  required by the course.
- [ ] Record the exact model/tool version and prompts actually used if required by
  course policy.
- [ ] Add human-review decisions for any later AI-assisted changes.
- [ ] Replace team-member placeholders with confirmed names and roles.
- [ ] Review the Week 5 implementation and documentation as a team.
- [ ] Have a human reviewer check the recorded Gemini response against the cited source page and record their decision.
- [ ] Rerun Gemini indexing after embedding quota is available if a fresh rebuild is required.
- [ ] Archive the full original Week 5 prompt verbatim if the course requires a self-contained prompt log.
