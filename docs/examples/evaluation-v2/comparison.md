# SlothLab efficiency comparison

fixed proposal replay (real experiments; no LLM autonomy evaluated)

| Scenario | Trial | Mode | State | Executed | Reused | Wall seconds | Model tokens | Evidence coverage | Scientific rubric |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| miscalibration | 0 | baseline | STOPPED | 12 | 0 | 14.804 | 0 | 1.000 | 1.000 |
| miscalibration | 0 | cache_only | STOPPED | 12 | 0 | 21.921 | 0 | 1.000 | 1.000 |
| miscalibration | 0 | lazyloop | STOPPED | 12 | 0 | 17.902 | 0 | 1.000 | 1.000 |
| mixed_outcomes | 0 | baseline | STOPPED | 9 | 0 | 12.446 | 0 | 1.000 | 1.000 |
| mixed_outcomes | 0 | cache_only | STOPPED | 6 | 3 | 8.933 | 0 | 1.000 | 1.000 |
| mixed_outcomes | 0 | lazyloop | STOPPED | 6 | 3 | 8.092 | 0 | 1.000 | 1.000 |
| no_shift | 0 | baseline | STOPPED | 9 | 0 | 12.214 | 0 | 1.000 | 1.000 |
| no_shift | 0 | cache_only | STOPPED | 6 | 3 | 7.448 | 0 | 1.000 | 1.000 |
| no_shift | 0 | lazyloop | STOPPED | 6 | 3 | 7.211 | 0 | 1.000 | 1.000 |
| prevalence_shift | 0 | baseline | STOPPED | 9 | 0 | 10.360 | 0 | 1.000 | 1.000 |
| prevalence_shift | 0 | cache_only | STOPPED | 6 | 3 | 6.706 | 0 | 1.000 | 1.000 |
| prevalence_shift | 0 | lazyloop | STOPPED | 6 | 3 | 6.567 | 0 | 1.000 | 1.000 |
| repeated_proposals | 0 | baseline | STOPPED | 9 | 0 | 9.878 | 0 | 0.167 | 0.625 |
| repeated_proposals | 0 | cache_only | STOPPED | 1 | 8 | 1.213 | 0 | 0.167 | 0.625 |
| repeated_proposals | 0 | lazyloop | STOPPED | 1 | 3 | 1.163 | 0 | 0.167 | 0.625 |
| sample_size | 0 | baseline | STOPPED | 12 | 0 | 13.199 | 0 | 1.000 | 1.000 |
| sample_size | 0 | cache_only | STOPPED | 12 | 0 | 13.221 | 0 | 1.000 | 1.000 |
| sample_size | 0 | lazyloop | STOPPED | 12 | 0 | 13.825 | 0 | 1.000 | 1.000 |
| valid_replication | 0 | baseline | STOPPED | 6 | 0 | 6.816 | 0 | 1.000 | 1.000 |
| valid_replication | 0 | cache_only | STOPPED | 6 | 0 | 6.799 | 0 | 1.000 | 1.000 |
| valid_replication | 0 | lazyloop | STOPPED | 6 | 0 | 6.729 | 0 | 1.000 | 1.000 |

## Paired comparisons

- **cache_only**: CONTROLLER_REPLAY_ONLY; 7 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].
- **lazyloop**: CONTROLLER_REPLAY_ONLY; 7 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].

## Limits

- Scientific scores use a predeclared finite benchmark rubric, not general scientific truth.
- Replay has intentionally repeated proposals and does not establish autonomous model efficiency.
- Student-t intervals assume independent trial differences; no multiplicity adjustment is applied.
- Timing includes process startup; OS caching and scheduling affect duration.
- Autonomous trajectories may differ despite identical constraints; fewer than three successful paired trials cannot establish quality preservation.
