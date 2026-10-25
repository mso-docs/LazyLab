"""Private subprocess entrypoint; reads one validated specification from stdin."""
import json
import math
from pathlib import Path
import sys
import time


def main():
    request = json.load(sys.stdin)
    # Limits are applied before numerical libraries are imported.
    try:
        import resource
        memory = int(request["memory_mb"]) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        cpu = max(1, math.ceil(float(request["timeout"])))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        limits = "RLIMIT_AS, RLIMIT_CPU, RLIMIT_CORE"
    except ImportError:
        limits = "unavailable on this platform; parent wall timeout only"
    from slothlab.schemas import ExperimentSpec
    from slothlab.experiments.registry import registered_experiment
    import numpy as np
    spec = ExperimentSpec.model_validate(request["spec"])
    # Defense in depth for registered Python functions. This blocks Python socket
    # and child-process APIs, but native extensions retain normal OS permissions.
    # It is deliberately not represented as OS/container network isolation.
    def deny_external_actions(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}:
            raise PermissionError("Network and child-process APIs are disabled in experiment workers")
        if event == 'open' and isinstance(args[0], (str, bytes)):
            filename = Path(args[0]).resolve()
            flags = args[2] if len(args)>2 and isinstance(args[2],int) else 0
            import os
            writing = bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not filename.is_relative_to(Path.cwd()) and str(filename) != '/dev/null':
                raise PermissionError('Experiment writes are restricted to its artifact directory')
    sys.addaudithook(deny_external_actions)
    started = time.perf_counter()
    metrics, data = registered_experiment(spec.experiment_family)(spec.parameters, spec.seed)
    directory = Path.cwd()
    dataset_path = directory / "data.npz"
    np.savez_compressed(dataset_path, **data)
    (directory / "spec.json").write_text(spec.model_dump_json(indent=2))
    try:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        telemetry={'cpu_seconds':usage.ru_utime+usage.ru_stime,'peak_memory_bytes':usage.ru_maxrss*1024}
    except (NameError,AttributeError):
        telemetry={'cpu_seconds':None,'peak_memory_bytes':None}
    print(json.dumps({"metrics": metrics, "scientific_runtime_seconds": time.perf_counter() - started,
                      "artifacts": [str(dataset_path), str(directory / "spec.json")],
                      "resource_limits": limits, "network_guard": "Python audit hook; OS network isolation depends on selected backend", 'resource_usage':telemetry}, allow_nan=False))


if __name__ == "__main__":
    main()
