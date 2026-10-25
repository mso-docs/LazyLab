# SlothLab efficiency comparison

fixed proposal replay (real experiments; no LLM autonomy evaluated)

| Scenario | Trial | Mode | State | Executed | Reused | Wall seconds | Model tokens | Evidence coverage | Scientific rubric |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| contradictory_evidence | 0 | baseline | STOPPED | 2 | 0 | 8.126 | 0 | 0.333 | 0.625 |
| contradictory_evidence | 0 | cache_only | STOPPED | 2 | 0 | 7.468 | 0 | 0.333 | 0.625 |
| contradictory_evidence | 0 | lazyloop | STOPPED | 2 | 0 | 7.597 | 0 | 0.333 | 0.625 |
| evidence_sufficiency | 0 | baseline | COMPLETED | 4 | 0 | 19.270 | 0 | 1.000 | 1.000 |
| evidence_sufficiency | 0 | cache_only | COMPLETED | 4 | 0 | 17.744 | 0 | 1.000 | 1.000 |
| evidence_sufficiency | 0 | lazyloop | COMPLETED | 4 | 0 | 13.258 | 0 | 1.000 | 1.000 |
| exact_duplicate | 0 | baseline | STOPPED | 2 | 0 | 8.356 | 0 | 0.167 | 0.625 |
| exact_duplicate | 0 | cache_only | STOPPED | 1 | 1 | 4.325 | 0 | 0.167 | 0.625 |
| exact_duplicate | 0 | lazyloop | STOPPED | 1 | 1 | 4.481 | 0 | 0.167 | 0.625 |
| invalid_parameters | 0 | baseline | STOPPED | 1 | 0 | 4.487 | 0 | 0.167 | 0.625 |
| invalid_parameters | 0 | cache_only | STOPPED | 1 | 0 | 4.258 | 0 | 0.167 | 0.625 |
| invalid_parameters | 0 | lazyloop | STOPPED | 1 | 0 | 4.731 | 0 | 0.167 | 0.625 |
| premature_stop_risk | 0 | baseline | COMPLETED | 8 | 0 | 35.025 | 0 | 1.000 | 1.000 |
| premature_stop_risk | 0 | cache_only | COMPLETED | 5 | 3 | 20.363 | 0 | 1.000 | 1.000 |
| premature_stop_risk | 0 | lazyloop | COMPLETED | 5 | 3 | 20.831 | 0 | 1.000 | 1.000 |
| repeated_planning | 0 | baseline | STOPPED | 6 | 0 | 18.787 | 0 | 0.167 | 0.625 |
| repeated_planning | 0 | cache_only | STOPPED | 1 | 5 | 4.320 | 0 | 0.167 | 0.625 |
| repeated_planning | 0 | lazyloop | STOPPED | 1 | 3 | 9.344 | 0 | 0.167 | 0.625 |
| resource_constraints | 0 | baseline | STOPPED | 1 | 0 | 8.304 | 0 | 0.167 | 0.625 |
| resource_constraints | 0 | cache_only | STOPPED | 1 | 0 | 6.497 | 0 | 0.167 | 0.625 |
| resource_constraints | 0 | lazyloop | STOPPED | 1 | 0 | 6.255 | 0 | 0.167 | 0.625 |
| valid_replication | 0 | baseline | STOPPED | 3 | 0 | 15.977 | 0 | 0.500 | 0.625 |
| valid_replication | 0 | cache_only | STOPPED | 3 | 0 | 12.916 | 0 | 0.500 | 0.625 |
| valid_replication | 0 | lazyloop | STOPPED | 3 | 0 | 11.903 | 0 | 0.500 | 0.625 |

## Paired comparisons

- **cache_only**: CONTROLLER_REPLAY_ONLY; 8 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].
- **lazyloop**: CONTROLLER_REPLAY_ONLY; 8 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].

## Limits

- Scientific scores use a predeclared finite benchmark rubric, not general scientific truth.
- Replay has intentionally repeated proposals and does not establish autonomous model efficiency.
- Student-t intervals assume independent trial differences; no multiplicity adjustment is applied.
- Timing includes process startup; OS caching and scheduling affect duration.
- Autonomous trajectories may differ despite identical constraints; fewer than three successful paired trials cannot establish quality preservation.
