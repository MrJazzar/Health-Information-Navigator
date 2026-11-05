# Week 5 Conversation Flow

This flow describes the implemented Streamlit + FastAPI behavior. Streamlit sends requests to a local Python API; the API performs safety checks before index access and model calls. It is a single-question navigator, not a persistent chat transcript. Relevant implementation: [app.py](../app.py), [api.py](../api.py), [src/backend_service.py](../src/backend_service.py), and [src/safety.py](../src/safety.py).

```mermaid
flowchart TD
    Start([Open navigator]) --> Welcome["Welcome, purpose, source, limitations, and privacy notice"]
    Welcome --> Input["Enter one question"]
    Input --> Empty{"Input empty?"}
    Empty -->|Yes| EmptyMessage["Ask the user to enter a question; no lookup or model call"]
    EmptyMessage --> Input
    Empty -->|No| API["POST /api/ask to local FastAPI backend"]
    API --> Safety["Run local safety and privacy checks first"]

    Safety -->|Urgent, professional-care, private-record, emergency-number, or detected email/phone| LocalReply["Show the matching local response; do not call Gemini"]
    LocalReply --> APIReply["Return local response to Streamlit"]
    APIReply --> UI
    LocalReply -->|Urgent or needs support| Handover["Direct to trusted person, qualified professional, or official local service"]
    Handover --> NoTransfer["State that the app does not monitor, dispatch, or contact anyone"]

    Safety -->|Normal educational question| Index["Load and validate local PDF index"]
    Index -->|Missing, stale, or unreadable| IndexError["Explain index/PDF problem; offer Retry and rebuild guidance"]
    IndexError -->|Retry| Safety
    Index -->|Ready| Retrieve["Embed query and rank passages with local cosine similarity"]
    Retrieve --> Found{"Relevant passages found?"}
    Found -->|No| Fallback["Explain that the source is insufficient; suggest rephrasing or an official resource"]
    Fallback --> UI
    UI -->|Rephrase and submit| Input
    Found -->|Yes| Generate["Send question and retrieved excerpts to configured Gemini model"]
    Generate -->|API error, empty response, or unsupported answer| ModelError["Show a safe fallback and non-secret recovery guidance"]
    ModelError -->|Retry same question| Safety
    Generate -->|Response| Cite["Attach citations from retrieved page metadata"]
    Cite --> Answer["Show answer and source passages"]
    Answer --> Controls{"User action"}
    Controls -->|Simplify Answer| Simplify["POST /api/action; retrieve passages and simplify in backend"]
    Controls -->|Suggest an Alternative| Alternative["POST /api/action; retrieve passages and generate in backend"]
    Controls -->|Show Sources| Sources["Open the retrieved-passage and page details"]
    Simplify --> Answer
    Alternative --> Answer
    Sources --> Answer
    Answer --> Feedback["Helpful / Not Helpful / Report an Issue"]
    Feedback --> LocalFeedback["Store timestamp, anonymous session ID, category, and generic label locally; do not store question text"]
```

## Behavior and boundaries

- Safety checks run before index access, embeddings, retrieval, and answer generation. Safety-routed messages are handled locally.
- Streamlit calls the local API for questions and answer-control actions. It does not call Gemini directly.
- The privacy route covers private-record requests and obvious email/phone patterns. This is not a comprehensive detector for names, addresses, or all personal information; the input notice still asks users not to share identifying or sensitive details.
- Empty retrieval has a source-limited fallback. The user can rephrase and submit again; the app does not claim that repeating the same query will create new evidence.
- API, retrieval, PDF, embedding, and Gemini failures produce a safe explanation and a Retry action. Retrieval errors also direct the user to rebuild the index when appropriate.
- Show Sources toggles the retrieved evidence panel. Simplify and Alternative reuse the existing answer-generation functions and retain citations from retrieved metadata.
- Human handover is guidance only. The app does not transfer a conversation, contact a person, dispatch services, or monitor the user.
- Feedback is local and question-free. The local delete control remains available.
