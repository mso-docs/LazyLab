"""Compact model-facing contracts, separate from durable application metadata.

Only the model chooses scientific conditions, seeds, and predictions. Identifiers,
protocol versions, ownership, timestamps and replication identities are supplied by
trusted application code, so small models need not regenerate infrastructure.
"""
from copy import deepcopy
import hashlib
import json
from slothlab.schemas import Parameters


def _compact(value):
    if isinstance(value, dict):
        return {k: _compact(v) for k, v in value.items() if k not in {"title", "default", "description"}}
    if isinstance(value, list):
        return [_compact(v) for v in value]
    return value


def hypotheses_schema():
    return {"type": "object", "additionalProperties": False, "properties": {
        "hypotheses": {"type": "array", "minItems": 2, "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"statement": {"type": "string", "minLength": 1},
                "falsifiable_prediction": {"type": "string", "minLength": 1},
                "expected_delta_direction": {"enum": ["negative", "positive", None]},
                "assumptions": {"type": "array", "items": {"type": "string"}}},
            "required": ["statement", "falsifiable_prediction", "expected_delta_direction", "assumptions"]}}},
        "required": ["hypotheses"]}


def decode_hypotheses(payload, session_id):
    result = deepcopy(payload)
    for hypothesis in result.get("hypotheses", []):
        hypothesis["session_id"] = session_id
    return result


def condition_key(parameters):
    values = parameters.model_dump() if hasattr(parameters, "model_dump") else parameters
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def replication_group(parameters):
    return "condition-" + hashlib.sha256(condition_key(parameters).encode()).hexdigest()[:16]


class NoViablePlan(ValueError):
    """No permitted scientific action can satisfy the current protocol stage."""


def planning_schema(config, hypotheses, can_confirm, has_evidence, previous_specs=(), require_confirmation=False):
    parameters = _compact(Parameters.model_json_schema())
    for key, allowed in config.objective.permitted_parameters.items():
        parameters["properties"][key]["enum"] = allowed
    parameters["required"] = list(Parameters.model_fields)
    phases = ["confirmatory"] if require_confirmation else (["exploratory", "confirmatory"] if can_confirm else ["exploratory"])
    allowed_phases = config.objective.constraints.get("allowed_phases", phases)
    phases = [p for p in phases if p in allowed_phases]
    fixed = all(len(config.objective.permitted_parameters.get(k, [])) == 1 for k in Parameters.model_fields)
    used = {p.seed for p in previous_specs if p.phase == "exploratory"}
    variants = []
    for phase in phases:
        seeds = list(config.exploratory_seeds if phase == "exploratory" else config.confirmatory_seeds)
        # Exclusion is safe only in a fully specified single-condition domain.
        # Never restore consumed seeds when the permitted domain is exhausted.
        if phase == "exploratory" and fixed and config.mode == "lazyloop":
            seeds = [seed for seed in seeds if seed not in used]
        if not seeds:
            continue
        props = {"hypothesis_id": {"type": "string", "enum": [h.id for h in hypotheses]},
                 "parameters": parameters,
                 "seed": {"type": "integer", "enum": seeds},
                 "phase": {"type": "string", "enum": [phase]},
                 "rationale": {"type": "string", "minLength": 1}}
        variants.append({"type": "object", "additionalProperties": False,
                         "properties": props, "required": list(props)})
    if not variants:
        raise NoViablePlan("No unused authorized seeds remain for the permitted protocol phase")
    items = variants[0] if len(variants) == 1 else {"anyOf": variants}
    groups = config.objective.success_criteria.get("minimum_confirmatory_groups", 1)
    minimum = groups*config.budget.minimum_replications if require_confirmation else (0 if has_evidence else 1)
    return {"type": "object", "additionalProperties": False, "properties": {
        "candidates": {"type": "array", "minItems": minimum,
                       "maxItems": config.budget.max_candidates,
                       "items": items}}, "required": ["candidates"]}


def decode_plan(payload):
    # Existing persisted/test contracts can still supply metadata; the actual
    # model-facing contract excludes it. Unknown keys remain schema errors.
    result = deepcopy(payload)
    for candidate in result.get("candidates", []):
        if not candidate.get("replicate_group") and isinstance(candidate.get("parameters", {}), dict):
            p = Parameters.model_validate(candidate.get("parameters", {}))
            candidate["replicate_group"] = replication_group(p)
    return result


def validate_confirmation_batch(candidates, config):
    """Validate every condition in the one predeclared final held-out batch."""
    groups = {}
    required = config.objective.success_criteria.get("minimum_confirmatory_groups", 1)
    minimum = config.budget.minimum_replications
    for spec in candidates:
        if spec.phase != "confirmatory" or spec.seed not in config.confirmatory_seeds:
            raise ValueError("Final confirmation requires phase confirmatory and reserved confirmation seeds")
        key = condition_key(spec.parameters)
        condition = groups.setdefault(key, [])
        if any(previous.seed == spec.seed for previous in condition):
            raise ValueError("Final confirmation requires distinct reserved seeds within each condition")
        condition.append(spec)
    if len(groups) < required or any(len(observations) < minimum for observations in groups.values()):
        raise ValueError(f"Final confirmation requires at least {required} conditions, each with {minimum} independent reserved seeds")
    return groups
