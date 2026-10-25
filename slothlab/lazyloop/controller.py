"""Deterministic authorization, observable priorities and exact-result reuse."""
from slothlab.schemas import ExperimentSpec, LazyLoopDecision
from slothlab.lazyloop.fingerprint import fingerprint


def validate_proposal(spec, config, hypothesis_ids):
    if spec.hypothesis_id not in hypothesis_ids:
        raise ValueError("Unknown hypothesis reference")
    allowed_seeds = config.exploratory_seeds if spec.phase == "exploratory" else config.confirmatory_seeds
    if spec.seed not in allowed_seeds:
        raise ValueError("Seed does not belong to its predeclared phase partition")
    for key, allowed in config.objective.permitted_parameters.items():
        if getattr(spec.parameters, key) not in allowed:
            raise ValueError(f"Parameter {key} outside authorized values")
    constraints = config.objective.constraints
    for key, bounds in constraints.get("parameter_bounds", {}).items():
        value = getattr(spec.parameters, key)
        if value < bounds.get("min", value) or value > bounds.get("max", value):
            raise ValueError(f"Parameter {key} violates the declared bounds")
    if spec.phase not in constraints.get("allowed_phases", ["exploratory", "confirmatory"]):
        raise ValueError("Experiment phase is not authorized")
    if spec.estimated_compute_seconds > constraints.get("max_estimated_compute_seconds", float("inf")):
        raise ValueError("Estimated cost violates the objective constraint")
    if constraints.get("require_replication_group") and not spec.replicate_group:
        raise ValueError("A shared replication group is required")


def observed_specs(repo, session_id):
    """Resolve cached provenance as well as this session's own measurements."""
    specs = {s.id: s for s in repo.specs(session_id)}
    observations = []
    for result in repo.results(session_id):
        if result.status != "COMPLETED" or not repo.verified(result):
            continue
        spec = specs.get(result.experiment_id)
        if spec is None:
            try:
                spec = repo.get_spec(result.experiment_id)
            except KeyError:
                continue
        observations.append((spec, result))
    return observations


def decide(spec: ExperimentSpec, session, config, repo):
    consumed, budget = session.budget_consumed, session.budget_configuration
    remaining = max(0, budget.wall_seconds - consumed["wall_seconds"])
    base = dict(experiment_id=spec.id, session_id=session.id,
                estimated_cost=spec.estimated_compute_seconds,
                available_budget={"wall_seconds": remaining,
                                  "experiments": max(0, budget.max_experiments-consumed["experiments"])})
    cached = repo.find_completed(fingerprint(spec))
    if cached and session.mode != "baseline":
        return LazyLoopDecision(**base, decision="REUSE", reason="Verified exact experiment already completed",
                                evidence_references=[cached.id], score_components={"information": 0.0, "novelty": 0.0,
                                "relevance": 1.0, "feasibility": 1.0, "cost": 0.0}), cached
    observations = observed_specs(repo, session.id)
    same = [(s, r) for s, r in observations if s.id != spec.id and s.parameters == spec.parameters
            and s.phase == spec.phase and s.seed != spec.seed]
    is_replication = bool(same)
    if is_replication and (not spec.replicate_group or not any(s.replicate_group == spec.replicate_group for s, _ in same)):
        return LazyLoopDecision(**base, decision="REJECT", reason="Independent replication requires the existing shared replicate_group"), None
    independent = {s.seed: r for s, r in same}
    deltas = [r.metrics.get("delta_brier", 0.0) for r in independent.values()]
    conflicting = any(d < 0 for d in deltas) and any(d > 0 for d in deltas)
    # This intentionally simple heuristic rewards resolving contradictory evidence
    # and collecting required independent replications. Scores are not probabilities.
    information = 0.95 if conflicting else (0.85 if is_replication and len(independent) < budget.minimum_replications else 0.65)
    if is_replication and len(independent) >= budget.minimum_replications and not conflicting:
        information = 0.20
    if spec.phase == "confirmatory":
        information = max(information, 0.90)
    components = {"information": information, "novelty": 0.75 if is_replication else 1.0,
                  "relevance": 1.0, "feasibility": 1.0,
                  "cost": min(1.0, spec.estimated_compute_seconds/budget.experiment_timeout)}
    score = (0.35*components["information"] + 0.30*components["novelty"] + 0.20*components["relevance"]
             + 0.15*components["feasibility"] - config.cost_penalty*components["cost"])
    if consumed["experiments"] >= budget.max_experiments or remaining <= 0:
        action, reason = "STOP", "Hard execution budget exhausted"
    elif spec.estimated_compute_seconds > remaining:
        action, reason = "DEFER", "Estimated cost exceeds remaining wall budget"
    else:
        action = "REPLICATE" if is_replication else "EXECUTE"
        reason = "Independent seed under identical conditions" if is_replication else "Authorized feasible candidate"
        if conflicting:
            reason += "; independent replication can resolve contradictory measured directions"
    return LazyLoopDecision(**base, decision=action, reason=reason, priority_score=score,
                            score_components=components, evidence_references=[r.id for _, r in same]), None
