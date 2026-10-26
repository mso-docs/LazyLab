# SlothLab + LazyLoop

**Local scientific research, with a reason to stop.**

SlothLab turns a research question into falsifiable hypotheses, validated experiments, measured evidence, and a reproducible report. LazyLoop controls the work: it prioritizes useful candidates, reuses verified results, permits independent replications, and stops when a declared target or resource boundary is reached.

The initial laboratory studies **oracle prior-probability correction under class prevalence shift**. Scientific execution and research memory stay on the app host, using Python, SQLite or JSON documents, and registered scikit-learn procedures. Inference can use a local or remote Ollama-compatible server. The Streamlit workspace supports the complete start → observe → pause/resume → export workflow; the CLI remains fully usable without Streamlit.

> This is a single-user Linux application intended for loopback use. It is not a public multi-tenant service. Scientific conclusions remain scoped to recorded evidence and the finite experimental protocol.

[Watch the walkthrough on YouTube](https://youtu.be/UV3h4IRk3go) · [Demo files and transcript](docs/demo.md)

[![Watch the SlothLab walkthrough on YouTube](https://img.youtube.com/vi/UV3h4IRk3go/hqdefault.jpg)](https://youtu.be/UV3h4IRk3go)

[GitHub Pages demo](https://mso-docs.github.io/LazyLab/) · [Video help guide](https://mso-docs.github.io/LazyLab/help.html) · [Pages setup](docs/github-pages.md)

[Read the project write-up on DEV: SlothLab — Hacktoberfest Week 3 Challenge](https://dev.to/mackenzie-techdocs/slothlab-hacktoberfest-week-3-challenge-11ao)

## Quick start

Use Python 3.12 or newer. Install Ollama separately, start its server, and select a model already listed by `ollama list`. SlothLab never downloads model weights automatically.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dashboard,dev]'
export OLLAMA_MODEL='your-installed-model'
slothlab init
slothlab doctor
slothlab dashboard
```

Open **http://127.0.0.1:8501**. In **New investigation**, choose the question, permitted experimental conditions, finite completion protocol, and compute budgets. **Discover installed models** checks the configured Ollama endpoint when clicked. Start an investigation, then follow its measurements, decisions, logs, and provisional findings in **Research**.

Jobs run in a separate local process, so closing or refreshing the browser does not abandon research. **Stop run** pauses a worker; **Resume investigation** continues a nonterminal checkpoint. The workspace automatically refreshes while jobs are active. **Comparisons** launches real-model or explicitly labeled replay benchmarks and displays their actual outputs.

With uv, install the locked development environment using `uv sync --locked --extra dashboard --extra dev`; prefix commands with `uv run` or activate `.venv`. To install the backend alone, use `python -m pip install -e .`. Bundled demo/config/benchmark assets are included in the package and are resolved when commands run outside the checkout.

## Appearance, local history and learning

The sidebar now offers **System / Light / Dark** appearance and three history modes:

- **Workspace:** continue using an existing local SQLite research workspace.
- **Browser profile:** create a named local profile. An opaque browser preference remembers its separate history on this same browser and origin. No account registration is needed.
- **Guest:** use temporary JSON research documents and artifacts, with no SQL database. Download a research bundle to preserve and reopen your history.

In **Provenance & export**, prepare a portable ZIP bundle. Guest bundles default to all guest sessions so shared evidence keeps its original provenance. In guest mode, use **Open research bundle** to restore a downloaded file. Opening an archive never starts inference; imported connections and execution settings require review before resume. Temporary guest files can remain on the app host until temporary-directory cleanup; guest mode is not an automatic secure-erasure promise.

**Learn & help** includes an offline 84-second captioned animated walkthrough, six seekable chapters, transcripts, practice questions and a research-design checklist. It is a silent instructional animation, not a recording of a live investigation. Appearance and the local profile locator are remembered in browser storage; clearing browser storage removes that locator, not the underlying files.

See [history and profiles](docs/identity.md), [learning guide](docs/learning.md), and [local/remote AI capabilities](docs/connections.md). Optional operator-configured OIDC hooks exist for deployments that need account identity, but local browser profiles and guests work without a provider.

## What you can investigate

The registered experiment creates disjoint training and evaluation samples from shared synthetic class-conditional feature distributions, fits logistic regression on training data only, and compares raw probabilities with a Bayesian prior correction. Conditions include prevalence, sample size, class separation, feature noise, regularization, and probability temperature.

- **Measured outcomes:** Brier score, log loss, their corrected-minus-baseline deltas, runtime, seed, sample size, and resource telemetry.
- **Scientific caution:** a negative delta favors correction; a positive delta means it worsened that trial. Correction is not assumed to help universally.
- **Oracle assumption:** true evaluation prevalence is supplied by this synthetic protocol. Unknown deployment prevalence estimation is outside this MVP.
- **Replication:** the same scientific configuration and seed can reuse a verified result. A different independent seed is a distinct experiment, never a duplicate merely because its description is similar.

Try one real scientific experiment without inference:

```bash
slothlab experiment --seed 7 --train-prevalence 0.5 --evaluation-prevalence 0.2
```

This produces measured artifacts and a report, but does not claim autonomous reasoning.

## CLI workflow

The bundled demo declares three exploratory measurements followed by one independent confirmation group. It can complete only when the replicated effect meets its finite criterion; mixed evidence or exhausted budgets remain explicit outcomes.

```bash
slothlab run --config configs/calibration.yaml
slothlab run --config configs/calibration.yaml --background
slothlab jobs
slothlab status SESSION_ID
slothlab stop JOB_ID
slothlab resume SESSION_ID --background
slothlab report SESSION_ID
slothlab demo
```

`slothlab --db PATH status SESSION_ID` and the same global `--db` option select a nondefault memory for resume/report. Terminal sessions retain their termination reason; they are not silently restarted. Session locks prevent two processes from operating the same investigation. Elapsed wall time includes pauses, and interrupted work retains its conservative resource charge.

See the [browser guide](docs/ui.md) and [operations guide](docs/operations.md) for lifecycle, recovery, isolation, backup, and troubleshooting details.

## Declare a finite scientific target

A broad question does not automatically become a machine-checkable success condition. The browser exposes a finite completion protocol; YAML offers the same contract. For example:

```yaml
objective:
  title: Replicated oracle correction under one controlled shift
  question: Is the Brier-score effect reproducible for this authorized condition?
  permitted_parameters:
    train_prevalence: [0.5]
    evaluation_prevalence: [0.2]
    sample_size: [1000]
    feature_count: [6]
    class_separation: [1.0]
    noise: [0.0]
    logistic_c: [1.0]
    probability_temperature: [1.0]
  constraints:
    parameter_bounds:
      sample_size: {min: 500, max: 2000}
    max_estimated_compute_seconds: 30
    allowed_phases: [exploratory, confirmatory]
    require_replication_group: true
  success_criteria:
    minimum_exploratory_experiments: 3
    minimum_conditions: 1
    require_confirmation: true
    minimum_confirmatory_groups: 1
    minimum_replications: 3
    effect_direction: either
    effect_tolerance: 0.0000000001
budget:
  max_experiments: 6
  max_rounds: 8
  max_candidates: 3
  wall_seconds: 1200
  max_tokens: 30000
  call_token_reserve: 2000
```

`effect_direction: either` accepts a consistently negative, positive, or negligible effect, rather than presupposing improvement. Mixed effects remain inconclusive. Once the predeclared exploratory target is reached, the agent requests one final held-out confirmation batch. It cannot keep optimizing proposals against those confirmation outcomes. `COMPLETED` means the operational criteria were met for tested conditions; it does not certify a universal scientific statement. Unknown constraint/criterion keys fail validation.

## Evaluate compute and scientific quality separately

Seven bundled domain scenarios cover prevalence shift, no-shift identity, sample size, independent replication, repeated proposals, mixed outcomes, and miscalibration. A separate eight-case behavioral suite covers every acceptance fixture in the writeup, including invalid proposals, constrained selection, evidence sufficiency, and premature stopping risk.

```bash
# Real autonomous comparisons: 7 scenarios × 3 modes × 3 paired trials.
slothlab benchmark --suite benchmarks/objectives --repeats 3

# Real scientific execution with fixed proposals and NO model inference.
slothlab benchmark --suite benchmarks/objectives --replay --output artifacts/benchmarks/replay

# Eight required behavioral cases: rejection, budgets, sufficiency and loop risks.
slothlab benchmark --suite benchmarks/behavioral --replay --output artifacts/benchmarks/behavioral

# Independent final-check grid, withheld from agent planning.
slothlab reference --config configs/calibration.yaml --output artifacts/reference/grid \
  --max-conditions 4 --seeds-per-condition 3
slothlab benchmark --suite benchmarks/objectives --repeats 3 \
  --reference artifacts/reference/grid/reference.json
```

Each benchmark arm has cold storage and identical scenario/model/budget/seed constraints. Trials receive disjoint seed partitions, paired within modes; arm order rotates across trials. Outputs retain failed arms, partial progress, resource costs, scientific diagnostics, and paired intervals. Use fresh output directories to avoid contaminating a cold-cache comparison. Real-model evaluation can take substantial time on CPU.

The scientific rubric audits measurement integrity, independent confirmation, applicable no-shift controls, and justified claim/evidence references. Evidence coverage remains a separate metric. Paired quality-preservation and compute-benefit verdicts require repeated autonomous evidence; fixed replay never establishes the central autonomy hypothesis. Independent reference estimates are finite-sample checks, not population truth.

The [verification report](docs/verification.md) records current test results, actual model-driven investigations and measured comparisons. [Example artifacts](docs/examples/README.md) preserve selected observations; targets are never reported as achieved improvements without measurement.

## Safety and reproducibility

Scientific actions use an allowlist of validated registered functions, never generated Python or shell commands. SHA-256 identities include scientific parameters, seed/phase, protocol, source, and dependency/environment versions. Completed results must pass numerical consistency and artifact-hash checks before reuse. Original result identities survive cross-session reuse, and committed worker receipts support crash reconciliation.

`execution_isolation: auto` uses rootless Bubblewrap when the host supports it and records a restricted-subprocess fallback otherwise. **Only Bubblewrap provides the implemented OS filesystem/network boundary.** Explicit `bubblewrap` mode fails closed when unavailable; `subprocess` is a weaker boundary for trusted registered code. Run `slothlab doctor` on the deployment host and inspect each result’s recorded boundary. See [operations](docs/operations.md#execution-boundary).

Configuration comes from YAML and exported variables in [.env.example](.env.example); `.env` is not loaded automatically. Inference endpoint, model, timeout, context, CPU threads and supported thinking mode are configurable. Missing token/resource telemetry stays unknown, while unreported/failed inference retains its conservative reservation.

## Development and scope

```bash
pytest -q
SLOTHLAB_TEST_OLLAMA=1 OLLAMA_MODEL='your-installed-model' pytest tests/test_models.py -q
```

Offline tests use clearly labeled scripted model responses and real numerical integration tests. Live-model tests are explicit opt-ins. Streamlit AppTest covers browser start/resume/stop, validation, measured plots, exports and comparison rendering; interactive browser/pixel review was unavailable in the implementation environment and is not claimed.

The [requirements audit](docs/requirements.md) maps the original writeup to implementation and evidence. More detail: [architecture](docs/architecture.md), [scientific protocol](docs/experiment_protocol.md), [evaluation](docs/evaluation.md), [operations](docs/operations.md), and the [original specification](docs/specification.md).

The original v0.1 boundary excluded unrestricted code execution, internet/literature research, fine-tuning, self-modification, distributed execution, multi-user authentication, cloud dependencies and autonomous publication. Optional semantic embeddings, learned scheduling, external tracing and additional scientific families are future work, not hidden MVP dependencies.

Version 0.2.0 adds appearance preferences, local browser profiles, portable JSON guest sessions, and guided learning. See [QoL verification and remaining deployment limits](docs/qol-verification.md).

For a pre-publication history audit, see [Gitleaks setup and history scanning](docs/security.md), or run `bash scripts/scan_history.sh`.
