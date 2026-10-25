# Local operation and deployment

SlothLab v0.1 is a **single-user Linux application bound to loopback**, using a local filesystem and SQLite. Its production boundary is a trusted user's workstation or dedicated host with explicit resource limits. It does not include public-service authentication, tenant isolation, cloud infrastructure, or distributed workers; those are original non-goals rather than hidden deployment guarantees.

## Installation and readiness

Use Python 3.12+ and an installed Ollama server/model. The backend can be installed independently of Streamlit:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .                  # CLI / scientific engine
python -m pip install -e '.[dashboard]'    # add the browser workspace
slothlab init
slothlab doctor --skip-model
export OLLAMA_MODEL='your-installed-model'
slothlab doctor
```

`doctor` reports dependency versions, configured/installed models, endpoint reachability and the host's Bubblewrap capability. An unavailable configured model or unavailable strict Bubblewrap policy makes readiness fail. In `auto`, readiness can be true with a documented weaker execution fallback; inspect the `isolation` details, not only the boolean.

`slothlab dashboard --port 8501` starts Streamlit on `127.0.0.1` and disables usage-stat gathering. Use another local port if necessary. The application loads local CSS and system fonts rather than third-party assets. Do not expose it directly through a public bind address or reverse proxy without independently adding authentication, transport protection and an appropriate threat-model review.

Bundled `demo`, default calibration config and benchmark objectives resolve from installed package data when not present in the current directory. Custom YAML remains an explicit user-managed path. The tested installation commands and latest isolated-wheel check are recorded in [verification](verification.md).

## Configuration and resources

The browser and YAML use the same Pydantic contracts. Exported environment variables override model, endpoint, memory and artifact paths; `.env` files are not implicitly loaded. `.env.example` documents the supported variables, including the durable job metadata location.

| Setting | Purpose |
|---|---|
| `OLLAMA_MODEL` / `model` | Installed inference model; never auto-downloaded |
| `OLLAMA_BASE_URL` / `base_url` | HTTP(S) Ollama endpoint, without embedded credentials |
| `SLOTHLAB_DB_PATH` / `db_path` | SQLite scientific memory |
| `SLOTHLAB_ARTIFACT_DIR` / `artifact_dir` | Datasets, receipts, logs, reports and benchmark outputs |
| `SLOTHLAB_JOB_DIR` | Durable job metadata/log root; defaults to `artifacts/jobs` |
| `SLOTHLAB_LOG_LEVEL` | CLI log level |
| `inference_timeout_seconds` | Per-call timeout, further bounded by remaining wall time |
| `inference_context_tokens` | Ollama context size; default 8,192 |
| `inference_threads` | Optional CPU thread count; `null` delegates to the runtime |
| `inference_thinking` | Optional model-supported thinking override: `null`, `false`, `true` |
| `execution_isolation` | `auto`, strict `bubblewrap`, or explicit `subprocess` |

Budgets cap experiment count, planning rounds, candidates, total wall time, tokens, per-experiment timeout and memory. At least three independent seeds are required for the protocol's replicated claims. Candidate capacity must fit a final confirmation batch, including every requested condition group. No priority score overrides these limits.

CPU inference may take minutes. A larger timeout is not a substitute for a total budget. A model with too little context or weak structured-output behavior can repeatedly propose invalid/duplicate work; inspect its trace, choose a suitable installed model, or simplify the authorized domain. Missing token usage and interrupted-call cost remain unknown/conservatively charged rather than zero.

## Durable lifecycle

In the browser, use **New investigation** or **Comparisons → Run a comparison**. In the CLI:

```bash
slothlab run --config my-investigation.yaml --background
slothlab jobs
slothlab stop JOB_ID
slothlab --db /absolute/path/research.sqlite status SESSION_ID
slothlab --db /absolute/path/research.sqlite resume SESSION_ID --background
slothlab --db /absolute/path/research.sqlite report SESSION_ID
```

A job ID identifies an operating-system worker; a session ID identifies scientific history. They are different. Job states are queued, running, stopping, completed, failed or stopped. Scientific terminal states are completed, stopped and failed; a deliberate user pause preserves a nonterminal resumable checkpoint and its reason.

The manager permits one active worker by default, persists atomic metadata, and checks PID creation time before signaling or reconciling a process. Per-session advisory locks reject simultaneous CLI/browser investigators even if they were launched through separate managers. Locks release when the owning process exits. Jobs survive browser refresh and server restart; read their status/logs from the workspace or `slothlab jobs`.

Stopping requests SIGTERM and a resumable checkpoint. A hard process exit may not complete cleanup; metadata is reconciled and evidence remains inspectable. Resume verifies committed worker receipts and artifact hashes before recovering measurements. A fully committed matching result can be recovered without execution; incomplete or changed-protocol artifacts never become successful results. Interrupted work retains its charge. Wall time includes pause/downtime, so an old checkpoint may immediately stop because its original budget has expired.

A terminal investigation is returned unchanged by foreground resume and rejected by background resume. To ask a new question or change the original hard budgets, create a new investigation. Immutable objective identities, session ownership and budgets protect historical provenance.

## Execution boundary

Only trusted registered scientific functions run. Model-generated Python, shell strings, arbitrary command names and network tools are not interfaces. Workers have validated parameters, generated output locations, explicit argument arrays, minimized environments, wall/CPU/memory limits, and Python socket/child-process guards.

| Policy | Boundary and failure behavior |
|---|---|
| `auto` | Probe rootless Bubblewrap. Use private filesystem/network namespaces when available; otherwise record an explicit restricted-subprocess fallback in result metadata. |
| `bubblewrap` | Require the implemented OS namespace boundary. If missing or blocked by host policy, fail closed without running the scientific function. |
| `subprocess` | Explicit weaker mode for trusted registered code. Python API guards and resource limits apply; native extensions retain ordinary OS permissions. |

Bubblewrap mounts only the runtime, application package and experiment output directory needed for execution. Runtime/package mounts are read-only; unrelated host files and host network are absent from the isolated view. This is still a bounded registered-workload design, not a claim that arbitrary hostile code is safe.

The implementation host's user-namespace policy prevented Bubblewrap execution during verification. The fail-closed path, private-network/minimal-mount command construction, and restricted-subprocess path are tested. Successful OS-isolated execution must be checked on the deployment host with `doctor` and a real experiment. Installing `bwrap` alone does not override a host policy that blocks user namespaces.

For strict deployment, put `execution_isolation: bubblewrap` in the investigation YAML, run `slothlab doctor --config my-investigation.yaml`, and resolve capability failures before running research. Do not relabel an `auto` fallback as OS isolation.

## Evidence, backups and retention

Keep SQLite scientific memory, experiment artifacts and their metadata together. Reports link results to hashes and original paths; removing data can intentionally invalidate cache reuse. A reference grid also depends on its original database and artifacts, not only its `reference.json` summary.

For a consistent backup:

1. Pause active workers and confirm their job states have settled.
2. Use SQLite's online backup API for each scientific/reference/benchmark database rather than copying a live database while ignoring its WAL.
3. Archive the corresponding artifact and job directories, user YAML, package/source version and dependency lockfile.
4. Test restoration and result verification before relying on the backup.

Example database snapshot after pausing:

```python
import sqlite3
with sqlite3.connect("artifacts/slothlab.sqlite") as source:
    with sqlite3.connect("backup/slothlab.sqlite") as destination:
        source.backup(destination)
```

Create `backup/` first. Stored artifact references include absolute local paths; restoring only a relocated database is not a portable artifact migration. Preserve/restore the referenced artifact layout or verify any deliberate migration independently. No automatic deletion/retention policy silently removes research history. Archive complete investigations and reference grids together.

## Evaluation operations

Benchmarks use fresh output directories and persist each arm separately. Scenario/model/budget/seed signatures must match before pairs are evaluated. Trial partitions are disjoint between repeats and paired within modes; mode order rotates. Partial or failed arms stay visible rather than aborting or being reported as successful runs.

Fixed replay executes real scientific procedures but no model. It can demonstrate reuse, replication and stopping behavior, not autonomous scientific quality preservation. Real-model quality/compute verdicts require repeated paired evidence under the documented rubric; an independent reference grid is withheld from planning and checked against its persisted measurements. See [evaluation](evaluation.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Model unavailable | Start Ollama, check `OLLAMA_BASE_URL`, use `ollama list`, then select an installed model. No fake fallback exists. |
| Slow or timed-out inference | Inspect worker logs and remaining wall/token budget; choose an appropriate model/context and explicit timeout. A failed call leaves usage unknown. |
| Worker busy / session already running | Inspect `slothlab jobs` or the execution queue. Stop the active worker or wait; do not delete locks for a live process. |
| Paused session cannot complete | Check elapsed global wall time and the immutable original budgets. Start a new investigation if more resources are required. |
| Strict isolation unavailable | Run `doctor`; resolve Bubblewrap/user-namespace policy or deliberately choose and document the weaker trusted-code boundary. |
| Result fails integrity checks | Restore its complete original artifacts. Do not bypass verification or turn incomplete work into a successful cache entry. |
| No scientific conclusion | Inspect completion criteria, required independent seeds and contradictory/mixed evidence. Insufficient evidence is a valid outcome. |
| No comparison visible | Select a discovered `comparison.json` or enter the actual output path. An empty dashboard does not invent results. |
| Dashboard import error | Install the `dashboard` extra in the same environment that runs `slothlab`. |

Current test results and actual measurements are in [verification](verification.md). UI behavior is covered by Streamlit AppTest; browser/pixel review was unavailable in the implementation environment and is not claimed as completed.
