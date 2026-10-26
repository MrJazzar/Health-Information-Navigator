# Mental Health Navigator

A locally runnable Streamlit prototype that retrieves educational passages from
*Starting a Conversation About Mental Health: Foundational Training for Students* and
uses the configured Google Gemini API to phrase an answer. It is an information
navigator, not diagnosis, psychotherapy, treatment, or emergency response.

## Requirements

- Python 3.11 (or a compatible Python 3 version supported by the installed packages).
- A Gemini API key, a generation model, and an embedding model enabled for your account
  are needed for generated answers and retrieval. PDF inspection, chunking, and tests
  do not need an API key.
- Gemini API embeddings are the default; no embedding model is downloaded. A local
  feature-hash baseline remains available by explicitly setting
  `EMBEDDING_PROVIDER=local`.

## Windows PowerShell setup

Run from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, either allow scripts for this
PowerShell process (`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`) or
run the environment's executable directly, for example
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Source PDF

The project workspace may already contain the source PDF in `data\`. The app uses
`data\mental_health_book.pdf` when present; otherwise it uses the only `*.pdf` in
`data\`. If there are multiple PDFs, set `PDF_PATH` in `.env`.

If you need to download the book manually, use the official BCcampus page:
<https://opentextbc.ca/studentmentalhealth/>. Download the book PDF from that page and
place it at `data\mental_health_book.pdf`. Do not replace or edit the original source
without a reason. The project does not perform OCR.

Inspect extracted content and page numbers before indexing:

```powershell
python scripts/inspect_pdf.py
```

The script reports total pages and extracted characters, pages with little/no text, and
any extraction errors. It records printed source page labels when they can be extracted
from the book footer, and interpolates gaps between consistent numbered footer
anchors, alongside physical PDF page positions. It writes
`storage\extraction_report.json` and
`storage\extracted_text.jsonl`. A page with no text may be scanned or image-heavy; OCR
is not automatic. Review the source page or choose an appropriate local OCR workflow
only if needed.

## Configure Gemini locally

Create a local `.env` file, which is ignored by Git:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `GEMINI_API_KEY` locally, `GEMINI_MODEL` to a generation model, and
`GEMINI_EMBEDDING_MODEL` to an embedding model supported by your Google AI account.
The current local `.env` uses `gemini-3.5-flash` and `gemini-embedding-2`, which were
reported as available and tested with the configured account. Availability may change.
Do not paste
keys into source files, issue trackers, or chat logs. The default
`EMBEDDING_PROVIDER=gemini` sends each book chunk and user query to the Google Gemini
API for embedding. Choose `EMBEDDING_PROVIDER=local` only if you prefer the
download-free but lower-quality local feature-hash baseline.

## Build and run

```powershell
python scripts/build_index.py
streamlit run app.py
```

The index is stored locally in `storage\index.json`; inspectable chunks are written to
`storage\chunks.jsonl`. The index includes the source PDF hash and embedding
configuration. Rebuild it after changing the source, chunking settings, or embedding
provider. The application refuses a stale or malformed index rather than silently
using it.

Set `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SIMILARITY`, `CHUNK_SIZE_CHARS`, and
`CHUNK_OVERLAP_CHARS` in `.env` to tune retrieval and chunking. Gemini embeddings use
question/document task formatting and are requested once per text passage. The local alternative
uses deterministic hashing of words and adjacent-word features. Similarity scores are
ranking aids, not probabilities. Evaluate retrieval against the actual book before
relying on it.

## Tests

```powershell
pytest -q
```

Tests use temporary PDFs and local embeddings. They do not call Gemini or require an
API key.

## Privacy, feedback, and safety

PDF extraction, chunks, the saved index, and cosine retrieval run on this computer.
With the default Gemini embedding provider, book chunks and ordinary user questions are
sent to the configured Gemini API for embedding. For generated answers, the question
and retrieved excerpts are also sent to Gemini. Review Google's applicable
terms/privacy settings before use. Safety-routed urgent questions do not get sent to
Gemini. The app does not monitor users or contact emergency services.

Feedback is stored in `storage\feedback.csv` with a UTC timestamp, random anonymous
session identifier, feedback category, and generic technical label. Question text is
not stored. Use the app's delete button or delete that specific file to remove feedback.
The local index and extraction artifacts can be removed and regenerated; do not
distribute those artifacts without reviewing their contents.

## Attribution and license

Primary source: **UBC Student Health and Wellbeing Staff, Jewell Gillies, Barbara
Johnston, Liz Warwick, Dagmar Devine, Jenny Guild, Arica Hsu, Hamza Islam, Mehakpreet
Kaur, Malena Mokhovikova, Jackson Mackenzie Nicholls, and Calla Smith. (2021).
_Starting a conversation about mental health: Foundational training for students_.
BCcampus.** <https://opentextbc.ca/studentmentalhealth/>

The official BCcampus book page identifies the book content as available under the
[Creative Commons Attribution 4.0 International license (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
Attribution should be retained when reusing or redistributing book material. The book
page separately credits its cover image to Leo Rivas via Unsplash; that third-party
image is governed by the [Unsplash License](https://unsplash.com/license), not assumed
to be covered by the book's CC BY license. This prototype does not redistribute the
PDF through Git; `data\*.pdf` is ignored.

## Evaluation

See [EVALUATION.md](EVALUATION.md) for the initial plan and
[docs/evaluation_methodology.md](docs/evaluation_methodology.md) for the Week 4
20-question evaluation dataset, metrics, and Windows commands. Run retrieval evaluation
with `python -m evaluation.run_evaluation`; generated answer evaluation is an explicit
opt-in via `--generate` because it sends test prompts and excerpts to Gemini and may
use quota. Run deterministic safety-routing checks with
`python -m evaluation.run_safety_tests`. After human annotation, recalculate metrics
with `python -m evaluation.score_results <results.csv-or-json>`. Reports are timestamped
in `evaluation/results/` and excluded from Git. The user test template is
`evaluation/user_testing_template.csv`; no participant outcomes are pre-populated.
Targets remain proposed until real review/testing confirms them.

## Troubleshooting

- **Missing PDF:** place it at `data\mental_health_book.pdf`, or set `PDF_PATH`.
- **No extracted text:** inspect `storage\extraction_report.json`; scan-only pages
  require a deliberate OCR process outside this prototype.
- **Index missing/stale:** run `python scripts/build_index.py` again.
- **Embedding dimension/configuration error:** use the same `EMBEDDING_PROVIDER` and
  model configuration for indexing and app startup, then rebuild the index.
- **Missing key/model:** set local `.env` values. Never commit `.env`.
- **Gemini rate limit/network/API error:** wait, check account access and model
  availability, then retry. The app reports the failure rather than fabricating an
  answer.
- **Unsupported question:** retrieval may return no sufficiently relevant passage;
  rephrase it or consult an appropriate qualified professional or official resource.
