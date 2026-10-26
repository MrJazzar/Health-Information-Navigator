# HAI Principle Ladder v1

All thresholds below are proposed targets. No participant results have been collected.

| Level | Objective | Current feature | Metric and proposed target | Evidence |
|---|---|---|---|---|
| 1 — Inform | Give understandable, relevant educational information grounded in the selected book, while setting scope and privacy expectations | Welcome, purpose, limitations, and data-flow notices; retrieval-based answer pipeline | Source-supported answer rate ≥80% | Human review of substantive claims against retrieved excerpts |
| 2 — Explain | Make source evidence and answer limitations inspectable | Book title/page citations; expandable retrieved passages and similarity ranks | Citation support rate ≥90% | Human checks each claim against actual cited passage; page existence alone does not pass |
| 3 — Allow Control | Let users request a simpler or different supported presentation | Simplify Answer; Suggest an Alternative | Supported-control task success ≥80% | Observe whether participant finds and completes each requested control |
| 4 — Enable Feedback | Let users report inaccurate, unclear, or inappropriate output | Helpful, Not Helpful, Report an Issue; local deletion action | Feedback discovery and successful use ≥80% | Observe task completion and ask where feedback is stored/how it can be deleted |

## Measurement boundaries

- Denominator and missing records must be reported for every percentage.
- “Source-supported” and “citation supported” require human assessment; embeddings or
  citation formatting cannot establish factual support on their own.
- Control success does not imply answer correctness or clinical safety.
- Feedback discoverability is unmeasured until participants test it.
- Use fictional scenarios, obtain consent, and do not solicit personal mental-health
  histories.
