# Appearance, profiles, portable guests, and learning verification

Verified October 25, 2026 for version 0.2.0.

- Full acceptance suite: **214 passed, zero skipped or failed**, including live Ollama and local HTTP job lifecycle tests. Evidence: `artifacts/verification-qol/acceptance.xml`.
- Light, Dark, and browser System preferences cover the workspace and chart surfaces. Browser persistence JavaScript is exercised with Node; Streamlit interactions are checked with AppTest.
- Local profiles remember a random browser token and keep separate research histories. They are local conveniences, not cross-device accounts. Anonymous account-mode sessions cannot open the operator's shared history.
- Guest research uses temporary JSON documents and artifact files. Tests prohibit SQLite connections while exercising execution, reuse, reports, comparisons, and reference generation. Both SQLite and document jobs pass pause/resume lifecycle tests.
- Portable ZIP bundles validate archive paths, size limits, relational closure, and artifact hashes before import. Import does not execute research; resuming imported configurations requires review. All-history export is explicit.
- A real Ollama guest investigation (`9cea117875494d3b8e32eb78be41ab28`) executed one scientific experiment, used three model calls and 3,936 tokens, and stopped at its configured planning limit with insufficient evidence. Its history was exported and reopened without SQLite. This verifies integration, not a scientific conclusion.
- The bundled 84-second instructional animation includes captions, chapter seeking, transcripts, research-design guidance, quizzes, and a checklist. All chapter frames were visually inspected. It is an instructional animation, not a recording of a completed investigation.
- The 0.2.0 wheel was built and installed outside the checkout; bundled video/caption assets and JSON storage were verified. Checksums are in `dist/SHA256SUMS`.

No browser automation surface was available for an end-to-end visual browser pass. Actual browser rendering and an external OIDC provider exchange remain unverified; no provider is needed for the requested local profiles or guest mode. AppTest and browser-persistence JavaScript tests passed. The deployment boundary remains a single-user loopback application, not a reviewed public multi-tenant service.

See [identity and history](identity.md), [learning](learning.md), and [AI connections](connections.md). Earlier scientific and release verification remains documented separately in [verification.md](verification.md).
