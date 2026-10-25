# SlothLab efficiency comparison

fixed proposal replay (real experiments; no LLM autonomy evaluated)

| Scenario | Trial | Mode | Executed | Cache hits | Wall seconds | Model tokens | Quality coverage |
|---|---:|---|---:|---:|---:|---:|---:|
| no_shift | 0 | baseline | 9 | 0 | 19.124 | 0 | 1.000 |
| no_shift | 0 | cache_only | 6 | 3 | 9.947 | 0 | 1.000 |
| no_shift | 0 | lazyloop | 6 | 3 | 13.051 | 0 | 1.000 |
| prevalence_shift | 0 | baseline | 9 | 0 | 21.047 | 0 | 1.000 |
| prevalence_shift | 0 | cache_only | 6 | 3 | 13.955 | 0 | 1.000 |
| prevalence_shift | 0 | lazyloop | 6 | 3 | 10.706 | 0 | 1.000 |

Quality score measures evidence coverage, not scientific truth.
Replay has intentionally repeated proposals and does not establish autonomous model efficiency.
Timing includes process startup; OS caching and scheduling affect duration.
Autonomous trajectories may differ between modes despite identical constraints; repeat trials before drawing conclusions.
