# Prior correction protocol 1

SlothLab studies a finite synthetic question: under which authorized conditions does correcting predicted probabilities for a **known change in class prevalence** reduce predictive loss? Its measurements describe the configured synthetic generator and methods. They do not establish that deployment prevalence is known or that correction always helps.

## Data generation and independence

For each seed, one `sklearn.datasets.make_classification` invocation defines shared class-conditional geometry for training and evaluation. A sufficiently large balanced pool is generated with no label flipping. Class indices are randomly permuted, then disjoint training and evaluation subsets are selected without replacement at the requested prevalences. Stored sample indices permit checking that evaluation rows never enter training.

The same seed and scientific configuration reproduce the numerical experiment. Different seeds produce independent trials and also vary the synthetic problem geometry. Thus replication estimates variation over the generator distribution, rather than repeatedly measuring a single fixed population. Within each trial, the class-conditional construction is shared across the prevalence shift.

`noise` means additive Gaussian **feature noise**, not label-flip probability. Shared noise preserves the intended label-shift construction. Requested prevalences are rounded to integer class counts; the measured training prevalence and oracle evaluation prevalence are recorded and used in correction.

## Scientific method and measurements

Logistic regression fits training data only, with configured regularization, deterministic seeds, the `lbfgs` solver and a fixed iteration limit. Optional probability temperature deliberately changes calibration without fitting evaluation labels. Given the resulting training posterior `p`, measured training prevalence `a` and oracle evaluation prevalence `b`, correction is:

```text
(p*b/a) / (p*b/a + (1-p)*(1-b)/(1-a))
```

Brier score and log loss for corrected and uncorrected predictions use the same evaluation sample. Each delta equals corrected minus baseline: **negative means correction reduced loss**. Equal training and evaluation prevalence supplies an identity control, checked within numerical tolerance. Improvements and regressions are both valid observations; a single unfavorable delta does not establish that a stochastic hypothesis is false.

Each completed experiment records parameters, seed, phase, actual prevalences, both losses and deltas, runtime, environment/source versions, and artifact hashes. NPZ artifacts contain training/evaluation features, labels, disjoint sample indices, and both probability arrays. Parameter snapshots and an atomic result receipt support reproducibility and recovery. Failed or incomplete results cannot be reused as successful evidence.

## Model choices and deterministic authorization

The model-facing hypothesis and planning contracts contain scientific choices rather than infrastructure metadata. The local model proposes falsifiable predictions, hypothesis references, authorized parameters, seeds, phases and rationales. The application supplies ownership, durable IDs, timestamps, protocol identity and consistent replication provenance. No scientific measurement is supplied by a fake application model or inferred from a rationale.

Planning schemas correlate each phase with its permitted seed partition: an exploratory record cannot select a reserved confirmation seed merely because both phases are available. Independent validation still checks registered family, parameter authorization/bounds, hypothesis ownership, allowed phase, seed partition, replication requirements and resource budgets before execution. Malformed outputs receive only bounded repairs. Structural repetition is tracked by actual scientific configuration and seed, never by prose similarity alone.

Exact successful experiments can be reused after numerical and artifact-integrity checks. Reuse preserves the original result identity and adds an evidence link; it does not create an independent measurement. The same condition with a different independent seed is a legitimate replication. A fixed one-condition domain never restores consumed exploratory seeds when no unused seeds remain.

## Exploration and one final confirmation batch

Exploratory and confirmatory seed sets are declared in advance and must be disjoint. For objectives with explicit operational criteria requiring confirmation, the deterministic controller keeps planning exploratory until the predefined exploratory experiment and distinct-condition targets are met. It then requests **one final held-out confirmation batch**; the model still selects the authorized conditions, hypothesis references and reserved seeds.

A final batch may contain multiple parameter conditions. Each condition must have identical parameters within its replication group and at least the configured minimum number of distinct reserved seeds, with an engineering default of three. Multiple groups require enough candidate and execution budget for `minimum_confirmatory_groups × minimum_replications` records. The same reserved seeds may be paired across different conditions for comparison; independence is counted **within each condition**, not multiplied by presenting paired conditions as independent trials of one claim.

Final-batch structure is checked during bounded model-output repair and again before execution. Confirmation outcomes never guide a later planning round. If an investigation is interrupted during confirmation, verified completed receipts are reconciled first and the already-authorized batch is finished before assessing success. Any uncommitted retry incurs another reservation. An unavailable budget or execution failure produces an explicit insufficient-evidence/failure outcome rather than selecting a favorable partial subset.

## Hypothesis assessment and revision

The model interprets recorded results using actual evidence IDs. Its free-form explanation and suggested status remain provisional. An independent numerical critic can assess only a declared `expected_delta_direction` for `delta_brier`: it requires verified measurements from at least the configured minimum number of independent seeds under identical parameters and phase. Consistently aligned directions can support that **scoped directional prediction**; consistently opposite directions can contradict it. Mixed, near-zero, insufficient, or unstructured predictions remain inconclusive. These statuses do not certify every assertion in a natural-language hypothesis.

A hypothesis revision requires valid cited measurements and a complete new statement and falsifiable prediction. The application preserves the old declaration and assessment, creates a **new untested hypothesis ID**, and records the old/new provenance. Prior observations that inspired a revision do not automatically become independent confirmation of it. Duplicate revisions do not recursively create copies. The latest recorded scientific direction is supplied to subsequent planning.

## Finite completion criteria and uncertainty

`COMPLETED` means the configured operational criteria were met, not that an unrestricted research question has been universally solved. Supported criteria include independent replication counts, minimum exploratory experiments, minimum distinct exploratory conditions, whether confirmation is required, minimum confirmatory groups, effect direction and effect tolerance. Unsupported arbitrary predicates are rejected rather than silently treated as satisfied.

For directional completion, each qualifying group must have consistent improvement, consistent regression, or effects within the declared zero tolerance, as requested. `effect_direction: either` accepts any one of those consistent characterizations; it does not accept an arbitrary mixture of signs within a group. An objective containing only the default minimum replication setting does not provide a general automatic certificate of scientific completion. Budgets, exhausted actions, repeated unproductive planning and low-information stopping retain explicit reasons and preserve insufficient evidence.

The minimum replication count and signed-effect rules are engineering protocol criteria, not validated statistical stopping thresholds. They must not be presented as significance tests or proofs of generality.

## Confidence intervals and reporting

Reports calculate a **95% Student-t interval** for the mean confirmatory delta Brier across distinct reserved seeds in each condition/replication group:

```text
mean(delta) ± t(0.975, n-1) * sample_std(delta) / sqrt(n)
```

The interval is unavailable when fewer than two independent seed observations identify variance. It is a diagnostic under assumptions about independent sampling and the distribution of seed-level effects; small-sample coverage may be poor when those assumptions fail. There is no multiple-comparison correction, and these intervals do not account for every exploratory selection decision or justify universal deployment claims. A consistently signed small sample may still have an interval spanning zero. Completion/criticism uses the declared protocol rules rather than relabeling that interval as a proof.

Reports retain the result IDs behind numerical findings, the tested parameter conditions, confirmatory seed counts, uncertainty, proposed model interpretations and deterministic assessment receipts. Computational cost and the finite scientific-quality rubric are reported separately; fewer executions alone do not establish that autonomous research quality was preserved.

## Scope of stopping audits

New terminal research records include an observational `termination_audit`. It flags a known protocol omission only when an already-persisted, authorized final confirmation batch remains unfinished, its declared estimates still fit the remaining resource/planning limits, and no hard-budget or critical-failure boundary justifies stopping. Verified exact reuse satisfies the corresponding proposal without creating another measurement. The audit does not change the stopping policy and makes no prediction that unmeasured future research would improve the science.

This is deliberately a finite **known authorized final-batch protocol** audit, not a universal measure of premature research termination. A false flag means no omission was identified within that scope; it does not prove optimal stopping. Historical runs without the event retain unknown stopping-audit telemetry rather than an invented zero.
