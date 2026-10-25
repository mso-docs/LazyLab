# SlothLab research report: Prior correction under label shift

When does oracle prior-probability correction improve Brier score under label shift?

Session: `d5739d2d069f419f8377afe8a3e296d9` · model: `none: direct scientific execution` · mode: `lazyloop`

State: **COMPLETED**. Termination reason: Direct exploratory experiment; no autonomous inference.

The protocol supplies true evaluation prevalence as an oracle input. These synthetic results do not establish that deployment prevalence is known.

## Measured evidence

Negative delta means correction reduced the loss. Each row is a stored measurement; reuse does not create an independent replication.

| Result ID | Experiment ID | Status | Baseline Brier | Corrected Brier | Δ Brier | Δ log loss | Runtime (s) |
|---|---|---|---:|---:|---:|---:|---:|
| `f905390f655548b7a6f0752627e39b84` | `3abb14def89946dc80393856b8352eab` | COMPLETED | 0.05142433 | 0.0381173 | -0.01330703 | -0.046206471 | 2.3028 |

## Hypotheses and uncertainty

- **PROPOSED** (`fa4f1ef7d8774e1ea5c643f789812247`): Oracle correction improves Brier under prevalence shift
  Prediction: delta_brier < 0; one trial is exploratory

Free-form model interpretations are unverified proposals. Hypothesis status remains INCONCLUSIVE because arbitrary natural-language predictions cannot be mechanically certified. The deterministic protocol checks below assess measured directions under fixed conditions, rather than certifying the model’s claims.

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
  "cache_hits": 0,
  "model_tokens": 0,
  "model_calls": 0,
  "inference_seconds": 0.0,
  "wall_seconds": 2.3027636309998343,
  "execution_seconds": 2.3027636309998343,
  "termination_reason": "Direct exploratory experiment; no autonomous inference"
}
```

Unknown token usage is represented as null. Scientific runtime excludes model inference; end-to-end wall time is reported separately.

## Provenance and decisions

- Result `f905390f655548b7a6f0752627e39b84` fingerprint `1d5db3267daa73ebf2c0cda4b4b2bcac98e737b8469c33c234fb373d53a796dc`; artifacts: artifacts/d5739d2d069f419f8377afe8a3e296d9/experiments/0a57af93fb934c90fc9a45e2/data.npz, artifacts/d5739d2d069f419f8377afe8a3e296d9/experiments/0a57af93fb934c90fc9a45e2/spec.json.

Full parameters, environment metadata, decision features and machine-readable measurements are in `metrics.json`.
