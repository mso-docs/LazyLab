# Evaluation protocol

SlothLab evaluates computational cost and scientific evidence separately. A smaller token bill is not a successful research result if conclusions become less justified.

## Three comparison arms

Every scenario/trial runs baseline, cache-only and LazyLoop against the same objective, allowed parameters, exploratory/confirmation partitions, model and hard budgets. Scientific seed partitions are deterministically rotated between trials, so independent repeats do not reuse the same scientific draws; all arms within a trial receive the same partition. Trial zero retains configured seeds. Arm execution order rotates across repeats (baseline first, cache-only first, LazyLoop first) to reduce systematic warmup-order bias; the actual arm order is recorded. Each arm has cold SQLite memory and separate artifacts. A configuration signature permits equality checks across arms. Reusing output storage is rejected before any experiment starts.

- **Baseline:** registered scientific tools and all hard validation/resource constraints; no exact reuse, candidate ranking or adaptive no-progress stopping.
- **Cache-only:** baseline plus verified exact-result reuse.
- **LazyLoop:** cache-only plus cost-aware ranking and bounded no-progress stopping.

`slothlab benchmark --suite benchmarks/objectives --repeats 3` performs actual model-led investigations. A failed arm remains inspectable in its database/report and does not erase other arms. `comparison.json` is atomically updated after every arm, with `complete: false` until the suite finishes.

`--replay` executes a predeclared proposal schedule with **real numerical experiments and no inference**. Replay is a controller evaluation, never a replacement for an autonomous model. It correctly records zero model calls/tokens. Scenario-specific schedules live in adjacent `.replay.json` files; scenarios without one use three exploratory seeds proposed twice, followed by three reserved confirmation seeds. Python-generated numerical fixtures are used only in automated tests.

## Bundled scenarios

| Scenario | Scientific/controller question | Fixed replay behavior |
|---|---|---|
| `prevalence_shift` | Does oracle correction help under substantial label shift? | Deliberate duplicates and independent confirmation |
| `no_shift` | Does correction preserve probabilities when priors match? | Identity control and independent confirmation |
| `valid_replication` | Can distinct seeds proceed under a shared condition? | Six independent exploratory/confirmatory trials |
| `repeated_proposals` | Can exact reuse and no-progress stopping avoid loops? | One condition repeatedly proposed; full mode stops after configured unproductive cycles when no independent scheduled work remains |
| `mixed_outcomes` | Can contradictory observations be preserved? | Predeclared seeds including known finite-sample counterexample conditions, without assuming the resulting signs |
| `miscalibration` | How does temperature distortion affect correction? | Two predeclared temperature conditions, independently replicated |
| `sample_size` | How do finite sample sizes change effects and uncertainty? | Small/large predeclared sample conditions, independently replicated |

Replay schedules are fixed before observing outcomes. A soft no-progress stop is deferred when an already authorized independent experiment remains later in the known schedule; the strategy revision and reason are recorded. A sequence containing only duplicates still terminates early. Multiple condition confirmations in a replay grid are not adaptive optimization against a held-out set. The autonomous agent still follows its own final-batch confirmation protocol.

## Scientific rubric

`quality_score` retains the original evidence-coverage proxy for compatibility: average capped independent-seed and reserved-confirmation coverage. It is **not scientific truth**.

`scientific_quality_score` uses an explicit finite benchmark rubric:

| Component | Weight | Measurement |
|---|---:|---|
| Measurement integrity | 0.30 | Fraction of stored results with complete consistent finite metrics and verified artifacts |
| Independent confirmation | 0.30 | Reserved independent confirmation coverage, capped at minimum replication count |
| Controlled expected behavior | 0.20 | No-shift identity: both metric deltas must be within `1e-10` of zero |
| Claim/evidence calibration | 0.20 | Established directional statuses must have matching deterministic assessment receipts and valid result references; retaining uncertainty is valid |

Inapplicable controls/claim components are excluded and weights renormalized; zero valid measurements always scores zero. Raw component scores, invalid result IDs, control result IDs, claim checks and invalid model evidence references accompany every score. Unverified model text is never treated as a scientific conclusion.

Confirmation summaries contain unique seeds, result IDs, mean delta Brier, sample standard deviation and a 95% Student-t interval. Intervals use the [SciPy Student-t distribution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html), `mean ± t(0.975, n−1) × s/√n`. They require at least two independent seeds, assume sampling from the generator distribution, and have no multiplicity adjustment. Consistently signed deltas describe a protocol observation; they do not automatically imply significance or a general law.

## Independent reference grid

`slothlab reference --config configs/calibration.yaml --output artifacts/reference --max-conditions 4 --seeds-per-condition 3` runs the registered scientific experiment on a deterministic spread of allowed parameter combinations. It requires fresh storage and obeys configured experiment and wall budgets. Selected seeds are outside **both** agent partitions and are explicitly marked reference-only.

The grid writes `reference.json`, a separate SQLite database, full artifacts and a report. Loading a reference re-verifies its persisted metrics, condition/seed identities and artifact integrity; modified summary means are rejected. Do not give reference observations to the planner or choose new experiments after inspecting them. `slothlab benchmark ... --reference artifacts/reference/reference.json` loads the grid exclusively for final scoring, matching confirmed parameter conditions and reporting mean differences and direction agreement. A reference interval crossing zero is unresolved and is not used as a true direction label. Independent finite-sample reference means remain estimates, not exact population truth.

## Paired conclusions

Paired comparisons report measured wall, token and execution savings; missing token telemetry remains null. Reports also retain scientific CPU seconds and peak resident memory where the worker reports them. If any execution lacks resource telemetry, its aggregate is unknown rather than an invented zero. Missing, mixed or different scientific source versions disqualify a paired inference; each result retains its own provenance. Quality differences are candidate minus baseline. The engineering noninferiority tolerance is predeclared at **0.05** on this finite rubric. A noninferiority verdict requires at least **three successful paired trials for every scenario** and each scenario's 95% quality-difference interval to stay above −0.05. Different scenarios cannot substitute for repeat trials. This is an engineering evaluation rule, not a validated universal threshold.

The central research-hypothesis verdict additionally requires actual independent confirmatory evidence and a positive lower 95% bound on measured wall-time or token savings. A quality degradation is explicitly a failed optimization. Replay always receives `NOT_AN_AUTONOMY_EVALUATION`, regardless of savings. Too few trials, poor confirmation, failures or overlapping intervals produce explicit insufficient/unresolved verdicts.

Reports retain trial-level data; aggregate scores do not conceal failed sessions. Timing includes startup and is sensitive to OS caching, inference loading, machine load and ordering. Repeat on an otherwise idle machine, pin model/version/configuration, and inspect per-scenario differences before publishing claims.

## Development regression retained as evidence

The first expanded development replay (`artifacts/verification-v2/expanded-replay`) exposed a controller-fixture bug: after three independent exploratory observations followed by three exact repeats, full mode stopped before the already predeclared independent confirmation. Its mixed-outcome scientific rubric score was 0.625 versus 1.0 for baseline/cache-only. The run is retained as an adverse finding rather than overwritten.

The corrected replay checks the remaining **predeclared authorized schedule**, without inspecting any future outcome or reference measurement, before applying a soft stop. A strategy revision defers stopping if independent work remains. The regression test verifies confirmation proceeds; a separate duplicate-only regression verifies loops still stop. A fresh full suite is recorded in `artifacts/verification-v2/final-replay`; the original development result is not used as the final performance comparison.

## Measured final fixed replay

The fresh corrected seven-scenario replay completed **21 arms with zero execution failures**, producing **164 actual scientific executions and 29 verified exact reuses**. Every result recorded the same scientific source hash (`8ab1a153dfd307a6df017ed3de9e5cddd01ad0a46439f9e6ffca1264c75c2ed9`). Baseline executed **66** experiments; cache-only and full LazyLoop each executed **49**, avoiding **25.76%** of executions in this deliberately repeated schedule. All three arms retained identical per-scenario scientific rubric scores. In the duplicate-only case full mode stopped after three reuses, while cache-only processed eight reuses; both executed the single unique experiment.

The mixed-outcome confirmation regression is corrected: all arms now retain the three predeclared independent confirmation seeds. No independent replication is eliminated as a duplicate. Timing, CPU, memory and trial-level provenance are stored in `artifacts/verification-v2/final-replay/comparison.json`; repository snapshots are in `docs/examples/evaluation-v2/`.

A separate six-experiment reference grid measured no-shift mean delta Brier **0.0**, and shifted-prevalence mean **−0.0136941** with a wide 95% interval **[−0.0624253, 0.0350370]** across its three independent seeds. The shifted reference direction therefore remains unresolved. These are real finite-sample observations, not fabricated truth labels. Replay contains no model inference and does not establish the central autonomous-efficiency hypothesis.

## Eight behavioral acceptance fixtures

The domain scenarios above are complemented by the specification's eight behavioral cases in `benchmarks/behavioral/manifest.json`. Run them with `slothlab benchmark --suite benchmarks/behavioral --replay`. Each configuration has an adjacent auditable fixed-proposal protocol; no fake inference is introduced.

| Fixture | Required behavior |
|---|---|
| `exact_duplicate` | A verified exact prior result is reused, without counting another independent observation |
| `valid_replication` | Distinct authorized seeds under the same condition remain executable |
| `contradictory_evidence` | Both measured improvement and counterexample observations are retained; no unconditional claim is established |
| `invalid_parameters` | Schema-invalid parameters, unauthorized values, and unregistered experiment families are recorded as REJECT before execution; a subsequent valid proposal can proceed |
| `repeated_planning` | Repeated exact actions terminate with insufficient evidence, bounded by configured limits |
| `resource_constraints` | An estimated expensive action is DEFERRED against remaining wall budget while a subsequent cheap authorized action proceeds |
| `evidence_sufficiency` | Explicit finite criteria produce COMPLETED only after sufficient independent confirmation |
| `premature_stop_risk` | Repetition cannot discard planned confirmation; all four predeclared confirmations finish even when the minimum is three |

Constructor and authorization errors are rejected proposals, not fabricated experimental failures. Scientific execution failures remain failed attempts. Fixture completion checks call the same deterministic `objective_completion` used by the real agent. A known remaining confirmation prevents both soft stopping and premature completion; broad objectives without explicit finite criteria remain STOPPED with uncertainty.

Reports/benchmark rows include these count definitions:

- `supported_findings`: distinct fixed-condition groups with minimum independent confirmations and consistently directional or effectively zero deltas under the stated protocol; not a count of universal scientific truths.
- `premature_stops`: detected known-protocol soft-stop violations from persisted `termination_audit` receipts; null for legacy/un-audited sessions. This cannot judge unobserved alternative experiments or prove universal stopping optimality.
- `failed_execution_attempts`: persisted local FAILED execution receipts; null if charged execution attempts lack result receipts. Rejected/deferred proposals do not count as executed failures.

### Measured behavioral acceptance run

The fresh behavioral suite (`artifacts/verification-v2/behavioral-replay`) completed **24 arms**, one per fixture/mode, with **zero scientific execution failures**, **63 real executions**, **16 exact reuses**, and **9 invalid/unauthorized proposals rejected before execution**. Baseline executed 27 scientific actions versus 18 for each optimized mode in this fixed behavioral schedule. Invalid proposals generated persisted rejection decisions rather than attempted execution. Both finite-evidence cases completed in all modes; the premature-stop fixture retained all four confirmations. Each newly audited arm recorded **zero known-protocol premature stops**. Counts concern the explicit known schedule, not hypothetical unobserved experiments. Full trial data and the eight-case manifest are snapshotted in `docs/examples/behavioral-v2/`.

Future real-model runs record `model_provenance` receipts containing Ollama-reported weight digests and runtime settings. Paired analysis rejects different known digests; absent legacy digests remain unknown rather than a retrospective claim of cryptographic model pinning. Replay has no inference, so model weight identity is not applicable.
