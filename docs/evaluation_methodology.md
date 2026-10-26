# Evaluation Methodology

## Verified implementation facts

- **LLM and SDK:** Google Gemini API through the official `google-genai` SDK. The local
  configuration was tested with `gemini-3.5-flash` for generation and
  `gemini-embedding-2` for embeddings. These account/model settings can change.
- **Interface/backend:** Python 3.11 and Streamlit.
- **Source extraction:** `pypdf` extracts per-page text locally. The report retains
  physical PDF pages and printed book page labels where recognized/inferred; it flags
  low-text or image-heavy pages and does not run OCR.
- **Chunking:** sentence-aware character-size chunks, page-specific metadata, JSONL
  storage; current defaults are 2,600 characters and 400 overlap.
- **Embeddings and retrieval:** Gemini API encodes chunks and query using document /
  question-answering task formatting. The vectors are stored locally. NumPy performs
  normalized cosine ranking. Top 3 passages above the configured threshold are sent
  to answer generation; the evaluator inspects unthresholded Recall@5.
- **Generation and citations:** retrieved passages are placed in the prompt as
  evidence, not instructions. Application code appends citations from retrieved
  metadata. This verifies page provenance, not whether every generated claim is
  supported.
- **Safety and privacy:** phrase-pattern routing runs before embedding/generation for
  urgent, professional-care, private-record, and location-specific emergency-number
  requests. The app does not log the submitted question in feedback. This is not a
  comprehensive classifier.
- **Testing:** pytest offline tests and separate command-line evaluation/safety
  runners. No new runtime package is required for evaluation.

## Run the evaluation

From the project root in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m evaluation.run_evaluation
```

Default mode calls the embedding API for retrieval but does **not** call generation.
It reports Recall@5 and retrieval-only latency. For generated answers, the runner
processes questions sequentially through the application's Gemini embedding,
retrieval-threshold, and answer-generation path. It writes JSON and CSV before
processing, then refreshes them after each question. To begin with the requested
three-question pilot:

```powershell
python -m evaluation.run_evaluation --generate --limit 3
```

For a pilot that also exercises an unanswerable prompt, select two answerable
questions and MHN-20 explicitly:

```powershell
python -m evaluation.run_evaluation --generate --question-ids MHN-01,MHN-02,MHN-20
```

The command prints the generated JSON path. Resume from that report with:

```powershell
python -m evaluation.run_evaluation --generate --resume-from evaluation\results\evaluation_<timestamp>_generated.json
```

Successful results are skipped; failed and pending questions are eligible to run.
If the pilot selected specific IDs, use the same `--question-ids` list when resuming
that pilot; omit it to continue all remaining dataset questions.
Temporary rate limits, server errors, and timeouts receive bounded exponential
backoff. Quota exhaustion is not retried and leaves later questions pending. JSON
`status_counts` tracks successful, failed, and pending questions; each result includes
its generated response, retrieved source references, latency, attempts, and sanitized
error details. Review `abstention_review_human` manually for generated answers to
unanswerable questions; retrieved passages are not automatically treated as success or
failure. Results are written under `evaluation/results/`; a missing PDF, stale index,
API problem, or missing credentials is reported rather than replaced with fabricated
output. To rebuild an invalid index:

```powershell
python scripts/build_index.py
```

## Metric definitions

- **Recall@5:** answerable questions whose manually verified expected source page is
  present in unthresholded top five chunks ÷ answerable questions with successful
  retrieval. Unanswerable prompts are excluded; report the denominator.
- **Answer correctness:** human-scored correct answers ÷ generated answers actually
  human-reviewed. `answer_correctness_human` is blank until a reviewer enters 0 or 1.
- **Citation support rate:** supported claim/citation pairs ÷ all claim/citation pairs
  reviewed by a human. Store individual review entries in `citation_reviews`, with
  `claim`, `page`, `supported`, and `reviewer`. A page number alone is not evidence.
- **Abstention quality:** report deterministic no-retrieval abstentions for
  unanswerable questions separately from generated answers. Generated answers on
  unanswerable questions require manual rating (`abstention_review_human`: 0 or 1).
  The manual aggregate reports appropriate and inappropriate reviewed answers
  separately; automatically empty retrieval, unanswerable questions with retrieved
  passages, and locally safety-routed requests are reported separately.
- **Latency:** median wall-clock ms among successful runs. Default includes retrieval
  for ordinary questions and local safety-route response time for safety-routed
  prompts; the report labels the mixed scope. `--generate` measures retrieval plus
  answer generation for normal-route questions. It is not a quality metric.

No response is scored automatically as factually correct. Review `expected_answer_points`
against the saved answer and retrieved passages. Answerability/source pages were
reviewed against extracted chunks before inclusion; reviewers should re-open the
original PDF before publishing results.

## Editing and reviewing records

Edit `evaluation/evaluation_dataset.json` to add or revise questions. Keep unique IDs,
write compact answer points, verify the printed page against the local PDF, and leave
page arrays empty for unanswerable questions. Do not treat an LLM answer as its own
ground truth.

In the timestamped CSV, review each generated answer and fill:

- `answer_correctness_human`: `1` correct or `0` incorrect.
- `citation_reviews`: JSON array of claim-by-claim review objects, e.g.
  `[{"claim":"The answer's claim","page":75,"supported":true,"reviewer":"R1"}]`.
- `abstention_review_human`: `1` appropriate, `0` inappropriate for unanswerable rows.
- `reviewer` and `review_notes`: reviewer code and concise evidence; do not put personal
  mental-health data here.

Rerun the metrics from edited results with
`python -m evaluation.score_results <path-to-json-or-csv>`; until manual labels are
entered, correctness/citation rates must remain “not measured.”
