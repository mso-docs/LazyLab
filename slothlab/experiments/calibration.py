"""Protocol 1: independent samples from shared synthetic class conditionals.

The evaluation class prevalence is an oracle input; this is not an estimator of
unknown deployment prevalence. Gaussian feature noise preserves label shift.
"""
from __future__ import annotations
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from slothlab.schemas import Parameters


def generate_dataset(parameters: Parameters, seed: int) -> dict[str, np.ndarray]:
    p = parameters
    n = p.sample_size
    # A single generator fixes the class-conditional geometry for BOTH splits.
    # Separate calls to make_classification would change that geometry.
    x, y = make_classification(
        n_samples=4 * n + 200, n_features=p.feature_count,
        n_informative=min(4, p.feature_count), n_redundant=0,
        n_clusters_per_class=1, weights=[0.5, 0.5], flip_y=0,
        class_sep=p.class_separation, random_state=seed,
    )
    rng = np.random.default_rng(seed)
    if p.noise:
        x = x + rng.normal(0, p.noise, x.shape)
    train_ids, eval_ids = [], []
    positives_train = int(round(n * p.train_prevalence))
    positives_eval = int(round(n * p.evaluation_prevalence))
    for label in (0, 1):
        indices = rng.permutation(np.flatnonzero(y == label))
        train_count = positives_train if label else n - positives_train
        eval_count = positives_eval if label else n - positives_eval
        if len(indices) < train_count + eval_count:
            raise ValueError("Insufficient class pool; no replacement sampling is permitted")
        train_ids.extend(indices[:train_count])
        eval_ids.extend(indices[train_count:train_count + eval_count])
    train_ids = rng.permutation(np.asarray(train_ids))
    eval_ids = rng.permutation(np.asarray(eval_ids))
    return {"x_train": x[train_ids], "y_train": y[train_ids],
            "x_eval": x[eval_ids], "y_eval": y[eval_ids],
            "train_ids": train_ids, "eval_ids": eval_ids}


def prior_correction(probabilities: np.ndarray, train_prevalence: float,
                     evaluation_prevalence: float) -> np.ndarray:
    if not 0 < train_prevalence < 1 or not 0 < evaluation_prevalence < 1:
        raise ValueError("Prevalences must be strictly between zero and one")
    probabilities = np.asarray(probabilities, dtype=float)
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Probabilities must be finite and in [0, 1]")
    positive = probabilities * evaluation_prevalence / train_prevalence
    negative = (1 - probabilities) * (1 - evaluation_prevalence) / (1 - train_prevalence)
    return positive / (positive + negative)


def run_experiment(parameters: Parameters, seed: int) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    data = generate_dataset(parameters, seed)
    classifier = LogisticRegression(C=parameters.logistic_c, max_iter=1000,
                                    solver="lbfgs", random_state=seed)
    classifier.fit(data["x_train"], data["y_train"])
    baseline = classifier.predict_proba(data["x_eval"])[:, 1]
    # Temperature deliberately models miscalibration; it does not use eval labels.
    clipped = np.clip(baseline, 1e-12, 1 - 1e-12)
    logits = np.log(clipped / (1 - clipped)) / parameters.probability_temperature
    baseline = 1 / (1 + np.exp(-np.clip(logits, -700, 700)))
    train_prior = float(np.mean(data["y_train"]))
    oracle_prior = float(np.mean(data["y_eval"]))
    corrected = prior_correction(baseline, train_prior, oracle_prior)
    y = data["y_eval"]
    metrics = {
        "baseline_brier": float(brier_score_loss(y, baseline)),
        "corrected_brier": float(brier_score_loss(y, corrected)),
        "baseline_log_loss": float(log_loss(y, baseline, labels=[0, 1])),
        "corrected_log_loss": float(log_loss(y, corrected, labels=[0, 1])),
        "sample_size": float(parameters.sample_size), "seed": float(seed),
        "actual_train_prevalence": train_prior,
        "oracle_evaluation_prevalence": oracle_prior,
    }
    metrics["delta_brier"] = metrics["corrected_brier"] - metrics["baseline_brier"]
    metrics["delta_log_loss"] = metrics["corrected_log_loss"] - metrics["baseline_log_loss"]
    if not all(np.isfinite(v) for v in metrics.values()):
        raise ValueError("Experiment produced non-finite measurements")
    data.update(baseline_probabilities=baseline, corrected_probabilities=corrected)
    return metrics, data
