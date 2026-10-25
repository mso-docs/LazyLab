import numpy as np
import pytest
from pydantic import ValidationError
from slothlab.schemas import ExperimentSpec, Parameters
from slothlab.experiments.calibration import generate_dataset, prior_correction, run_experiment
from slothlab.experiments.executor import execute
from slothlab.lazyloop.fingerprint import fingerprint


def test_dataset_reproducible_and_disjoint():
    a = generate_dataset(Parameters(sample_size=200), 42)
    b = generate_dataset(Parameters(sample_size=200), 42)
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])
    assert not set(a["train_ids"]) & set(a["eval_ids"])
    assert a["y_train"].mean() == 0.5
    assert a["y_eval"].mean() == 0.2


def test_correction_reference_and_identity():
    p = np.array([0., .1, .5, .9, 1.])
    odds_multiplier = (.2 / .8) / (.5 / .5)
    expected = p * odds_multiplier / (1 - p + p * odds_multiplier)
    np.testing.assert_allclose(prior_correction(p, .5, .2), expected)
    np.testing.assert_allclose(prior_correction(p, .2, .2), p)
    with pytest.raises(ValueError):
        prior_correction(np.array([np.nan]), .5, .2)


def test_experiment_metrics_reproduce():
    a, _ = run_experiment(Parameters(sample_size=200), 12)
    b, _ = run_experiment(Parameters(sample_size=200), 12)
    assert a == b
    assert -1 <= a["delta_brier"] <= 1
    assert a["delta_brier"] == a["corrected_brier"] - a["baseline_brier"]
    assert a["baseline_log_loss"] >= 0


@pytest.mark.parametrize("params", [{"sample_size": 1}, {"train_prevalence": 0},
                                      {"feature_count": 1}, {"noise": float("nan")}])
def test_invalid_parameters(params):
    with pytest.raises(ValidationError):
        Parameters(**params)


def test_fingerprint_ignores_prose_and_tracks_seed():
    spec = ExperimentSpec(hypothesis_id="h", seed=1, rationale="investigate")
    assert fingerprint(spec) == fingerprint(spec.model_copy(update={"id": "new", "rationale": "changed"}))
    assert fingerprint(spec) != fingerprint(spec.model_copy(update={"seed": 2}))
    assert fingerprint(spec) != fingerprint(spec.model_copy(update={"phase": "confirmatory"}))


def test_executor_real_artifacts_and_timeout(tmp_path):
    spec = ExperimentSpec(hypothesis_id="h", seed=42, rationale="test", parameters=Parameters(sample_size=200))
    result = execute(spec, tmp_path)
    assert result.status == "COMPLETED", result.error_details
    assert result.environment_metadata["oracle_prevalence"] is True
    assert len(result.artifact_paths) == 2
    data = np.load(result.artifact_paths[0])
    assert not set(data["train_ids"]) & set(data["eval_ids"])
    failed = execute(spec.model_copy(update={"id": "timeout"}), tmp_path, timeout=.0001)
    assert failed.status == "FAILED"
    assert failed.error_details


def test_path_traversal_ids_are_not_paths(tmp_path):
    spec = ExperimentSpec(id="../../outside", hypothesis_id="h", seed=1, rationale="test", parameters=Parameters(sample_size=100))
    result = execute(spec, tmp_path)
    assert result.status == "COMPLETED", result.error_details
    from pathlib import Path
    assert all(Path(p).is_relative_to(tmp_path) for p in result.artifact_paths)
