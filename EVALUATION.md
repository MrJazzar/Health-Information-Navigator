# Evaluation Plan

## Procedure

1. Inspect the source PDF and confirm the extracted text and page positions are
   readable. Record any pages with no/little text; do not infer missing content.
2. Build the index with the selected embedding configuration and record its settings.
3. For each sample question, inspect the top three retrieved passages. Annotate
   relevance before reading the generated answer to reduce confirmation bias.
4. Review every substantive answer claim against those exact passages and actual page
   metadata. Mark unsupported or mis-cited claims as not grounded.
5. Run task-based sessions with consenting team members. Give participants a task,
   observe completion without coaching, then ask short comprehension and transparency
   questions. Do not collect sensitive mental health disclosures.
6. Record one row per question/participant in `data/evaluation_template.csv`. Leave
   unknown measures blank and document exclusions or failures in reviewer notes.

## Sample questions

These seed questions were checked against the extracted text in the local PDF. The
indicated printed page labels are navigation aids for manual review, not evaluation
results; the retriever must still return relevant passages in the run being assessed.

1. What steps does the book suggest when helping another student? (Printed book page
   76; the “Listen actively” list appears in the extracted text.)
2. According to the book, what is an empathetic listener's role, and what should they
   avoid doing? (Printed book page 75.)
3. What kinds of services and supports can students consider on campus? (Printed book
   page 77 and following.)

## Metrics and proposed targets

| Metric | Calculation | Proposed target |
|---|---|---|
| Retrieval Recall@5 | Answerable questions with a verified supporting page in the unthresholded top 5 ÷ answerable questions with successful retrieval × 100 | ≥80% |
| Answer correctness | Generated answers meeting manually reviewed answer points ÷ generated answers with completed human review × 100 | ≥80% |
| Citation support rate | Claim/citation pairs supported by their cited passage ÷ all human-reviewed claim/citation pairs × 100 | ≥90% |
| Task completion | Participants who complete the assigned information-finding task without intervention ÷ participants who attempted it × 100 | ≥80% |
| Answer comprehension | Participants who correctly paraphrase the answer's main point and limitation ÷ participants asked the comprehension check × 100 | ≥80% |
| Control discoverability | Participants who find and successfully use the requested control without help ÷ participants asked to use it × 100 | ≥80% |
| Source transparency | Participants who correctly identify the cited source/page and find the supporting passage ÷ participants asked to verify a source × 100 | ≥80% |

For binary questions, mark `1` for success and `0` for failure; calculate the percentage
from nonblank reviewed records. Report denominator and missing values alongside any
percentage. Do not report targets as achieved until results are collected.

## Results

| Metric | Target | Observed result | Denominator / notes |
|---|---:|---:|---|
| Retrieval Recall@5 | ≥80% | 13/14 (92.9%) | [Retrieval-only JSON run](evaluation/results/evaluation_20261026T211559Z_retrieval.json); 14 eligible answerable questions |
| Answer correctness | ≥80% | Not measured | Requires generated answers and human review |
| Citation support rate | ≥90% | Not measured | Requires claim-by-claim human review |
| Abstention quality | Report appropriate/inappropriate counts | Not assessed on generated answers | Retrieval-only run; normal unsupported questions had retrieved passages; generation and human review are still needed |
| Task completion | ≥80% | Not measured | |
| Answer comprehension | ≥80% | Not measured | |
| Control discoverability | ≥80% | Not measured | |
| Source transparency | ≥80% | Not measured | |

## Known limitations and next steps

For generated answers, begin with a three-question API pilot:
`python -m evaluation.run_evaluation --generate --question-ids MHN-01,MHN-02,MHN-20`
includes two answerable questions and one unanswerable question. The runner saves progress
after each question and resumes from the JSON file with
`--generate --resume-from <generated-json-path>`. Inspect `status_counts`, the
`answer_text`, and `retrieved_sources` fields. Correctness, citation support, and
whether generated answers appropriately acknowledge insufficient evidence remain
unscored until human review.

The Week 4 evaluation deliverables now live in
[docs/evaluation_methodology.md](docs/evaluation_methodology.md) and
[evaluation/](evaluation/). Use the reproducible 20-question dataset and separate
safety test runner rather than treating the three sample prompts below as the complete
test set.

- The default Gemini embedding provider sends book chunks and queries to an external
  API. A local feature-hash fallback captures word and adjacent-word overlap; it is
  not a trained sentence model and may miss paraphrases.
- A similarity threshold is a ranking cutoff, not calibrated confidence.
- Generation depends on external Gemini availability and can still produce errors.
- Safety rules are explicit lightweight patterns, not comprehensive risk assessment.
  This system is not monitored and cannot provide emergency response.
- Verify sample questions against the extracted text; review book pages and
  third-party rights when reusing content.
- Conduct actual task/comprehension testing with appropriate consent before filling
  in results. No user research or outcomes are claimed here.
