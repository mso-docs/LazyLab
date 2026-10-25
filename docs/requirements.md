# Original writeup: implementation and evidence audit

This audit maps the [submitted specification](specification.md) to the implementation. “Implemented” means the capability exists and has inspectable code/tests; it does **not** mean an empirical research hypothesis has been proven. The [verification report](verification.md) is the authority for the latest full test result, installation checks, real-model runs and measured benchmark outcomes.

The intended release boundary is a local, single-user Linux application. Unrestricted execution, public multi-user hosting and cloud dependencies are explicitly outside the original v0.1 scope. Host-dependent OS isolation and unavailable interactive browser inspection are called out rather than silently marked verified.

## P0: scientific execution, autonomy and evidence

| Required piece | Implementation | Evidence and scope |
|---|---|---|
| Installable Python 3.12+ application, configurable local inference | `pyproject.toml`, `config.py`, `models/ollama_client.py`, packaged defaults in `slothlab/data/` | `tests/test_installation.py`, `tests/test_models.py`; actual wheel/live status in verification |
| Strict data contracts and JSON round trips | `schemas.py`; all requested objective/hypothesis/spec/result/decision/session contracts | `tests/test_contracts.py`, `tests/test_memory.py`; extra/non-finite/invalid inputs rejected |
| Controlled label-shift generation without leakage | `experiments/calibration.py`: shared class-conditional pool, disjoint stratified samples | `tests/test_science.py`; reproducibility, disjoint indices and independent correction reference |
| Prior correction and required scientific metrics | Logistic regression, oracle prior adjustment, Brier/log loss and signed deltas | Real scientific reports and tests; oracle prevalence is explicit, never implied to be known in deployment |
| Registered validated execution | `experiments/registry.py`, `executor.py`, `worker.py` | Real subprocess integration tests; no model-generated code or unrestricted shell interface |
| Time/resource/output limits and failure reporting | Worker wall/CPU/address-space limits, generated output directories, resource telemetry and structured failures | `tests/test_science.py`, `tests/test_recovery_isolation.py`; actual boundary recorded per result |
| OS isolation or explicitly documented fallback | `experiments/isolation.py`: rootless Bubblewrap probe, strict fail-closed mode, explicit subprocess fallback | Command/fail-closed paths tested; namespace success is host-dependent and was unavailable on the verification host; see operations/doctor |
| Hypotheses, proposals, interpretation and revisions from real inference | `agent/planner.py`, `orchestrator.py`, `critic.py`; compact structured schemas and evidence-linked revisions | `tests/test_models.py`, `tests/test_research_protocol.py`, real-model runs in verification; model quality is empirical, not guaranteed |
| Explicit persisted finite-state machine | `agent/orchestrator.py` state graph and checkpoints | Multi-round state, bounded malformed repair, completed/stopped/failed and recovery tests |
| Persistent sessions, objectives, hypotheses, specs/results, evidence, decisions and budgets | Transactional SQLite repository with foreign keys/WAL, immutable identities/ownership and local artifacts | `tests/test_memory.py`, `tests/test_runtime_review.py`; cross-session result reuse preserves original identity |
| Resume interrupted work | Session locking, atomic committed result receipts, reconciliation, persisted model/execution reservations | `tests/test_research_protocol.py`, `tests/test_recovery_isolation.py`, `tests/test_job_lifecycle.py`; incomplete output is never reused as successful |
| Exact-result deduplication, canonical provenance and valid replication | SHA-256 structural identity, source/environment versions, numerical/artifact checks; distinct independent seeds and groups | `tests/test_science.py`, `tests/test_agent.py`, `tests/test_memory.py`; failed/unverified results excluded |
| Candidate validation and observable heuristic priorities | `lazyloop/controller.py`, config bounds, allowed phases, cost and replication-group constraints | Hard parameter/seed/phase/resource authorization tests; score cannot override a limit |
| Budgets, loop prevention and adaptive stopping | Global experiment/round/candidate/wall/token limits, bounded repairs, structural repetition/progress checks | `tests/test_agent.py`, `tests/test_budget_accounting.py`, `tests/test_research_protocol.py`; unknown telemetry stays unknown |
| Deterministic operational completion | `lazyloop/stopping.py`: distinct conditions, exploration target, independent confirmation, effect direction/tolerance | Completion tests require predeclared criteria; arbitrary prose is not falsely certified |
| Evidence-grounded summaries and reports | `reporting/generator.py`; Markdown/HTML/CSV/JSON exports with IDs, parameters, hashes, decisions and caveats | `tests/test_evaluation_reports.py`, `tests/test_memory.py`; printable HTML escapes generated prose |

## P1: convincing evaluation, presentation and packaging

| Required piece | Implementation | Evidence and scope |
|---|---|---|
| Baseline, cache-only and full LazyLoop | `evaluation/benchmark.py`; shared hard limits/tools, mode-specific optimizations | `tests/test_benchmark.py`; cold databases, constraint signatures and independent inspectable arms |
| Scientific scenario coverage | Seven bundled YAML objectives and explicit replay schedules: prevalence shift, no shift, sample size, replication, repeated proposals, mixed outcomes, miscalibration | Domain scenarios in `benchmarks/objectives/` and package data; behavioral acceptance fixtures are mapped separately below |
| Repeated reproducible comparisons | Disjoint trial seeds paired across modes, rotating arm order, atomic partial comparisons | `tests/test_benchmark.py`; failures remain visible; current actual repeated-run coverage in verification |
| Computational telemetry | Model calls/tokens/inference time, wall time, actual executions, cache hits, redundant proposals, failed arms and supported resource telemetry | Benchmark/report accounting tests; interrupted or unavailable measurements are not fabricated zeros |
| Scientific quality separate from compute | `evaluation/quality.py`: integrity, independent confirmation, applicable identity controls and claim/evidence calibration; coverage retained separately | `tests/test_evaluation_quality.py`; transparent finite rubric, not universal scientific truth |
| No unjustified “less compute is success” claim | `evaluation/metrics.py`: repeated paired quality/compute intervals, confirmation coverage, mismatch/failure checks | Tests reject degradation, missing repeats, protocol mismatches and absent confirmation; replay verdict explicitly excludes autonomy |
| Independent reference characterization | `evaluation/reference.py`: cold registered-science grid, independent seeds, final-only comparison, summary verified against stored evidence | `tests/test_evaluation_reference.py`; never included in planner context; unresolved/noisy reference directions are not truth labels |
| Required CLI commands | `init`, `run`, `resume`, `status`, `report`, `benchmark`, `dashboard`, `demo`; plus `experiment`, `reference`, `doctor`, `jobs`, `stop` | `tests/test_cli.py`, `tests/test_installation.py`, runtime review tests; CLI does not import Streamlit for scientific work |
| Dashboard overview/history/trace/findings/efficiency | `ui/dashboard.py`, presentation helpers and local CSS | Streamlit AppTest covers persisted state, unknown telemetry, actual charts, provenance, export and comparisons |
| Interactive start/resume/stop and durable progress | `runtime/jobs.py`, `job_worker.py`, browser forms and periodic fragments | AppTest validates service calls/authorization; lifecycle tests exercise real background processes with labeled scripted inference fixtures |
| Scientific/runtime auditability | State/event/decision/evidence traces, error logs, source/dependency fingerprints, readable reports | Repository/report/runtime tests and actual example artifacts |
| Setup, demo, architecture, protocol, evaluation and troubleshooting docs | README, `.env.example`, docs and bundled package assets | Installation/asset tests; docs map to supported CLI/config keys |
| Final engineering report | `docs/verification.md`, measured examples and this requirements audit | Actual results and limitations are reported separately from intended capability |


## Behavioral benchmark-fixture acceptance

All eight required behaviors have standalone deterministic replay fixtures, in addition to the scientific domain suite and integration tests:

| Original behavior | Runnable fixture |
|---|---|
| Exact duplicate detection | `benchmarks/behavioral/exact_duplicate.yaml` |
| Valid scientific replication | `benchmarks/behavioral/valid_replication.yaml` |
| Contradictory experimental evidence | `benchmarks/behavioral/contradictory_evidence.yaml` |
| Invalid parameter proposals | `benchmarks/behavioral/invalid_parameters.yaml` |
| Repeated unproductive planning | `benchmarks/behavioral/repeated_planning.yaml` |
| Resource-constrained selection | `benchmarks/behavioral/resource_constraints.yaml` |
| Evidence sufficiency and legitimate stopping | `benchmarks/behavioral/evidence_sufficiency.yaml` |
| Premature stopping risk | `benchmarks/behavioral/premature_stop_risk.yaml` |

Each YAML has a predeclared adjacent `.replay.json` schedule. `manifest.json` maps the acceptance cases. Run all with `slothlab benchmark --suite benchmarks/behavioral --replay`. These schedules execute real scientific functions; intentionally invalid proposals are recorded as rejected without execution, and resource estimates are explicitly estimates. Replay is not a substitute for autonomous model evaluation. Tests additionally cover malformed model output, interrupted confirmation, and persistence/authorization failures.

## Definition-of-done interpretation

The original definition requires a working research loop, registered reproducible science, persistent memory, reuse without suppressing replications, enforceable limits, explicit stops, baseline comparison, separately measured quality/cost, reports, optional UI, passing tests and real setup commands. The code paths and test evidence for those items are mapped above; final executed validation is recorded in verification rather than copied into an unmaintained checklist.

A scientific investigation can validly end with **evidence insufficient**, mixed outcomes, budget exhaustion, no viable experiments, repeated unproductive planning or execution failure. `COMPLETED` is reserved for explicit finite criteria. It does not mean the program solved an arbitrary scientific question or established a general law. The central hypothesis can remain unresolved or fail even when the application is functioning correctly.

The full three-mode research conclusion must be based on actual repeated autonomous runs and the declared scientific rubric. Fixed replay demonstrates controller behavior and resource accounting. It is not quietly substituted for real inference and does not establish preserved autonomous research quality.

## Optional P2 and long-term research

The original writeup makes these optional or future work, so their absence is not an unfinished required MVP dependency:

- Semantic embeddings/Sentence Transformers and vector similarity, only after exact/structural detection is proven worthwhile.
- Learned scheduling, reinforcement learning, advanced expected-information-gain or Bayesian experimental design.
- External tracing platforms, distributed experimentation, richer scientific domains or additional experiment families.
- Dynamic model selection, fine-tuning, long-horizon hierarchical research memory and local-document retrieval.
- Expected calibration error and reliability diagrams were optional metrics. Independent-seed Student-t intervals are implemented, but do not supply multiplicity correction or universal statistical guarantees.

## Explicit non-goals preserved

No arbitrary internet/literature search, unrestricted shell, generated-code execution, self-modifying application, model-weight updates, multi-user authentication, cloud dependency, general-purpose simulation, autonomous publication or external communication is implemented. These remain excluded by the specification rather than being silently claimed complete.

## Operational verification limits

- The host must support Bubblewrap/user namespaces for the implemented OS filesystem/network boundary. Strict mode fails closed; automatic fallback is explicit and weaker.
- Browser behavior is covered by Streamlit AppTest. An interactive browser/pixel review was unavailable in the implementation environment and is not claimed.
- Model planning quality depends on the configured model and resources. Real observations and failures are retained; no deterministic fake client is used as an application fallback.
- Source/metadata hashes and verified artifacts support reproducibility, not a guarantee across arbitrary numerical libraries, hardware changes or deleted/migrated files. Preserve complete evidence when backing up or sharing research.

See [operations](operations.md) for the actual deployment boundary and recovery procedures, and [verification](verification.md) for current acceptance results and measured research limitations.
