# SlothLab research report: Live Ollama smoke investigation

When does oracle prior-probability correction improve Brier score under label shift?

Session: `c1d8e796f9b0418e9c9cb1bdb3d99b59` · model: `llama3.2:1b` · mode: `lazyloop`

State: **STOPPED**. Termination reason: Maximum planning rounds reached: evidence insufficient.

The protocol supplies true evaluation prevalence as an oracle input. These synthetic results do not establish that deployment prevalence is known.

## Measured evidence

Negative delta means correction reduced the loss. Each row is a stored measurement; reuse does not create an independent replication.

| Result ID | Experiment ID | Status | Baseline Brier | Corrected Brier | Δ Brier | Δ log loss | Runtime (s) |
|---|---|---|---:|---:|---:|---:|---:|
| `aff39a51fb434a62a7fdc1c8a8addb7e` | `317534b721db4dfbaaa291e4786c9438` | COMPLETED | 0.0058189114 | 0.0063852362 | 0.00056632474 | 0.0029495976 | 1.7311 |

## Hypotheses and uncertainty

- **INCONCLUSIVE** (`9f76a6850f064f209ba574407255f05c`): When oracle prior-probability correction improves Brier score under label shift
  Prediction: Expected Delta Direction: positive
- **PROPOSED** (`4dd4fb923cb448d895e6145f6b99e0a5`): When oracle prior-probability correction improves Brier score under label shift
  Prediction: Expected Delta Direction: negative

Free-form model interpretations are unverified proposals. Hypotheses without a predeclared expected_delta_direction remain INCONCLUSIVE. Explicit directional predictions are assessed deterministically using verified measurements and independent seeds; these statuses do not establish a general law. The protocol checks below assess measured directions under fixed conditions.

## Deterministic protocol checks

- INSUFFICIENT_EVIDENCE: 0 independent confirmatory seeds; evidence: none.

Evidence-coverage proxy: 0.167. Equal-weight independent-seed coverage and reserved-confirmatory-seed coverage, each capped at minimum_replications; a coverage proxy, not truth or statistical significance.

- Oracle evaluation prevalence is supplied; deployment prevalence estimation is not evaluated.
- Consistent replicated effects do not establish a general law or a statistical significance claim.
- Reusing a seed across exploratory and confirmatory phases invalidates its confirmatory independence.

## Resource telemetry

```json
{
  "mode": "lazyloop",
  "executed_experiments": 1,
  "successful_measurements": 1,
  "cache_hits": 2,
  "model_tokens": 8297,
  "model_calls": 5,
  "inference_seconds": 234.32525695400045,
  "wall_seconds": 236.31633010999985,
  "execution_seconds": 1.731085357000211,
  "termination_reason": "Maximum planning rounds reached: evidence insufficient"
}
```

Unknown token usage is represented as null. Scientific runtime excludes model inference; end-to-end wall time is reported separately.

## Provenance and decisions

- `317534b721db4dfbaaa291e4786c9438`: **EXECUTE** — Authorized feasible candidate Evidence: none.
- `88b21ca3527f4fce8e4559aae9c7a6a9`: **REUSE** — Verified exact experiment already completed Evidence: aff39a51fb434a62a7fdc1c8a8addb7e.
- `fafc39d8238b47b38472116e743b73db`: **REUSE** — Verified exact experiment already completed Evidence: aff39a51fb434a62a7fdc1c8a8addb7e.
- Result `aff39a51fb434a62a7fdc1c8a8addb7e` fingerprint `0a65799a3435781bb6357d96e7612cf87b4670ce43217d7722e55fa6e019eec1`; artifacts: artifacts/verification/c1d8e796f9b0418e9c9cb1bdb3d99b59/experiments/cf83cab985c97b8337f1e349/data.npz, artifacts/verification/c1d8e796f9b0418e9c9cb1bdb3d99b59/experiments/cf83cab985c97b8337f1e349/spec.json.

Full parameters, environment metadata, decision features and machine-readable measurements are in `metrics.json`.
