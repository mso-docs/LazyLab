"""Structural action tracking; prose similarity never establishes redundancy."""
import hashlib
import json


def action_signature(spec):
    values = {"family": spec.experiment_family, "dataset": spec.dataset_id,
              "parameters": spec.parameters.model_dump(), "seed": spec.seed,
              "phase": spec.phase, "protocol": spec.protocol_version}
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def repeated_actions(candidates, prior_specs):
    known = {action_signature(s) for s in prior_specs}
    seen = set()
    repeated = []
    for candidate in candidates:
        signature = action_signature(candidate)
        if signature in known or signature in seen:
            repeated.append(candidate.id)
        seen.add(signature)
    return repeated
