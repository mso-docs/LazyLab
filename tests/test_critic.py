import pytest

from slothlab.agent.critic import assess_hypothesis
from slothlab.schemas import ExperimentResult, ExperimentSpec, Hypothesis, Parameters


def hypothesis(direction="negative"):
    return Hypothesis(id="h", session_id="session", statement="Correction lowers Brier score", falsifiable_prediction="delta_brier < 0", expected_delta_direction=direction)


def observations(deltas, hypothesis_id="h", seeds=None, parameters=None, phase="exploratory"):
    specs, results = [], []
    for index, delta in enumerate(deltas):
        spec = ExperimentSpec(id=f"e-{hypothesis_id}-{index}", hypothesis_id=hypothesis_id, seed=(seeds or list(range(len(deltas))))[index], rationale="Independent protocol measurement", parameters=parameters or Parameters(), phase=phase)
        result = ExperimentResult(id=f"r-{hypothesis_id}-{index}", experiment_id=spec.id, fingerprint="test-fixture", status="COMPLETED", runtime_seconds=.1, metrics={"baseline_brier": .3, "corrected_brier": .3 + delta, "delta_brier": delta, "baseline_log_loss": .7, "corrected_log_loss": .7 + delta, "delta_log_loss": delta})
        specs.append(spec)
        results.append(result)
    return specs, results


@pytest.mark.parametrize("expected,deltas,status", [("negative", [-.1, -.02, -.05], "SUPPORTED"), ("positive", [.1, .02, .05], "SUPPORTED"), ("negative", [.1, .02, .05], "CONTRADICTED"), ("positive", [-.1, -.02, -.05], "CONTRADICTED"), ("negative", [-.1, .02, -.05], "INCONCLUSIVE"), ("negative", [-.1, 0, -.05], "INCONCLUSIVE"), ("negative", [-.1, -1e-12, -.05], "INCONCLUSIVE")])
def test_explicit_numerical_direction(expected, deltas, status):
    specs, results = observations(deltas)
    assessment = assess_hypothesis(hypothesis(expected), specs, results)
    assert assessment["status"] == status
    assert assessment["verified_claim"] is (status != "INCONCLUSIVE")
    assert assessment["evidence_ids"] == [r.id for r in results]


def test_free_form_predictions_never_inferred_from_text():
    specs, results = observations([-.1, -.1, -.1])
    assessment = assess_hypothesis(hypothesis(None), specs, results)
    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["verified_claim"] is False


def test_cross_hypothesis_evidence_rejected():
    specs, results = observations([-.1, -.1, -.1], hypothesis_id="another")
    assessment = assess_hypothesis(hypothesis(), specs, results)
    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["evidence_ids"] == []


def test_failed_or_inconsistent_metrics_cannot_establish_direction():
    specs, results = observations([-.1, -.1, -.1])
    results[0].status = "FAILED"
    results[1].metrics["corrected_brier"] = .99
    assessment = assess_hypothesis(hypothesis(), specs, results)
    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["verified_claim"] is False


def test_duplicate_seeds_do_not_count_as_independent_replications():
    specs, results = observations([-.1, -.1, -.1], seeds=[1, 1, 2])
    assert assess_hypothesis(hypothesis(), specs, results)["status"] == "INCONCLUSIVE"


def test_different_parameters_and_phases_do_not_pool_replications():
    specs, results = observations([-.1, -.1, -.1])
    specs[0].parameters = Parameters(sample_size=200)
    specs[1].phase = "confirmatory"
    assert assess_hypothesis(hypothesis(), specs, results)["status"] == "INCONCLUSIVE"


def test_minimum_replications_is_honored_and_cannot_drop_below_three():
    specs, results = observations([-.1, -.1, -.1])
    assert assess_hypothesis(hypothesis(), specs, results, minimum_replications=4)["status"] == "INCONCLUSIVE"
    assert assess_hypothesis(hypothesis(), specs[:2], results[:2], minimum_replications=1)["status"] == "INCONCLUSIVE"


def test_conflicting_qualifying_conditions_stay_inconclusive():
    specs, results = observations([-.1, -.1, -.1])
    other_specs, other_results = observations([.1, .1, .1])
    for spec in other_specs:
        spec.id += "-condition-b"
        spec.parameters = Parameters(sample_size=200)
    for spec, result in zip(other_specs, other_results):
        result.id += "-condition-b"
        result.experiment_id = spec.id
    assessment = assess_hypothesis(hypothesis(), specs + other_specs, results + other_results)
    assert assessment["status"] == "INCONCLUSIVE"
    assert len(assessment["evidence_ids"]) == 6
