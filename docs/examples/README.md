# Measured examples

These are snapshots from actual local execution on October 25, 2026. They are not fixtures or fabricated outputs. Referenced database/NPZ artifacts remain in the local ignored `artifacts/` directory; published provenance paths are relative to the repository root, with the original machine-specific checkout prefix removed for privacy. Measurements and artifact hashes are unchanged; these references are not portable artifact downloads.

- `scientific/report.md` and `scientific/metrics.json`: direct exploratory experiment, seed 7, generated with `slothlab experiment --seed 7`.
- `replay/comparison.md` and `replay/comparison.json`: two fixed schedules across baseline, cache-only and LazyLoop, generated with `slothlab benchmark --replay --output artifacts/benchmarks/verified-replay`. Science was real; no inference was used. Zero tokens are accurate for this protocol.

Earlier replay snapshots report the original evidence-coverage proxy. The newer evaluation-v2 snapshot additionally reports a finite scientific rubric; neither is proof of general scientific truth. Runtime includes process startup and concurrent machine activity. These are single trials, not statistically characterized performance estimates.

- `ollama/report.md`, `ollama/metrics.json`, and `ollama/config.yaml`: completed live model-driven investigation (one real execution, two exact reuses, finite planning stop). The config uses the model installed on the verification machine; select your own installed model.

- `complete-investigation/`: a real model-driven investigation that reached **COMPLETED** through measured exploration and a final independent three-seed confirmation batch; reports retain five actual executions and one exact reuse.
- `evaluation-v2/`: the corrected seven-scenario, three-mode replay comparison and independent reference grid. The earlier adverse stopping result is retained in local runtime history and discussed in the evaluation guide.

- `behavioral-v2/`: all eight mandatory acceptance behaviors across three modes, with real execution and explicit invalid-proposal rejection.
- `autonomous-repeated/`: three independent paired trials of a strictly budgeted real-model investigation across all three modes; insufficient confirmatory coverage prevents an autonomous-efficiency claim.
