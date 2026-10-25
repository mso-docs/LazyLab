"""Explicit scientific tool allowlist; models cannot supply executable code."""
from slothlab.experiments.calibration import run_experiment
REGISTRY = {"prior_correction": run_experiment}


def registered_experiment(name: str):
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unregistered experiment family: {name}") from exc
