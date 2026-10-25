# Final v0.1 engineering verification

**Verification date:** October 25, 2026. **Target:** a trusted, single-user Linux workstation, local SQLite/artifacts, loopback Streamlit, configured Ollama inference.

The required P0/P1 application pieces from the original writeup are implemented and mapped to evidence in [requirements.md](requirements.md). This is a functioning local application and an empirical evaluation harness. It is not a claim that the central research hypothesis has been established, that arbitrary scientific prose is automatically provable, or that the application is suitable for public multi-tenant deployment.

## Final acceptance

| Check | Actual result |
|---|---|
| Full acceptance suite, including real local inference and local process lifecycle tests | **158 passed, 0 failed, 0 skipped** in 54.10 seconds |
| Machine-readable test evidence | `artifacts/verification-v2/acceptance.xml` |
| Streamlit interaction/presentation cases within that suite | **20 passed**, covering setup, validation, discovery, start/stop/resume, real recorded charts, exports and comparisons |
| Numerical scientific cases | **10 passed**, including reproducibility, disjoint sampling, correction reference, invalid inputs, timeout and artifact boundaries |
| Durable lifecycle | Real subprocess pause during scripted test-only HTTP inference, manager restart, resume, and replay benchmark completion passed |
| Package build | Final `slothlab-0.1.0-py3-none-any.whl` built successfully; artifact and checksum in `dist/` |
| Separate wheel installation | Installed in `/tmp/slothlab-installed`, outside the source checkout; resolved 7 domain and 8 behavioral fixtures plus finite demo criteria |
| Actual installed-wheel science | Seed-7 experiment completed and reproduced the previously measured Brier/log-loss values |
| Static validation | Application compilation and `git diff --check` passed |
| CI | Python 3.12/3.13/3.14 workflow provided; the local acceptance run used **Python 3.14.4**, not all CI matrix interpreters |

Acceptance command:

```bash
SLOTHLAB_TEST_OLLAMA=1 OLLAMA_MODEL=llama3.2:1b \
  .venv/bin/pytest -q --junitxml=artifacts/verification-v2/acceptance.xml
```

Offline runs intentionally skip the opt-in real-model case and may skip the socket lifecycle fixture where the execution environment forbids opening local sockets. The final acceptance above had those permissions and exercised them.

## Implemented application

- Browser investigation setup, installed-model discovery, bounded background start, pause/resume, automatic progress refresh, queue state/logs, experiment charts, hypotheses, decisions, findings and provenance.
- Browser launch/stop of real-model or explicitly labeled replay comparisons, discovered comparison outputs and side-by-side plots.
- Fully independent CLI: init/run/demo/resume/status/report/benchmark/dashboard plus experiment/reference/doctor/jobs/stop.
- Strict shared schemas and finite authorization/completion contracts; compact model-facing scientific choices without asking the model to invent application IDs or timestamps.
- Real hypothesis generation, autonomous parameter/seed selection, numerical interpretation, evidence-grounded revisions that create new untested hypotheses, and preserved original declarations.
- Exact verified reuse, independent replication groups, inspectable weighted priorities, normalized repetition checks, bounded schema/semantic repair, low-information and hierarchical stopping.
- One final held-out confirmation batch, optionally with multiple condition groups, phase-correlated seeds and at least three independent seeds per condition. All predeclared confirmation work is retained before completion checks.
- Transactional SQLite/WAL scientific memory, immutable session/ownership/budget metadata, atomic flushed job/result receipts, per-session locks, safe PID ownership checks and crash reconciliation.
- Real worker wall/CPU/memory limits and resource telemetry; optional rootless Bubblewrap with explicit fail-closed strict mode and documented weaker fallback.
- Markdown, printable escaped HTML, CSV and JSON reports, with original result IDs, parameters, artifacts, hashes, environment versions, scoped numerical findings and honest missing telemetry.
- Separate evidence coverage and finite scientific-quality rubric, diagnostic independent-seed Student-t intervals, verified independent reference grids, repeated paired comparisons, counterbalanced arm order and failure/source/constraint checks.
- Model weight-digest provenance for new real-model sessions. Missing legacy digests remain unverified rather than being reconstructed after the fact.

See [architecture](architecture.md), [protocol](experiment_protocol.md), [UI](ui.md), [evaluation](evaluation.md), and [operations](operations.md) for the actual contracts and boundaries.

## Real model-driven investigations

### Independent follow-up and revision

A `llama3.2:1b` investigation executed two distinct exploratory seeds, **0 and 1**, interpreted their stored measurements, and recorded one evidence-linked hypothesis revision. It made **5 inference calls**, used **6,084 reported tokens**, and took **221.073 seconds**. It ended at its two-experiment budget with insufficient confirmation; it did not falsely establish a general claim.

Runtime memory: `artifacts/verification/iteration/live.sqlite`.

### Exploration → final confirmation → COMPLETED

A real `qwen3:0.6b` run, with thinking explicitly disabled, completed its declared scoped protocol:

| Item | Measurement |
|---|---:|
| Actual executed experiments | **5** |
| Exact result reuses | **1** |
| Exploratory independent seeds | **1, 2** |
| Final independent confirmation seeds | **10000, 10001, 10002** |
| Inference calls / reported tokens | **5 / 10,712** |
| End-to-end wall time | **430.493 seconds** |
| Final state | **COMPLETED**, predeclared operational criteria satisfied |

The confirmed condition used sample size 500, train prevalence 0.5, oracle evaluation prevalence 0.2, separation 1 and probability temperature 1. All three confirmatory delta-Brier values were negative, with mean **−0.0061867449** and sample standard deviation **0.0060189197**. The diagnostic 95% interval was **[−0.0211385704, 0.0087650805]**: it spans zero. Consistent signs satisfy this declared engineering protocol; they are **not** a statistical-significance or universal-generalization claim.

The full real evidence, configuration, decisions, report HTML/Markdown, CSV and JSON snapshot are in [examples/complete-investigation](examples/complete-investigation/README.md). Local runtime memory: `artifacts/verification/iteration/completion-correlated.sqlite`.

Initial unsuccessful trials are preserved. They exposed invalid early confirmation, phase/seed mismatches, repeated work and CPU inference timeouts. The final implementation correlates phases/seeds in the output schema, performs bounded semantic batch repairs and validates completion deterministically. No failed run was relabeled successful.

## Measured evaluation

### Seven scientific domain scenarios

A fresh fixed-proposal replay executed real science across **7 scenarios × 3 modes = 21 arms**, with **zero execution failures** and one consistent scientific source version.

| Mode | Executed | Exact reuses | Summed wall seconds |
|---|---:|---:|---:|
| Baseline | 66 | 0 | 79.716 |
| Cache-only | 49 | 17 | 66.241 |
| Full LazyLoop | 49 | 12 | 61.488 |

Each optimized mode avoided **25.76%** of baseline executions. Per-scenario scientific rubric scores matched; the duplicate-only case legitimately had insufficient confirmation in every mode. Full mode also stopped repeated duplicate-only planning earlier. These are **replay** results with zero inference calls, not an autonomous-efficiency conclusion.

The initial adverse replay, where an early soft stop skipped known future confirmation, remains archived. The regression was corrected by retaining predeclared independent work, then a fresh complete run produced the table above. See [evaluation](evaluation.md).

Actual outputs: `artifacts/verification-v2/final-replay/`; snapshot: [examples/evaluation-v2](examples/evaluation-v2/README.md).

### All eight required behavioral fixtures

The separate acceptance suite ran **8 fixtures × 3 modes = 24 arms**:

- **63 real executions**, **16 exact reuses**, and **zero execution failures**.
- Baseline executed **27** experiments; each optimized mode executed **18**.
- **9 invalid/unauthorized proposals** were rejected before execution.
- Resource-constrained proposals were deferred, while authorized lower-cost work executed.
- Finite evidence-sufficiency cases reached COMPLETED; the premature-stop fixture retained all four declared confirmations even though the minimum was three.
- Every audited arm reported **zero detected known-protocol premature stops**. This audits declared protocol obligations, not unknowable universally optimal stopping.

Actual outputs: `artifacts/verification-v2/behavioral-replay/`; snapshot: [examples/behavioral-v2](examples/behavioral-v2/README.md).

### Repeated real autonomous comparison

The real-model study ran **3 independent paired trials × 3 modes = 9 arms** with cold databases, matching per-trial constraints, disjoint scientific seeds across trials and counterbalanced arm order. All arms completed without infrastructure failure. The deliberately small budget allowed two exploratory experiments per arm and **no sufficient confirmation**.

| Mode | Executed | Exact reuses | Model calls | Reported tokens | Summed wall seconds |
|---|---:|---:|---:|---:|---:|
| Baseline | 6 | 0 | 9 | 12,640 | 268.159 |
| Cache-only | 6 | 0 | 9 | 12,767 | 446.089 |
| Full LazyLoop | 6 | 0 | 9 | 12,544 | 461.955 |

The finite scientific rubric differences were zero in all three paired trials. There was **no reduction in executed experiments**, and token/wall intervals did not establish a compute benefit. The report correctly returns **INSUFFICIENT_CONFIRMATORY_EVIDENCE** for the central research hypothesis. Shared-machine activity, inference/model warmup and a concurrent verification run also limit interpretation of these descriptive wall times. These older study arms did not capture cryptographic model digests; they are explicitly marked unverified for weight identity.

This is an actual low-budget autonomous comparison, **not** evidence that LazyLoop achieves the research hypothesis at scale. Larger confirmatory budgets and more independent objective/model trials remain necessary as scientific work, rather than missing application plumbing.

Actual outputs: `artifacts/verification-v2/autonomous-repeated/`; snapshot: [examples/autonomous-repeated](examples/autonomous-repeated/README.md).

### Independent reference grid

Six real reference experiments characterized two conditions using three seeds outside all exploration/confirmation partitions. The shifted mean was approximately **−0.0136941**, with 95% interval **[−0.0624253, 0.0350370]**; that direction is unresolved. The no-shift control mean was **0.0**. Reference data was used only for final checks, never supplied to planning.

The loader verifies the summary against its own persisted SQLite evidence, parameters, seeds and artifact hashes. Deleting or tampering with supporting artifacts invalidates it. Actual output: `artifacts/verification-v2/reference-grid/reference.json`; snapshot: `examples/evaluation-v2/reference.json`.

## Release boundary and remaining limits

- **Local single-user application:** loopback only; public authentication, tenancy, distributed workers and cloud infrastructure are explicit non-goals.
- **Host-dependent OS isolation:** the verification host blocks unprivileged namespaces. Strict Bubblewrap fails closed; successful namespace execution is not claimed. The tested automatic fallback uses only trusted registered functions, resource limits and Python guards and is explicitly weaker than OS isolation.
- **Visual review:** Streamlit interaction tests pass, but this environment supplied no usable interactive browser for pixel/screenshot review. That review is not claimed.
- **Scientific interpretation:** finite numerical protocols and a transparent rubric are implemented. Arbitrary natural-language scientific truth, significance, multiplicity correction and generalization are not certified. The central hypothesis remains unestablished by the measured autonomous study.
- **Reproducibility:** preserve datasets, receipts, source/dependency versions, model weights and local artifact paths. The final model-provenance feature cannot retroactively pin older mutable tags. Example snapshots retain absolute verification-machine paths; large raw runtime artifacts remain locally ignored files.
- **Optional future scope:** semantic embeddings, learned scheduling, advanced Bayesian experimental design, external tracing, additional experiment families, internet/literature research and model training are not required MVP dependencies and were not added.

No failing acceptance case is known at release verification. This does not replace independent deployment/security review or prove universal research competence. Recommended scientific next step: adequately funded repeated autonomous investigations with independent confirmation/reference data, followed by the existing separate quality-and-compute analysis.
