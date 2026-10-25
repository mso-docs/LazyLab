# SlothLab efficiency comparison

autonomous Ollama comparison

| Scenario | Trial | Mode | State | Executed | Reused | Wall seconds | Model tokens | Evidence coverage | Scientific rubric |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| paired_scoped_shift | 0 | baseline | STOPPED | 2 | 0 | 63.074 | 4162 | 0.333 | 0.625 |
| paired_scoped_shift | 0 | cache_only | STOPPED | 2 | 0 | 100.172 | 4204 | 0.333 | 0.625 |
| paired_scoped_shift | 0 | lazyloop | STOPPED | 2 | 0 | 89.526 | 4092 | 0.333 | 0.625 |
| paired_scoped_shift | 1 | cache_only | STOPPED | 2 | 0 | 198.492 | 4157 | 0.333 | 0.625 |
| paired_scoped_shift | 1 | lazyloop | STOPPED | 2 | 0 | 254.907 | 4074 | 0.333 | 0.625 |
| paired_scoped_shift | 1 | baseline | STOPPED | 2 | 0 | 84.397 | 4280 | 0.333 | 0.625 |
| paired_scoped_shift | 2 | lazyloop | STOPPED | 2 | 0 | 117.522 | 4378 | 0.333 | 0.625 |
| paired_scoped_shift | 2 | baseline | STOPPED | 2 | 0 | 120.688 | 4198 | 0.333 | 0.625 |
| paired_scoped_shift | 2 | cache_only | STOPPED | 2 | 0 | 147.426 | 4406 | 0.333 | 0.625 |

## Paired comparisons

- **cache_only**: QUALITY_NONINFERIOR_UNDER_RUBRIC; 3 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].
- **lazyloop**: QUALITY_NONINFERIOR_UNDER_RUBRIC; 3 paired observations. Quality difference (candidate minus baseline): 0.0; 95% interval: [0.0, 0.0].

## Limits

- Scientific scores use a predeclared finite benchmark rubric, not general scientific truth.
- Replay has intentionally repeated proposals and does not establish autonomous model efficiency.
- Student-t intervals assume independent trial differences; no multiplicity adjustment is applied.
- Timing includes process startup; OS caching and scheduling affect duration.
- Autonomous trajectories may differ despite identical constraints; fewer than three successful paired trials cannot establish quality preservation.
