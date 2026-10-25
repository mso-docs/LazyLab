# Streamlit research workspace

Launch from the checkout root with `slothlab dashboard`. The server is a local, single-user application; keep it bound to loopback and do not expose it directly to the internet. The configured Ollama endpoint handles inference. No model response or scientific finding is simulated by the UI.

## Start research in the browser

Open **New investigation**, enter an installed Ollama model name, and choose your question, permitted prevalences/sample sizes/class separation/temperature, a finite completion protocol, and resource budgets. The completion controls declare exploratory/condition targets, independent confirmation, replicated effect direction and an explicit numerical tolerance. Meeting a finite target is scoped to tested conditions rather than a universal scientific claim. **Discover installed models** queries your chosen Ollama endpoint only when clicked. The advanced settings expose candidate and output limits, experiment timeout/memory inference timeout/context/CPU threads/thinking, and the explicit execution-isolation policy. Automatic isolation can record a weaker fallback; strict Bubblewrap requires the OS boundary and fails closed when unavailable.

**Start investigation** validates configuration and starts a durable local worker process. Research continues across browser refreshes and tab closure. The execution queue records its state and log; **Stop run** asks the worker to stop. Use **Resume investigation** for a nonterminal persisted session after an interruption or user stop. Terminal sessions retain their original termination reason; start another investigation for additional work.

## Follow evidence

The **Research** workspace selects sessions from your configured SQLite memory. While background jobs are active, the research region refreshes every three seconds. Experiments show actual persisted Brier/log-loss measurements. A negative delta means correction reduced loss. Reused results retain original identities and do not create independent replications.

The overview includes hypotheses, the latest deterministic decision, compute usage and a measurement chart. The proposal ledger includes execution, reuse and deferred/rejected actions with original result links; reuse never invents a new measurement. The original measurement table exports to CSV. The trace exposes rejection/reuse/replication explanations and score components. Findings distinguish provisional model interpretation from deterministic protocol checks and display confirmatory seed counts. **Provenance & export** downloads evidence JSON and prepares Markdown and printable standalone HTML reports with result IDs, parameters and environment/artifact references.

Missing telemetry is shown as **Unknown**. An empty memory does not fabricate an active investigation. Invalid configuration, unavailable inference, malformed comparison files and unreadable databases produce actionable in-app errors.

## Compare modes

**Comparisons → Run a comparison** launches real autonomous evaluation or explicitly labeled fixed replay as a background job. The form shows the scenario × three modes × trial count before launch; autonomous comparisons require an installed model. Stop controls also apply to benchmarks.

**Comparisons** automatically discovers `comparison.json` under the selected artifact directory’s `benchmarks/` tree. A custom comparison path is also accepted. Charts show executions and runtime separately from the evidence-coverage score. Select scenarios and inspect trial rows before interpreting means. Fixed replay is explicitly labeled as controller evaluation without autonomous model planning.

## Configuration

The sidebar controls the SQLite memory and artifact directory. Defaults come from `SLOTHLAB_DB_PATH` and `SLOTHLAB_ARTIFACT_DIR`; `SLOTHLAB_JOB_DIR` controls durable worker metadata (default `artifacts/jobs`). `OLLAMA_BASE_URL` and `OLLAMA_MODEL` supply initial connection values. Session configuration snapshots remain in scientific memory for resume.

The UI uses only local CSS and system fonts: no external assets, analytics, remote fonts or CDNs are loaded. Streamlit AppTest coverage exercises start validation, model discovery, resume/stop service calls, persisted measurements and exports, comparison rendering, missing/corrupt storage, and unknown telemetry.
