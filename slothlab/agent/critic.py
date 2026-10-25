"""Numerical assessment of explicitly declared directional predictions.

This checks a replication protocol, not statistical significance or a general law.
Free-form language is never parsed into a numerical claim.
"""
from collections import defaultdict
import json

from slothlab.memory.repository import Repository
from slothlab.schemas import ExperimentResult, ExperimentSpec, Hypothesis


EPSILON = 1e-10


def assess_hypothesis(
    hypothesis: Hypothesis,
    specs: list[ExperimentSpec],
    results: list[ExperimentResult],
    minimum_replications: int = 3,
) -> dict:
    def conclusion(status, reason, evidence_ids=()):
        return {"status": status, "verified_claim": status != "INCONCLUSIVE",
                "reason": reason, "evidence_ids": list(evidence_ids)}

    expected = hypothesis.expected_delta_direction
    if expected is None:
        return conclusion("INCONCLUSIVE", "No explicit numerical delta_brier direction was declared; free-form predictions cannot be mechanically assessed.")
    required = max(3, minimum_replications)
    by_id = {spec.id: spec for spec in specs if spec.hypothesis_id == hypothesis.id}
    groups = defaultdict(list)
    for result in results:
        spec = by_id.get(result.experiment_id)
        if spec is None or not Repository.verified(result):
            continue
        key = json.dumps({"parameters": spec.parameters.model_dump(), "phase": spec.phase}, sort_keys=True)
        groups[key].append((spec, result))

    qualified = []
    for observations in groups.values():
        independent = {}
        for spec, result in observations:
            if spec.seed in independent:
                # Reusing an identical seed is never another independent trial.
                existing = independent[spec.seed]
                if abs(existing.metrics["delta_brier"] - result.metrics["delta_brier"]) > EPSILON:
                    return conclusion("INCONCLUSIVE", "Conflicting measurements share the same condition and seed; resolve the integrity ambiguity.", [r.id for _, r in observations])
            else:
                independent[spec.seed] = result
        if len(independent) >= required:
            qualified.extend(independent.values())
    if not qualified:
        return conclusion("INCONCLUSIVE", f"Insufficient verified independent replications: need {required} distinct seeds within one identical parameter and phase condition.")

    evidence_ids = list(dict.fromkeys(result.id for result in qualified))
    deltas = [result.metrics["delta_brier"] for result in qualified]
    sign = -1 if expected == "negative" else 1
    aligned = [sign * value for value in deltas]
    scope = "This is a directional replication assessment for the tested conditions, not statistical significance or a universal scientific claim."
    if all(value > EPSILON for value in aligned):
        return conclusion("SUPPORTED", f"All qualifying independent measurements have the declared {expected} delta_brier direction. {scope}", evidence_ids)
    if all(value < -EPSILON for value in aligned):
        return conclusion("CONTRADICTED", f"All qualifying independent measurements have the opposite of the declared {expected} delta_brier direction. {scope}", evidence_ids)
    return conclusion("INCONCLUSIVE", f"Qualifying measurements have mixed directions or effects within {EPSILON:g} of zero. {scope}", evidence_ids)
