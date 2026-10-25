"""Predeclared numerical objective completion, separate from model opinions."""
from collections import defaultdict
from slothlab.agent.planner import condition_key


def objective_completion(config, specs, results, verified):
    criteria = config.objective.success_criteria
    explicit = set(criteria) - {"minimum_replications"}
    if not explicit:
        return {"satisfied": False, "reason": "No explicit operational completion criterion was declared", "evidence_ids": []}
    by_id = {s.id: s for s in specs}
    observations = []
    unique = set()
    for r in results:
        spec = by_id.get(r.experiment_id)
        if spec and verified(r):
            identity = (condition_key(spec.parameters), spec.seed, spec.phase)
            if identity not in unique:
                observations.append((spec, r))
                unique.add(identity)
    exploratory = [(s, r) for s, r in observations if s.phase == "exploratory"]
    conditions = {condition_key(s.parameters) for s, _ in exploratory}
    if len(exploratory) < criteria.get("minimum_exploratory_experiments", 1):
        return {"satisfied": False, "reason": "Exploratory evidence target not met", "evidence_ids": []}
    if len(conditions) < criteria.get("minimum_conditions", 1):
        return {"satisfied": False, "reason": "Distinct-condition target not met", "evidence_ids": []}
    confirmation = criteria.get("require_confirmation", True)
    phase = "confirmatory" if confirmation else "exploratory"
    groups = defaultdict(dict)
    exploratory_seeds = {s.seed for s, _ in exploratory}
    for s, r in observations:
        if s.phase == phase and (phase != "confirmatory" or s.seed not in exploratory_seeds):
            groups[condition_key(s.parameters)].setdefault(s.seed, r)
    minimum = max(3, criteria.get("minimum_replications", config.budget.minimum_replications))
    direction, tolerance = criteria.get("effect_direction", "either"), criteria.get("effect_tolerance", 1e-10)
    qualified = []
    for values in groups.values():
        if len(values) < minimum:
            continue
        deltas = [r.metrics["delta_brier"] for r in values.values()]
        negative, positive = all(d < -tolerance for d in deltas), all(d > tolerance for d in deltas)
        zero = all(abs(d) <= tolerance for d in deltas)
        match = {"negative": negative, "positive": positive, "zero": zero, "either": negative or positive or zero}[direction]
        if match:
            qualified.append(list(values.values()))
    target = criteria.get("minimum_confirmatory_groups", 1) if confirmation else criteria.get("minimum_conditions", 1)
    satisfied = len(qualified) >= target
    return {"satisfied": satisfied,
            "reason": "Predeclared operational research criteria satisfied; conclusions are scoped to the tested conditions" if satisfied else "Independent replicated effect target not met",
            "qualifying_groups": len(qualified), "observed_conditions": len(conditions),
            "evidence_ids": [r.id for group in qualified for r in group]}
