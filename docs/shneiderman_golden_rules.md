# Shneiderman's Eight Golden Rules Checklist

Statuses below describe the current implementation, not a usability-study result. No participant testing has been completed for this checklist.

| Rule | Actual screen/component or flow decision | How it is implemented | Status |
|---|---|---|---|
| 1. Strive for consistency | Main Streamlit page, sidebar, answer controls | The same navigator title, educational warning, privacy notice, question form, and answer area are used on the main screen. Labels follow the existing Streamlit style. There is only one principal workflow, so cross-screen consistency has limited evidence. | Partially Implemented |
| 2. Enable shortcuts | Contextual quick-reply buttons | After a grounded answer, users can invoke Simplify Answer, Suggest an Alternative, or Show Sources directly rather than re-entering the question. Keyboard shortcuts and a broader expert workflow are not implemented. | Partially Implemented |
| 3. Offer informative feedback | Spinner, answer/fallback/error messages, feedback controls | The interface reports work in progress, explains empty or failed requests, shows citations and passages, acknowledges saved feedback, and offers Helpful / Not Helpful / Report an Issue. | Implemented |
| 4. Design dialogs that give closure | Answer display and feedback acknowledgement | A completed response is displayed, safety routes provide a complete local message, and feedback submission receives a confirmation. There is no explicit end-of-session or conversation-closing action. | Partially Implemented |
| 5. Prevent errors and handle them simply | Question form, safety/privacy checks, index loader, retry control | Empty input is rejected; input length is capped; existing safety routes run before retrieval; obvious email/phone patterns and private-record requests are handled locally; index, PDF, embedding, and Gemini errors have safe explanations and recovery guidance. The contact-detail check is limited and cannot detect every kind of identifying information. | Partially Implemented |
| 6. Permit easy reversal of actions | Show Sources / Hide Sources, new question, feedback deletion | Users can open or hide source details, submit a different question (which clears the prior answer state), and delete locally stored feedback. Already-sent external API requests cannot be undone. | Partially Implemented |
| 7. Support the user's sense of control | Source inspection, answer controls, retry, privacy notice, feedback and deletion | Users can inspect the evidence, request a simpler or alternate supported answer, retry a failed request, understand the data flow, and delete local feedback. The app cannot retract a question already sent to Gemini for embedding or generation. | Partially Implemented |
| 8. Reduce short-term memory load | Inline notices, citations, expandable evidence, contextual controls | Scope and privacy information are visible on the question screen; answers retain citations and can be checked against displayed passages; controls are next to the answer they affect. The app is single-question rather than a transcript, so users must restate a question when changing direction. | Partially Implemented |

## Evidence boundaries

- “Implemented” refers only to the listed interface behavior; it does not mean that usability or accessibility has been measured.
- The contact-detail route recognizes common email and phone patterns only. It is not a general personal-information scanner.
- Control discoverability, comprehension, and task success remain unmeasured until the planned user test is conducted.

Implementation references: [app.py](../app.py), [src/safety.py](../src/safety.py), and [src/feedback.py](../src/feedback.py). The existing user-testing method is in [user_testing_plan.md](user_testing_plan.md).
