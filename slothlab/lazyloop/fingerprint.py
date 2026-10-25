"""Scientific identities exclude prose, proposal IDs and hypothesis IDs."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
from slothlab.schemas import ExperimentSpec


def _source_hash() -> str:
    source_dir = Path(__file__).resolve().parents[1] / "experiments"
    code = hashlib.sha256()
    for name in ("calibration.py", "registry.py", "worker.py", "executor.py"):
        code.update(name.encode())
        code.update((source_dir / name).read_bytes())
    return code.hexdigest()


def environment_metadata() -> dict:
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")}
    return {"python": platform.python_version(), "platform": platform.platform(),
            "dependencies": versions, "source_sha256": _source_hash(), "oracle_prevalence": True,
            "isolation": "registered subprocess; resource limits; not a hardened sandbox"}


def _canonical(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    return value


def fingerprint(spec: ExperimentSpec) -> str:
    identity = {"family": spec.experiment_family, "dataset": spec.dataset_id,
                "protocol": spec.protocol_version, "parameters": spec.parameters.model_dump(),
                "seed": spec.seed, "phase": spec.phase, "source_sha256": _source_hash(),
                "environment": environment_metadata()}
    encoded = json.dumps(_canonical(identity), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()
