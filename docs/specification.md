# SlothLab + LazyLoop
## Autonomous Scientific Research Agent — MVP Implementation Specification

**Project:** SlothLab  
**Core subsystem:** LazyLoop  
**Version:** 0.1.0  
**Language:** Python 3.12+  
**Inference:** Local open-weight models via Ollama  
**Target:** Linux / Ubuntu, CPU or GPU  
**Development methodology:** Test-driven, modular implementation  
**Primary deliverable:** Working local application with autonomous experimentation, intelligent stopping, research memory, evaluation benchmarks, and an interactive dashboard.

---

# 1. Instructions for the Implementation Agent

You are the lead software architect and implementation agent responsible for building SlothLab, a self-directed scientific research system governed by LazyLoop, a compute-aware orchestration and execution controller.

Your responsibilities include:

- Inspecting the existing repository, if one exists, before modifying files.
- Designing and implementing a modular, testable Python application.
- Delegating independent implementation tasks to specialized subagents when supported.
- Implementing the research execution engine before adding UI components.
- Creating automated tests for scientific validity, experiment execution, agent decisions, persistence, and stopping behavior.
- Implementing a complete vertical slice before adding optional functionality.
- Maintaining documentation as implementation progresses.
- Running tests and fixing integration issues.
- Providing a truthful final implementation report.

Do not stop at generating architecture diagrams, pseudocode, or placeholder modules. Implement functioning components.

Do not silently substitute simulated LLM responses for real model inference. A deterministic fake model may be used for automated tests, but the actual application must integrate with Ollama.

Do not fabricate scientific measurements, benchmark results, token savings, or experimental findings.

**Execution directive:** Make reasonable engineering decisions autonomously. Only request clarification for genuinely blocking problems. If a dependency or optional integration is unavailable, implement a documented fallback and continue.

---

# 2. Product Vision

SlothLab is an autonomous scientific research agent capable of receiving a scientific objective, proposing hypotheses, designing experiments, running them, evaluating results, and deciding what to investigate next.

LazyLoop is the supervisory system responsible for minimizing unnecessary computation and avoiding unproductive research cycles.

The combined system should answer two questions:

1. What experiment should we perform next to advance the investigation?
2. Is that experiment worth executing given the existing evidence and available computational resources?

The system should favor scientific progress over simply maximizing the number of experiments completed.

## Core research hypothesis

**A compute-aware autonomous research agent can reduce redundant execution and resource consumption while preserving the quality of its scientific investigations.**

This hypothesis must be evaluated empirically.

## Core design principles

1. Local-first execution.
2. Open-weight model compatibility.
3. Scientific reproducibility.
4. Explicit state transitions.
5. Persistent experimental memory.
6. Deterministic execution safeguards.
7. Measurable computational efficiency.
8. Scientific uncertainty must be preserved.
9. No fabricated experimental results.
10. Autonomous decisions within defined execution boundaries.

---

# 3. MVP Scope

## Required capabilities

The initial application must:

- Accept a research objective and a configuration defining the permitted experimental space.
- Generate falsifiable hypotheses using a local LLM.
- Propose experiments through validated structured outputs.
- Evaluate experiment novelty, feasibility, scientific relevance, and estimated cost.
- Select and execute experiments autonomously.
- Analyze results and update its hypotheses.
- Reuse exact prior experimental results.
- Distinguish duplicate work from valid scientific replication.
- Detect repeated unproductive reasoning cycles.
- Terminate when configured stopping conditions are satisfied.
- Resume a previously interrupted investigation.
- Produce a research summary grounded in stored measurements.
- Compare ordinary autonomous execution against LazyLoop-enabled execution.
- Expose research activity and resource usage in a small dashboard.

## Explicit non-goals for v0.1

Do not implement these until required MVP functionality is working:

- Arbitrary internet research.
- Autonomous literature search.
- Unrestricted shell access.
- Arbitrary Python code generated and executed by an LLM.
- Model fine-tuning.
- Model weight updates.
- Self-modifying application code.
- Distributed experiment execution.
- Multi-user authentication.
- Cloud infrastructure dependencies.
- General-purpose scientific simulation.
- Autonomous publication or external communication.

The MVP should support independent scientific decision-making, not unrestricted code execution.

---

# 4. Technology Stack

## Backend

- Python 3.12+
- Pydantic for validated schemas.
- Ollama for local inference.
- NumPy for numerical operations.
- Pandas for dataset and results processing.
- scikit-learn for initial scientific experiments.
- SQLite for persistent application state.
- SQLAlchemy or Python's standard SQLite interface.
- pytest for automated testing.
- psutil for resource monitoring, where supported.

## Frontend

Use Streamlit for the initial interactive dashboard.

The frontend must remain optional. The complete investigation workflow must be operable through the CLI.

## Additional libraries

Use Sentence Transformers for semantic similarity only if exact and structural deduplication are working and profiling demonstrates that semantic detection is worth its additional cost.

Avoid unnecessary vector databases, message brokers, or multi-agent orchestration frameworks.

## Model interface

Implement an interchangeable model-client abstraction with two implementations:

**OllamaModelClient:** Real inference against a configured local Ollama endpoint.

**FakeModelClient:** Deterministic scripted responses for automated tests.

Model selection must be configurable.

Do not hardcode a particular model, GPU, or system configuration.

Relevant environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `SLOTHLAB_DB_PATH`
- `SLOTHLAB_ARTIFACT_DIR`
- `SLOTHLAB_LOG_LEVEL`

The application should detect when Ollama is unavailable, display a clear error, and avoid silently pretending that an investigation ran.

---

# 5. High-Level Architecture

Implement five major subsystems.

## 5.1 Research Orchestrator

Responsible for coordinating an autonomous investigation.

Primary operations:

- Initialize a research session.
- Load the research objective.
- Retrieve existing evidence.
- Generate or revise hypotheses.
- Propose candidate experiments.
- Request LazyLoop decisions.
- Execute approved experiments.
- Analyze observed results.
- Update research memory.
- Evaluate stopping conditions.
- Produce research reports.

Implement an explicit finite-state machine.

Recommended states:

- `INITIALIZED`
- `HYPOTHESIZING`
- `PLANNING`
- `VALIDATING`
- `EXECUTING`
- `ANALYZING`
- `REPLANNING`
- `COMPLETED`
- `STOPPED`
- `FAILED`

Persist state transitions so investigations can be resumed.

## 5.2 LazyLoop Controller

Responsible for compute-aware orchestration.

Implement separate modules for:

- Experiment validation.
- Fingerprinting and deduplication.
- Candidate prioritization.
- Scientific progress tracking.
- Repetition detection.
- Budget enforcement.
- Adaptive stopping.
- Decision recording.

LazyLoop must function independently of the dashboard.

Its decisions must be inspectable.

Each decision should record:

- Proposed experiment ID.
- Selected action.
- Relevant evidence references.
- Estimated cost.
- Available budget.
- Reason for selection or rejection.
- Timestamp.
- Current research session ID.

## 5.3 Experiment Execution Engine

Responsible for executing a limited set of approved scientific procedures.

Requirements:

- Registered experiment families.
- Validated parameter schemas.
- Deterministic random seed handling.
- Isolated execution.
- Execution timeouts.
- Resource limits.
- Structured metrics.
- Reproducible artifacts.
- Exception and failure reporting.

Experiments must run through registered functions rather than arbitrary generated code.

## 5.4 Scientific Memory

Store:

- Research sessions.
- Research objectives.
- Hypotheses.
- Experiment configurations.
- Experiment results.
- Replication groups.
- Evidence references.
- Agent decisions.
- Budget usage.
- State transitions.
- Errors and execution metadata.

Use SQLite for structured information and a local artifact directory for datasets, configuration snapshots, logs, and plots.

## 5.5 Reporting and Evaluation

Responsible for:

- Research summaries.
- Experiment comparison tables.
- Evidence provenance.
- Termination reports.
- Runtime statistics.
- Token and inference usage.
- Baseline comparisons.
- Reproducibility information.

Reports must use actual persisted data.

---

# 6. MVP Scientific Experiment

The initial research domain will be:

**Bayesian prior-probability correction under class prevalence shift.**

This domain was selected because it supports inexpensive, reproducible experiments and meaningful hypothesis-driven investigation.

## Research objective

Determine the conditions under which adjusting predicted probabilities for a change in class prevalence improves predictive performance.

## Dataset generation

Use `sklearn.datasets.make_classification` to generate synthetic binary classification datasets.

Construct training and evaluation datasets with controlled class prevalence.

Support configurable:

- Training prevalence.
- Evaluation prevalence.
- Sample size.
- Random seed.
- Feature count.
- Class separation.
- Noise level, when applicable.
- Logistic-regression parameters.

For the initial implementation, model a label-shift setting where class-conditional feature distributions are preserved.

Generate independent class-conditional samples, or construct disjoint pools with properly controlled sampling.

Do not introduce training/test leakage.

## Statistical experiment

Implement:

1. Generate training and evaluation distributions.
2. Train a logistic-regression classifier.
3. Produce uncorrected probability predictions.
4. Apply a prior-probability correction.
5. Compute evaluation metrics for both methods.
6. Record improvements or regressions.
7. Repeat across justified scenarios and random seeds.

For the initial synthetic experiments, the true test prevalence may be supplied as an oracle input. The application must explicitly identify this assumption.

Do not imply that oracle prevalence is available in a real deployment.

## Metrics

Required:

- Brier score.
- Log loss.
- Difference in Brier score.
- Difference in log loss.
- Experiment runtime.
- Sample size.
- Random seed.

Optional:

- Expected calibration error.
- Reliability diagrams.
- Confidence intervals across repeated trials.

Use the convention:

`delta_brier = corrected_brier - baseline_brier`

A negative delta means the corrected method achieved a lower Brier score.

## Experimental reasoning

The research agent should independently investigate questions such as:

- Does correction help under substantial class prevalence shift?
- What happens when the shift is small?
- Does the benefit depend on sample size?
- Are improvements consistent across random seeds?
- Can correction worsen performance?
- What is the effect of classifier miscalibration?
- Which observed results require replication?

The agent must be allowed to revise hypotheses when results are contradictory.

## Evaluation data integrity

Separate exploratory experiments from any confirmatory evaluation.

Reserve independent random seeds or datasets for confirmation.

The agent must not repeatedly optimize proposals against a nominally held-out final evaluation set.

---

# 7. Data Contracts

Create Pydantic models with strict validation.

## ResearchObjective

Required fields:

- `id`
- `title`
- `question`
- `experiment_family`
- `primary_metric`
- `permitted_parameters`
- `constraints`
- `success_criteria`

## Hypothesis

Required fields:

- `id`
- `session_id`
- `statement`
- `falsifiable_prediction`
- `assumptions`
- `status`
- `created_at`

Supported statuses:

- `PROPOSED`
- `TESTING`
- `SUPPORTED`
- `CONTRADICTED`
- `INCONCLUSIVE`

## ExperimentSpec

Required fields:

- `id`
- `hypothesis_id`
- `experiment_family`
- `dataset_id`
- `protocol_version`
- `parameters`
- `seed`
- `replicate_group`
- `estimated_compute_seconds`
- `rationale`

## ExperimentResult

Required fields:

- `id`
- `experiment_id`
- `fingerprint`
- `status`
- `metrics`
- `runtime_seconds`
- `artifact_paths`
- `environment_metadata`
- `created_at`
- `error_details`, when applicable

## LazyLoopDecision

Required fields:

- `experiment_id`
- `decision`
- `reason`
- `evidence_references`
- `priority_score`
- `estimated_cost`
- `timestamp`

Supported decisions:

- `EXECUTE`
- `REUSE`
- `REPLICATE`
- `DEFER`
- `REJECT`
- `STOP`

## ResearchSession

Required fields:

- `id`
- `objective_id`
- `state`
- `model_name`
- `budget_configuration`
- `budget_consumed`
- `iteration_count`
- `started_at`
- `last_checkpoint`
- `termination_reason`

Implement JSON serialization, schema validation, and round-trip tests.

---

# 8. Experiment Fingerprinting and Replication

Create a stable experiment fingerprint using SHA-256 over a canonical representation of:

- Dataset content or generation parameters.
- Dataset split identity.
- Experiment protocol version.
- Relevant source code version.
- Model or scientific method configuration.
- Numerical parameters.
- Random seed.
- Relevant dependency/environment versions.

Canonicalize JSON keys and numeric representations before hashing.

## Duplicate behavior

If an identical, completed, verified experiment exists, return its stored result rather than running it again.

## Replication behavior

A replication is not a duplicate if the seed, independent sample, or other required experimental condition differs.

Replicates must be associated with a shared replication group.

Do not skip scientifically required replications merely because their text descriptions are similar.

Failed or incomplete experiments must not be treated as reusable successful results.

Cache hits must be logged and included in evaluation statistics.

---

# 9. LazyLoop Candidate Prioritization

Implement a simple, explicit heuristic for the initial MVP.

For candidate experiment `e`:

`priority(e) = 0.35*I + 0.30*N + 0.20*R + 0.15*F - lambda*C`

Where:

- `I`: Estimated information value.
- `N`: Novelty relative to existing evidence.
- `R`: Relevance to the research objective.
- `F`: Feasibility.
- `C`: Normalized estimated computational cost.
- `lambda`: Configurable cost penalty.

All feature scores must be normalized.

These scores are heuristic rankings, not statistically calibrated probabilities.

Keep the components individually observable.

The LLM may propose score justifications, but a deterministic controller must:

- Validate them.
- Calculate the final score.
- Apply hard constraints.
- Reject disallowed experiments.
- Record the decision.

A high priority score cannot override authorization or resource limits.

Use `lambda = 0.25` as the initial configurable default.

Do not implement reinforcement learning or learned scheduling policies in v0.1.

---

# 10. Adaptive Stopping and Loop Prevention

Implement hierarchical stopping rules.

## Hard stopping rules

Terminate when:

- Maximum wall-clock budget is exhausted.
- Maximum experiment count is reached.
- Maximum model token budget is reached or the next permitted call cannot fit.
- A critical execution or integrity failure makes continuation unsafe.
- No viable experiments remain and replanning has been exhausted.

## Soft stopping rules

Consider termination or strategy revision when:

- Candidate experiments repeatedly provide no meaningful new evidence.
- Hypotheses have sufficient evidence under predefined completion criteria.
- The agent proposes equivalent actions repeatedly.
- Estimated information value remains low.
- All remaining valid candidates are deferred because of resource constraints.

## Initial configurable defaults

- Maximum executed experiments: 12.
- Maximum planning rounds: 20.
- Maximum new candidate proposals per round: 5.
- Maximum wall-clock duration: 20 minutes.
- Maximum cumulative model tokens: 20,000.
- Maximum failed repair attempts per invalid proposal: 2.
- Maximum repeated no-progress planning rounds: 3.
- Minimum independent replications for a claim designated as confirmed by the protocol: 3.

These are engineering defaults, not scientifically validated thresholds.

All limits must be configurable.

## Reasoning-loop detection

Track normalized proposed actions across iterations.

Detect:

- Identical repeated proposals.
- Previously rejected plans reappearing without new justification.
- Repeated analysis requests with no new observations.
- Consecutive replanning rounds without valid candidates.

On the first detected loop, request a materially different plan.

After configured repeated failures, terminate with an explicit reason.

Semantic similarity may provide warnings, but must not by itself constitute proof of experimental redundancy.

## Scientific caution

Do not treat failure to improve a metric as proof that a hypothesis has been disproven.

Do not equate lack of progress with scientific certainty.

Termination reports must distinguish:

- Research objective satisfied.
- Evidence insufficient.
- Budget exhausted.
- No viable experiments.
- Repeated unproductive planning.
- Execution failure.

---

# 11. Autonomous Agent Loop

Implement the following behavior:

1. Initialize or resume research session.
2. Load the objective, constraints, and existing scientific memory.
3. Generate competing falsifiable hypotheses.
4. Propose candidate experiments.
5. Validate each proposed specification.
6. Retrieve related prior experiments.
7. Calculate LazyLoop priorities.
8. Reject, reuse, defer, replicate, or execute candidates.
9. Validate experimental results.
10. Store outcomes and provenance.
11. Request scientific interpretation from the LLM.
12. Check interpretation against recorded numerical evidence.
13. Update hypotheses and uncertainty.
14. Evaluate termination criteria.
15. Replan if research should continue.
16. Produce final reports when terminated.

Every loop must contain a deterministic budget check.

Every executed scientific action must generate a persisted event.

The agent must not be allowed to create unlimited recursive planning calls.

## Model output handling

Use structured JSON outputs and Pydantic validation.

Implement bounded retries for malformed outputs.

Never automatically execute a tool call from an unvalidated model response.

Ensure the agent receives only relevant evidence and compact summaries rather than continuously appending the entire session history.

---

# 12. Execution Safety

The agent must not execute arbitrary model-generated source code or shell commands.

The MVP should expose a registry of permitted experiment functions.

Require:

- Input schema validation.
- Registered function lookup.
- Restricted output directories.
- Execution timeout.
- Memory and CPU limits where supported.
- Explicit subprocess argument arrays; avoid shell evaluation.
- No access to unrelated filesystem locations.
- No network access for isolated experimental workloads.
- Deterministic failure reporting.

Prefer rootless container isolation for experimental workloads where available.

If container isolation is unavailable, use a restricted subprocess implementation and explicitly document the weaker security boundary. Do not describe it as a hardened sandbox.

Unsafe or unauthorized proposals must be rejected without execution.

---

# 13. Memory and Persistence

Use SQLite with transactional writes.

Minimum tables:

- `research_sessions`
- `research_objectives`
- `hypotheses`
- `experiment_specs`
- `experiment_results`
- `evidence_records`
- `agent_decisions`
- `budget_events`
- `state_transitions`

Store large artifacts on disk.

Suggested artifact structure:

- `artifacts/{session_id}/experiments/`
- `artifacts/{session_id}/plots/`
- `artifacts/{session_id}/logs/`
- `artifacts/{session_id}/reports/`

Use stable identifiers and foreign-key relationships.

A research report must be able to link every quantitative claim to the underlying experiment result.

Support resuming interrupted investigations without rerunning already completed, verified experiments.

---

# 14. CLI Requirements

Expose the following commands using a Python CLI framework such as Typer:

**Initialize:** `slothlab init`

Creates local configuration, database, and artifact directories.

**Run:** `slothlab run --config configs/calibration.yaml`

Starts an autonomous investigation.

**Resume:** `slothlab resume SESSION_ID`

Restores a persisted investigation.

**Status:** `slothlab status SESSION_ID`

Displays progress, budgets, executed experiments, and latest decisions.

**Report:** `slothlab report SESSION_ID`

Creates a Markdown research report and machine-readable metrics.

**Benchmark:** `slothlab benchmark --suite benchmarks/objectives`

Runs configured comparison conditions.

**Dashboard:** `slothlab dashboard`

Starts the Streamlit interface.

**Demo:** `slothlab demo`

Runs the bundled reproducible demonstration using a documented configuration.

Implement helpful error messages and documented CLI options.

---

# 15. Baseline Evaluation and Ablations

Implement three agent configurations:

## A. Baseline

A self-directed research agent with identical permitted scientific tools and hard safety limits, but without LazyLoop optimization.

It must still obey the same maximum resource budgets and maintain scientific validity.

## B. Cache-only

The baseline agent with exact-result reuse enabled.

Do not enable advanced candidate prioritization or adaptive stopping.

## C. Full LazyLoop

Enable:

- Exact-result reuse.
- Redundancy detection.
- Candidate prioritization.
- Scientific progress checks.
- Adaptive stopping.

All configurations must use the same underlying LLM, scientific experiment implementation, benchmark objectives, and maximum budgets.

## Benchmark scenarios

Create deterministic benchmark fixtures covering:

1. Exact duplicate detection.
2. Valid scientific replication.
3. Contradictory experimental evidence.
4. Invalid parameter proposals.
5. Repeated unproductive planning.
6. Resource-constrained experiment selection.
7. Evidence sufficiency and legitimate stopping.
8. Premature stopping risk.

## Measurement

Track:

- Total model tokens, when reported by the inference provider.
- Model calls.
- Model inference duration.
- Total investigation duration.
- Number of executed experiments.
- Number of cache hits.
- Number of repeated or redundant actions.
- Failed execution attempts.
- Number of supported scientific findings.
- Number of premature stops.
- Final research outcome.

If token counts are unavailable, report them as unavailable rather than fabricating them.

## Quality evaluation

Scientific quality must be evaluated separately from resource consumption.

Use objective-specific deterministic checks and a documented scoring rubric.

At minimum, evaluate:

- Validity of proposed experiments.
- Accuracy of reported numerical comparisons.
- Whether conclusions cite actual supporting evidence.
- Whether scientific replication requirements were satisfied.
- Whether contradictory observations were acknowledged.
- Whether termination was justified.
- Whether the investigated scenarios meaningfully address the objective.

The agent must not be the sole judge of its own research quality.

Where feasible, compare findings against a precomputed independent reference experiment grid.

## Success criteria

Target:

- Zero unauthorized experiment executions.
- Zero fabricated numerical findings.
- Accurate experiment reuse.
- Correct handling of deliberate replications.
- Reproducible benchmark runs.
- Measured reductions in redundant work.
- No material degradation in scientific-quality scores relative to the baseline.

Treat compute reduction without preserved research quality as a failed hypothesis, not a successful optimization.

Do not present a target improvement as an actual achievement before measuring it.

---

# 16. Dashboard

Build a minimal but useful Streamlit research dashboard.

## Research overview

Display:

- Current research objective.
- Session state.
- Active hypotheses.
- Experiment progress.
- Remaining computational budget.
- Latest agent decision.

## Experiment history

Display a table containing:

- Experiment ID.
- Hypothesis.
- Parameters.
- Status.
- Metrics.
- Execution duration.
- LazyLoop action.

## Decision trace

Display why each experiment was executed, reused, rejected, or deferred.

## Research findings

Display:

- Current hypothesis assessments.
- Supporting experiment IDs.
- Contradictory evidence.
- Unresolved uncertainties.

## Efficiency comparison

Display side-by-side baseline and LazyLoop results.

Include:

- Token usage.
- Execution duration.
- Experiment count.
- Redundant actions.
- Scientific-quality score.
- Termination reasons.

Use actual telemetry only.

The UI must not invent an active agent state or simulated research findings.

---

# 17. Repository Structure

Suggested structure:

slothlab/

- `pyproject.toml`
- `README.md`
- `.env.example`
- `configs/`
  - `calibration.yaml`
  - `demo.yaml`
- `slothlab/`
  - `cli.py`
  - `config.py`
  - `agent/`
    - `orchestrator.py`
    - `planner.py`
    - `analyst.py`
    - `critic.py`
  - `lazyloop/`
    - `controller.py`
    - `fingerprint.py`
    - `prioritization.py`
    - `progress.py`
    - `budgets.py`
    - `stopping.py`
  - `experiments/`
    - `registry.py`
    - `executor.py`
    - `calibration.py`
    - `validation.py`
  - `memory/`
    - `models.py`
    - `database.py`
    - `repository.py`
  - `models/`
    - `base.py`
    - `ollama_client.py`
    - `fake_client.py`
    - `schemas.py`
  - `evaluation/`
    - `benchmark.py`
    - `metrics.py`
    - `quality.py`
  - `reporting/`
    - `generator.py`
  - `ui/`
    - `dashboard.py`
- `benchmarks/`
  - `objectives/`
  - `fixtures/`
- `tests/`
  - `unit/`
  - `integration/`
  - `scientific/`
- `docs/`
  - `architecture.md`
  - `experiment_protocol.md`
  - `evaluation.md`
- `artifacts/`

Adjust organization when a simpler structure provides better maintainability.

---

# 18. Implementation Milestones

## Milestone 1 — Scientific Execution Foundation

Implement:

- Project scaffold.
- Configuration loading.
- Pydantic schemas.
- Synthetic dataset generation.
- Prior-probability correction experiment.
- Metric calculations.
- Deterministic seeds.
- Unit tests.

**Acceptance criteria:** An experiment can run from a validated configuration, produce scientifically meaningful metrics, and reproduce its results.

## Milestone 2 — Persistence and Memory

Implement:

- SQLite schema.
- Research sessions.
- Experiment persistence.
- Artifact storage.
- Experiment fingerprinting.
- Result retrieval.
- Resume checkpoints.

**Acceptance criteria:** Results survive process restarts, exact experiments can be retrieved, and incomplete runs are not confused with completed runs.

## Milestone 3 — Autonomous Research Agent

Implement:

- Ollama integration.
- Structured hypothesis generation.
- Structured experiment proposals.
- Experiment selection.
- Result interpretation.
- Hypothesis revision.
- State transitions.

**Acceptance criteria:** The agent can investigate a research objective across multiple experiments and revise its next actions based on recorded evidence.

## Milestone 4 — LazyLoop

Implement:

- Exact-result reuse.
- Replication detection.
- Candidate scoring.
- Resource accounting.
- Reasoning-loop detection.
- Adaptive stopping.
- Structured decision logs.

**Acceptance criteria:** The controller can prevent redundant work while permitting valid scientific experimentation.

## Milestone 5 — Evaluation

Implement:

- Baseline agent mode.
- Cache-only mode.
- Full LazyLoop mode.
- Benchmark scenarios.
- Computational metrics.
- Scientific-quality assessment.
- Comparison report.

**Acceptance criteria:** All three variants can run equivalent benchmark tasks and produce a grounded comparison from actual measurements.

## Milestone 6 — Presentation and Packaging

Implement:

- Streamlit dashboard.
- Demo configuration.
- Research report export.
- README.
- Setup instructions.
- Architecture documentation.
- Basic troubleshooting guide.

**Acceptance criteria:** A developer can install the project, configure an Ollama model, run the demonstration, and inspect research and efficiency results.

---

# 19. Test Requirements

Create automated tests for at least the following cases.

**Scientific execution**
- Dataset generation is reproducible.
- Evaluation data does not leak into training.
- Prior correction matches a reference implementation on controlled inputs.
- Metric calculations are numerically valid.
- Invalid parameter values are rejected.

**Persistence**
- Results survive restart.
- Experiment fingerprints are stable.
- Different random seeds produce different experiment identities.
- Failed executions cannot be reused as successful results.

**Agent operation**
- Malformed model output is rejected.
- Valid structured proposals are accepted.
- An investigation can progress through multiple state transitions.
- The agent can revise its hypothesis after contradictory results.
- A session can resume after interruption.

**LazyLoop**
- Exact duplicates are reused.
- Valid replications are allowed.
- Over-budget work is rejected.
- Repeated invalid planning terminates safely.
- Resource accounting is correct.
- An unsupported scientific claim is not presented as established.

**Evaluation**
- All variants use equivalent benchmark constraints.
- Efficiency calculations use actual recorded data.
- Baseline and LazyLoop outcomes remain independently inspectable.
- Missing model token usage is represented as missing, not zero.

Use a deterministic fake model for continuous integration tests and a separate Ollama integration test for actual local inference.

---

# 20. Definition of Done

The MVP is complete only when:

- [ ] The application installs locally.
- [ ] A real open-weight model can drive the research loop.
- [ ] The agent generates hypotheses and independently selects subsequent experiments.
- [ ] Experiments execute through validated registered functions.
- [ ] All scientific measurements are reproducible.
- [ ] Research memory persists between sessions.
- [ ] LazyLoop prevents verified redundant execution.
- [ ] Deliberate scientific replication remains possible.
- [ ] Execution and resource limits are enforced.
- [ ] The agent can terminate with explicit reasons.
- [ ] A baseline comparison can be executed.
- [ ] Scientific quality and compute costs are measured separately.
- [ ] A research report is generated from evidence.
- [ ] The CLI works without Streamlit.
- [ ] The dashboard displays persisted information.
- [ ] Automated tests pass.
- [ ] The README contains actual setup and demo commands.
- [ ] Known limitations are documented.

---

# 21. Working Practices for Agent and Subagents

If subagent delegation is supported, divide implementation into these workstreams:

**Scientific Engineering Agent**
- Implements synthetic datasets, calibration experiments, numerical validation, and scientific tests.

**Agent Orchestration Agent**
- Implements Ollama integration, structured planning, research state machine, and model response handling.

**LazyLoop Agent**
- Implements experiment reuse, prioritization, budget enforcement, repetition detection, and stopping.

**Persistence and Evaluation Agent**
- Implements SQLite, experiment provenance, research reports, benchmark runner, and quality scoring.

**Integration Agent**
- Owns the CLI, dashboard, cross-module integration, documentation, and end-to-end testing.

Shared schemas and public interfaces must be agreed upon before parallel work begins.

Do not allow subagents to independently redefine common schemas or database tables.

The lead agent is responsible for resolving integration conflicts and validating the final system.

---

# 22. Priority and Time Constraints

Build the simplest complete system that demonstrates actual autonomy and measurable computational efficiency.

Development priority:

**P0 — Essential**
- Scientific runner.
- Ollama planning.
- Validated autonomous execution.
- Persistent results.
- Exact deduplication.
- Budgets and stopping.
- Evidence-based research reports.

**P1 — Required for convincing evaluation**
- Cache-only and full LazyLoop comparisons.
- Repeated benchmark scenarios.
- Scientific-quality checks.
- Decision traces.
- Basic dashboard.

**P2 — Optional**
- Semantic similarity.
- Advanced statistical experiment selection.
- Rich visualizations.
- External tracing platforms.
- Additional scientific experiment families.

Do not spend time implementing P2 features while P0 or P1 functionality remains broken.

---

# 23. Final Deliverables

Produce:

1. A functioning local SlothLab application.
2. A functioning LazyLoop decision engine.
3. A reproducible experimental protocol.
4. An autonomous research workflow.
5. A persistent research database.
6. A runnable benchmark suite.
7. A minimal interactive dashboard.
8. A sample research report generated from actual experiments.
9. A computational-efficiency comparison.
10. Developer documentation and test results.

When implementation is complete, provide a final engineering report containing:

- Implemented features.
- Architecture and significant decisions.
- Installation instructions.
- Commands to run the demo.
- Tests executed and their results.
- Actual experimental findings, if experiments were run.
- Actual efficiency measurements, if benchmarks were run.
- Known defects.
- Unimplemented features.
- Recommended next steps.

**Do not claim functionality is complete unless it has been implemented and verified.**

---

# 24. Long-Term Research Direction

The MVP should establish the foundation for investigating cost-aware scientific autonomy.

Future research could explore:

- Bayesian experimental design.
- Expected information gain.
- Dynamic model selection.
- Cost-aware multi-agent collaboration.
- Uncertainty-aware stopping.
- Model-independent scientific memory.
- Hierarchical research planning.
- Automated experiment replication.
- Scientific hypothesis tracking over long periods.
- Learned resource scheduling.
- Research workflows grounded in local document retrieval.

However, these are future capabilities.

**The immediate objective is a functioning, reproducible, self-directed scientific research agent that can demonstrate when additional computation is useful—and when it is not.**

## Final Instruction

Begin by inspecting the repository and creating a concise implementation plan. Establish data contracts and implement the scientific experiment runner first. Then build the autonomous investigation loop, integrate LazyLoop, and complete the benchmark.

Work incrementally, run tests at each milestone, and prioritize demonstrated functionality over speculative architectural complexity.

The final application must make it possible to test the central hypothesis:

**Can an autonomous AI research agent do less computational work while achieving comparable scientific results?**
