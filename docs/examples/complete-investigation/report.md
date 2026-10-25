# SlothLab research report: Independent confirmation of a scoped prevalence-shift condition

Characterize whether oracle correction consistently improves or worsens Brier score for this one authorized synthetic condition. Explore first, then perform a final batch with three distinct reserved confirmation seeds. Preserve uncertainty about generalization.

Session: `5bee1711d22248aabfb5ec9b2b32f375` · model: `qwen3:0.6b` · mode: `lazyloop`

State: **COMPLETED**. Termination reason: Predeclared operational research criteria satisfied; conclusions are scoped to the tested conditions.

The protocol supplies true evaluation prevalence as an oracle input. These synthetic results do not establish that deployment prevalence is known.

## Measured evidence

Negative delta means correction reduced the loss. Each row is a stored measurement; reuse does not create an independent replication.

| Result ID | Experiment ID | Status | Baseline Brier | Corrected Brier | Δ Brier | Δ log loss | Runtime (s) |
|---|---|---|---:|---:|---:|---:|---:|
| `36aebdde38394f99bea8e1bedf469ccd` | `257ce44458d04bebb9e7aea552bfdc36` | COMPLETED | 0.056792255 | 0.043257585 | -0.01353467 | -0.040524829 | 3.5236 |
| `4ec1310ba8fb4ea896ed9000f2a3dd6c` | `e1fe8770176c474083795a2672fc3df8` | COMPLETED | 0.054907667 | 0.040963411 | -0.013944255 | -0.05219167 | 3.5031 |
| `744c075075104ca28d1e4a7808397257` | `3dd21c2d6d524fa08e1c12d951f57a8e` | COMPLETED | 0.028320796 | 0.027465208 | -0.00085558798 | -0.0066378488 | 4.3026 |
| `d8b4148fa4754c0895627673fd362565` | `9fac6670812a44fe8b9147bce4db0d1d` | COMPLETED | 0.062348323 | 0.049634462 | -0.012713861 | -0.041169585 | 3.6944 |
| `7182df0645044e3e83c4ba04e9a74fff` | `5ad9be1224004f91b46df8778e61b942` | COMPLETED | 0.029748057 | 0.024757271 | -0.0049907863 | -0.020764054 | 3.8298 |

## Hypotheses and uncertainty

- **INCONCLUSIVE** (`bde7447e5f014360a159c1ec89bd02d6`): Hypothesis 1: Oracle correction may improve Brier score when applied to the synthetic condition.
  Prediction: negative
  Deterministic assessment: Insufficient verified independent replications: need 3 distinct seeds within one identical parameter and phase condition. Evidence: none.
  Deterministic assessment: Insufficient verified independent replications: need 3 distinct seeds within one identical parameter and phase condition. Evidence: none.
- **INCONCLUSIVE** (`865f187e4e1f4dd697195d1df7be4068`): Hypothesis 2: Oracle correction may fail to improve Brier score when applied to the synthetic condition.
  Prediction: positive
  Deterministic assessment: Insufficient verified independent replications: need 3 distinct seeds within one identical parameter and phase condition. Evidence: none.
  Deterministic assessment: Insufficient verified independent replications: need 3 distinct seeds within one identical parameter and phase condition. Evidence: none.

Free-form model interpretations are unverified proposals. Hypotheses without a predeclared expected_delta_direction remain INCONCLUSIVE. Explicit directional predictions are assessed deterministically using verified measurements and independent seeds; these statuses do not establish a general law. The protocol checks below assess measured directions under fixed conditions.

## Deterministic protocol checks

- CONSISTENT_IMPROVEMENT: 3 independent confirmatory seeds; mean delta Brier -0.006186744939433456; 95% Student-t interval [-0.02113857040001533, 0.008765080521148418]; evidence: `744c075075104ca28d1e4a7808397257`, `d8b4148fa4754c0895627673fd362565`, `7182df0645044e3e83c4ba04e9a74fff`.

Evidence-coverage proxy: 1.000. Equal-weight independent-seed and reserved-confirmatory-seed coverage, capped at minimum_replications. Coverage is not scientific truth.

- Oracle evaluation prevalence is supplied; deployment prevalence estimation is not evaluated.
- Scores are a transparent finite benchmark rubric, not a general measure of scientific truth.
- Student-t intervals assume independent seeds sampled from the generator distribution; no multiplicity correction is applied.
- Consistent replicated effects alone do not establish a general law or statistical significance.
- Reusing an exploratory seed invalidates its confirmatory independence.

Scientific rubric score: 1.000. Predeclared weighted diagnostic: measurement integrity .30, independent confirmation .30, applicable no-shift identity controls .20, claim/evidence calibration .20; inapplicable components are excluded and remaining weights renormalized. No valid measurements scores zero.

### Expected controls and claim audit

Unjustified established claims: 0. Invalid measurements: 0.

## Resource telemetry

```json
{
  "mode": "lazyloop",
  "executed_experiments": 5,
  "successful_measurements": 5,
  "supported_findings": 1,
  "premature_stops": null,
  "failed_execution_attempts": 0,
  "cache_hits": 1,
  "redundant_proposals": 1,
  "failed_measurements": 0,
  "rejected_proposals": 0,
  "model_tokens": 10712,
  "model_calls": 5,
  "inference_seconds": 410.86193846899914,
  "wall_seconds": 430.49328365400015,
  "execution_seconds": 18.853534976000446,
  "scientific_cpu_seconds": 15.273776,
  "peak_memory_bytes": 219492352,
  "termination_reason": "Predeclared operational research criteria satisfied; conclusions are scoped to the tested conditions",
  "count_definitions": {
    "supported_findings": "Distinct confirmed fixed-condition groups with consistently directional or effectively zero deltas under the minimum independent replication protocol; not general scientific truth.",
    "premature_stops": "Detected known-protocol soft-stop violations in persisted termination audits; null without an audit, not a claim of universal optimal stopping.",
    "failed_execution_attempts": "Persisted FAILED local execution receipts; null if a charged execution has no result receipt."
  }
}
```

Unknown token usage is represented as null. Scientific runtime excludes model inference; end-to-end wall time is reported separately.

## Provenance and decisions

- `257ce44458d04bebb9e7aea552bfdc36`: **EXECUTE** — Authorized feasible candidate Evidence: none.
- `e1fe8770176c474083795a2672fc3df8`: **REPLICATE** — Independent seed under identical conditions Evidence: 36aebdde38394f99bea8e1bedf469ccd.
- `6299981e4f7d467fb11aed68d8f60156`: **REUSE** — Verified exact experiment already completed Evidence: 36aebdde38394f99bea8e1bedf469ccd.
- `3dd21c2d6d524fa08e1c12d951f57a8e`: **EXECUTE** — Authorized feasible candidate Evidence: none.
- `9fac6670812a44fe8b9147bce4db0d1d`: **REPLICATE** — Independent seed under identical conditions Evidence: 744c075075104ca28d1e4a7808397257.
- `5ad9be1224004f91b46df8778e61b942`: **REPLICATE** — Independent seed under identical conditions Evidence: 744c075075104ca28d1e4a7808397257, d8b4148fa4754c0895627673fd362565.
- Result `36aebdde38394f99bea8e1bedf469ccd` fingerprint `842fb7b4a5e5c7594bc4fda18945b56ffabc529dd990cfb55b66c012a5d29ab5`; artifacts: artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/77f8118c5ee57168237085f6/data.npz, artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/77f8118c5ee57168237085f6/spec.json.
- Result `4ec1310ba8fb4ea896ed9000f2a3dd6c` fingerprint `938c2dc7a24647dd3f8fcd140b82a9a0a36dbac8f26d38f260fe120391e8f245`; artifacts: artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/9d5346be195c367bea8732b7/data.npz, artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/9d5346be195c367bea8732b7/spec.json.
- Result `744c075075104ca28d1e4a7808397257` fingerprint `589750d9ac8bcf01e81f3c939cfafe7b4544babc55fc99b9bc3f7c6b1065726b`; artifacts: artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/f68c3b7905f5d58caeb4b1d8/data.npz, artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/f68c3b7905f5d58caeb4b1d8/spec.json.
- Result `d8b4148fa4754c0895627673fd362565` fingerprint `799e46b0e31368ab48b84208926f1f429e86bda3b5bb29ff4cca94a1fbb6556d`; artifacts: artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/33dbd47ebccd85852a43fa6a/data.npz, artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/33dbd47ebccd85852a43fa6a/spec.json.
- Result `7182df0645044e3e83c4ba04e9a74fff` fingerprint `5662beff8a46464b13024b7ee9ea049f3825437c7a6b9f0fa61c6f32f79a5335`; artifacts: artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/6603b7f598a5778dc5e923d2/data.npz, artifacts/verification/iteration/completion-correlated/5bee1711d22248aabfb5ec9b2b32f375/experiments/6603b7f598a5778dc5e923d2/spec.json.

Full parameters, environment metadata, decision features and machine-readable measurements are in `metrics.json`.
