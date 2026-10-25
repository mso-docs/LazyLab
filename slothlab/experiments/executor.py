"""Restricted registered-function subprocess executor, NOT a security sandbox.

No generated source, shell evaluation, or network tool is accepted. The worker has
ordinary OS user permissions; use containers for hostile code or OS isolation.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from slothlab.schemas import ExperimentResult, ExperimentSpec
from slothlab.lazyloop.fingerprint import environment_metadata, fingerprint
from slothlab.runtime.atomic import atomic_json
from slothlab.experiments.isolation import command as isolated_command


def experiment_directory(spec, artifact_dir):
    return Path(artifact_dir).resolve()/hashlib.sha256(spec.id.encode()).hexdigest()[:24]


def recover(spec: ExperimentSpec, artifact_dir: Path) -> ExperimentResult | None:
    """Reconcile a fully committed worker receipt after an orchestrator crash."""
    from slothlab.memory.repository import Repository
    directory=experiment_directory(spec,artifact_dir)
    manifest=directory/'result.json'
    if not manifest.is_file() or manifest.is_symlink():
        return None
    try:
        result=ExperimentResult.model_validate_json(manifest.read_text())
        if result.experiment_id!=spec.id or result.fingerprint!=fingerprint(spec):
            return None
        if not result.artifact_paths or not result.environment_metadata.get('artifact_sha256'):
            return None
        if any(Path(p).resolve().parent!=directory for p in result.artifact_paths):
            return None
        return result if Repository.verified(result) else None
    except (OSError,ValueError):
        return None


def execute(spec: ExperimentSpec, artifact_dir: Path, timeout: float = 30,
            memory_mb: int = 2048, isolation: str = 'auto') -> ExperimentResult:
    spec = ExperimentSpec.model_validate(spec.model_dump())
    if timeout <= 0 or memory_mb < 256:
        raise ValueError("Positive timeout and at least 256 MiB memory are required")
    identity = fingerprint(spec)
    metadata = environment_metadata()
    # Model-proposed IDs can never become filesystem paths.
    directory = experiment_directory(spec,artifact_dir)
    if directory.is_symlink():
        raise ValueError("Experiment output directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "LANG", "LC_ALL", "SYSTEMROOT"}}
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               PYTHONPATH=str(Path(__file__).resolve().parents[2]),
               PYTHONNOUSERSITE="1")
    request = {"spec": spec.model_dump(), "timeout": timeout, "memory_mb": memory_mb}
    started = time.perf_counter()
    try:
        arguments, boundary=isolated_command(directory,isolation)
        metadata['execution_boundary']=boundary
        metadata['isolation']=boundary['backend']
        child = subprocess.run(arguments,
                               input=json.dumps(request), text=True, capture_output=True,
                               cwd=directory, env=env, timeout=timeout, check=True)
        output = json.loads(child.stdout)
        if boundary['backend']=='bubblewrap' and any(Path(p).parent!=Path('/work') for p in output['artifacts']):
            raise ValueError('Worker artifact escaped the approved output directory')
        artifact_paths = [str(directory/Path(p).name) if boundary['backend']=='bubblewrap' else p for p in output["artifacts"]]
        hashes = {}
        for filename in artifact_paths:
            path = Path(filename).resolve()
            if path.parent != directory:
                raise ValueError("Worker artifact escaped the approved output directory")
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata.update(artifact_sha256=hashes, resource_limits=output["resource_limits"],
                        network_guard=output["network_guard"],
                        resource_usage=output.get('resource_usage',{}),
                        scientific_runtime_seconds=output["scientific_runtime_seconds"])
        result = ExperimentResult(experiment_id=spec.id, fingerprint=identity, status="COMPLETED",
                                metrics=output["metrics"], runtime_seconds=time.perf_counter() - started,
                                artifact_paths=artifact_paths, environment_metadata=metadata)
        atomic_json(directory/'result.json',result.model_dump(mode='json'))
        return result
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, RuntimeError) as exc:
        error = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            error += ": " + exc.stderr[-4000:]
        return ExperimentResult(experiment_id=spec.id, fingerprint=identity, status="FAILED",
                                runtime_seconds=time.perf_counter() - started,
                                environment_metadata=metadata, error_details=error)
