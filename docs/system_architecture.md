# System Architecture

This diagram follows the current Streamlit + FastAPI implementation. The key design feature is **EXPLAINABILITY AND SOURCE-GROUNDED ANSWERS**: generated answers use retrieved excerpts, and the backend adds citations from the actual retrieved page metadata.

```mermaid
flowchart TD
    User[User] --> UI["Streamlit interface: app.py"]
    UI -->|HTTP on localhost| API["FastAPI backend: api.py"]
    API --> Backend["Question service: src/backend_service.py"]
    Backend --> Safety["Local safety and privacy checks"]
    Safety -->|Non-normal route| LocalResponse["Local response; no Gemini call"]
    LocalResponse --> API
    API --> UI
    Safety -->|Normal question only| IndexLoader["Load/validate local index"]

    subgraph Build["Offline/local index preparation: scripts/build_index.py"]
        PDF["PDF knowledge source"] --> Extract["PDF extraction: pypdf"]
        Extract --> Chunk["Page-preserving text chunking"]
        Chunk --> TextChunks["Inspectable chunks and page metadata"]
        TextChunks --> DocEmbed["Document embedding generation"]
    end

    DocEmbed --> DocProvider{"Configured document embedding provider"}
    DocProvider -->|Gemini| Gemini["Configured Google Gemini API"]
    DocProvider -->|Local| LocalHash["Local feature-hash embeddings"]
    Gemini -->|Embedding vectors| DocVectors
    LocalHash -->|Embedding vectors| DocVectors
    DocVectors["Document vectors"] --> LocalIndex["Local vector index: storage/index.json"]
    TextChunks --> LocalIndex
    TextChunks --> ChunksFile["Readable chunk metadata: storage/chunks.jsonl"]

    LocalIndex --> IndexLoader
    IndexLoader --> QueryEmbed["Generate query embedding using configured provider"]
    QueryEmbed --> QueryProvider{"Configured query embedding provider"}
    QueryProvider -->|Gemini| Gemini
    QueryProvider -->|Local| LocalHash
    Gemini -->|Query vector| QueryVector["Query vector"]
    LocalHash -->|Query vector| QueryVector
    QueryVector --> Retriever["Retriever: local cosine ranking and threshold"]
    IndexLoader -->|Loaded chunks and document vectors| Retriever
    Retriever -->|No relevant passages| Fallback["Source-insufficient fallback"]
    Fallback --> API
    Retriever -->|Top passages and page metadata| AnswerGen["Answer generation: src/answer_generator.py"]
    AnswerGen -->|Question and excerpts sent externally| Gemini
    Gemini -->|Generated answer text| AnswerGen
    AnswerGen --> Citations["Attach verified page citations from retrieved metadata"]
    Retriever -->|Evidence excerpts and scores| Citations
    Citations --> Response["Answer plus expandable source passages"]
    Response --> API
    API --> UI

    UI -->|Simplify / Alternative actions over localhost HTTP| API
    API -->|Retrieve passages and run answer control| AnswerGen

    UI -->|Helpful / Not Helpful / Report an Issue; no question text| Feedback["Local feedback storage: storage/feedback.csv"]
```

## Data-flow notes

- PDF extraction, chunking, persisted chunks/index, and cosine ranking run locally.
- With the default Gemini provider, document chunks are sent to Gemini while building embeddings, and a normal user question is sent for its query embedding. For a generated answer, the question and retrieved excerpts are also sent to Gemini.
- The local feature-hash embedding provider avoids those embedding calls, but answer generation still requires Gemini when a supported answer is requested.
- Safety and privacy routes are evaluated before the retrieval and Gemini paths. They return local messages.
- Streamlit sends question and answer-control requests to the local FastAPI service; it does not call Gemini directly. The API validates request lengths and returns structured answer, source, route, or safe error data.
- The API binds to `127.0.0.1` by default. It is a local development backend and has no authentication; it must not be exposed publicly without additional safeguards.
- Citation text is attached by Python from retrieved page metadata. This confirms citation provenance, not that every generated claim is factually supported by the passage; human review is still needed.
- Feedback records contain a timestamp, anonymous session identifier, category, and generic technical label. They do not contain the question text.

Implementation references: [app.py](../app.py), [api.py](../api.py), [src/backend_client.py](../src/backend_client.py), [src/backend_service.py](../src/backend_service.py), [src/answer_generator.py](../src/answer_generator.py), [src/embeddings.py](../src/embeddings.py), [src/retriever.py](../src/retriever.py), [src/pdf_processor.py](../src/pdf_processor.py), [src/chunking.py](../src/chunking.py), [src/feedback.py](../src/feedback.py), and [scripts/build_index.py](../scripts/build_index.py).
