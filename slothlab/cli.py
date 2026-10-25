"""CLI stays independent of Streamlit; inference is always explicit."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import sqlite3
from slothlab.config import load_config, Config
from slothlab.memory.factory import open_repository
from slothlab.models import client_from_config, ModelError
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.reporting.generator import generate_report


def parser():
    p = argparse.ArgumentParser(prog="slothlab", description="Local evidence-grounded autonomous research")
    p.add_argument("--db", help="Override SQLite memory path")
    p.add_argument('--storage',choices=['sqlite','document'],help='Use SQLite or a database-free JSON research document')
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create local database and artifact directory")
    run = sub.add_parser("run", help="Start an autonomous Ollama investigation")
    run.add_argument("--config", default="configs/calibration.yaml")
    run.add_argument("--mode", choices=["baseline", "cache_only", "lazyloop"])
    run.add_argument('--background',action='store_true',help='Run durably outside the terminal/browser')
    sub.add_parser("demo", help="Run bundled configuration using real Ollama inference")
    for cmd in ("resume", "status", "report"):
        command=sub.add_parser(cmd)
        command.add_argument("session_id")
        if cmd=='resume':
            command.add_argument('--background',action='store_true')
    b = sub.add_parser("benchmark", help="Compare three modes using equivalent scenario constraints")
    b.add_argument("--suite", default="benchmarks/objectives")
    b.add_argument("--output", default=None)
    b.add_argument("--repeats", type=int, default=1)
    b.add_argument("--replay", action="store_true", help="Fixed proposal schedule, real science, no model inference; tests controller only")
    b.add_argument('--reference',help='Independent reference JSON, used only for final evaluation')
    reference=sub.add_parser('reference',help='Generate a reference grid withheld from agent planning')
    reference.add_argument('--config',default='configs/calibration.yaml')
    reference.add_argument('--output',required=True)
    reference.add_argument('--max-conditions',type=int,default=4)
    reference.add_argument('--seeds-per-condition',type=int,default=3)
    doctor=sub.add_parser('doctor',help='Inspect installation, local inference and execution isolation')
    doctor.add_argument('--config')
    doctor.add_argument('--skip-model',action='store_true')
    sub.add_parser('jobs',help='List durable background investigations')
    sub.add_parser('stop',help='Pause a background job safely').add_argument('job_id')
    e = sub.add_parser("experiment", help="Run one registered scientific experiment without an LLM")
    e.add_argument("--seed", type=int, default=0)
    e.add_argument("--train-prevalence", type=float, default=0.5)
    e.add_argument("--evaluation-prevalence", type=float, default=0.2)
    dashboard=sub.add_parser("dashboard", help="Open the interactive Streamlit research workspace")
    dashboard.add_argument('--port',type=int,default=8501)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        logging.basicConfig(level=os.getenv("SLOTHLAB_LOG_LEVEL", "INFO").upper())
        config = load_config(getattr(args,'config',None) if args.command in {'run','reference','doctor'} else "configs/demo.yaml" if args.command == "demo" else None)
        if args.db:
            config.db_path = args.db
        if args.storage:
            config.storage_backend=args.storage
        if args.command == "benchmark":
            from slothlab.evaluation.benchmark import run_benchmark
            from slothlab.schemas import uid
            from slothlab.assets import asset_path
            if args.repeats < 1:
                raise ValueError("--repeats must be positive")
            comparison=run_benchmark(asset_path(args.suite), args.output or f"artifacts/benchmarks/{uid()}", args.replay, args.repeats,reference_path=args.reference)
            print(comparison)
            failed=json.loads(comparison.read_text()).get('failed_runs',0)
            if failed:
                print(f'slothlab: {failed} benchmark arms failed; inspect the saved comparison',file=sys.stderr)
            return 1 if failed else 0
        if args.command == 'reference':
            from slothlab.evaluation.reference import generate_reference_grid
            print(generate_reference_grid(config,args.output,max_conditions=args.max_conditions,seeds_per_condition=args.seeds_per_condition))
            return 0
        if args.command in {'jobs','stop'}:
            from slothlab.runtime.jobs import JobManager
            manager=JobManager(os.getenv('SLOTHLAB_JOB_DIR','artifacts/jobs'))
            print(json.dumps(manager.list_jobs() if args.command=='jobs' else manager.stop(args.job_id),indent=2))
            return 0
        if args.command=='doctor':
            from slothlab.runtime.doctor import diagnose
            result=diagnose(config,check_model=not args.skip_model)
            print(json.dumps(result,indent=2))
            return 0 if result['ready'] else 1
        if args.command == "dashboard":
            import importlib.util
            if importlib.util.find_spec('streamlit') is None:
                raise ValueError('Install dashboard support: python -m pip install "slothlab[dashboard]"')
            if not 1 <= args.port <= 65535:
                raise ValueError('Port must be between 1 and 65535')
            env = dict(os.environ, SLOTHLAB_DB_PATH=config.db_path,SLOTHLAB_STORAGE_BACKEND=config.storage_backend)
            return subprocess.call([sys.executable, "-m", "streamlit", "run", str(Path(__file__).parent/"ui"/"dashboard.py"),'--server.address','127.0.0.1','--server.port',str(args.port),'--server.maxUploadSize','100','--browser.gatherUsageStats','false'], env=env)
        with open_repository(config.db_path,config.storage_backend) as repo:
            if args.command == "init":
                import yaml
                Path(config.artifact_dir).mkdir(parents=True, exist_ok=True)
                template = Path("configs/calibration.yaml")
                if not template.exists():
                    template.parent.mkdir(parents=True, exist_ok=True)
                    template.write_text(yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False))
                print(f"Initialized {config.db_path}; artifacts: {config.artifact_dir}")
            elif args.command in {"run", "demo"}:
                if getattr(args, "mode", None):
                    config.mode = args.mode
                if not config.model:
                    raise ValueError("Set OLLAMA_MODEL to an installed Ollama model, or configure model in YAML. No fake inference is used.")
                if getattr(args,'background',False):
                    from slothlab.runtime.jobs import JobManager
                    print(json.dumps(JobManager(os.getenv('SLOTHLAB_JOB_DIR','artifacts/jobs')).launch(config),indent=2))
                    return 0
                session = ResearchAgent(repo, client_from_config(config), config).create()
                print(session.model_dump_json(indent=2))
                print(generate_report(repo, session.id, config.artifact_dir))
            elif args.command == "resume":
                saved = repo.events(args.session_id, "configuration")
                if not saved:
                    raise ValueError("Session has no saved configuration")
                resumed = Config.model_validate(saved[0]["payload"])
                resumed.db_path = str(Path(config.db_path).resolve())
                resumed.storage_backend=config.storage_backend
                if not resumed.model:
                    raise ValueError("This session is a fixed replay, not an autonomous model session")
                if args.background:
                    from slothlab.runtime.jobs import JobManager
                    print(json.dumps(JobManager(os.getenv('SLOTHLAB_JOB_DIR','artifacts/jobs')).resume(resumed,args.session_id),indent=2))
                    return 0
                session = ResearchAgent(repo, client_from_config(resumed), resumed).run(args.session_id)
                print(session.model_dump_json(indent=2))
                print(generate_report(repo, session.id, resumed.artifact_dir))
            elif args.command == "status":
                session = repo.get_session(args.session_id)
                print(json.dumps({"session": session.model_dump(mode="json"), "hypotheses": [h.model_dump(mode="json") for h in repo.hypotheses(session.id)], "decisions": [d.model_dump(mode="json") for d in repo.decisions(session.id)[-5:]]}, indent=2))
            elif args.command == "report":
                saved=repo.events(args.session_id,'configuration')
                artifact_dir=saved[0]['payload'].get('artifact_dir',config.artifact_dir) if saved else config.artifact_dir
                print(generate_report(repo, args.session_id, artifact_dir))
            elif args.command == "experiment":
                from slothlab.schemas import ResearchSession, Hypothesis, ExperimentSpec
                from slothlab.experiments.executor import execute
                repo.save_objective(config.objective)
                s = ResearchSession(objective_id=config.objective.id, model_name="none: direct scientific execution")
                repo.save_session(s)
                h = Hypothesis(session_id=s.id, statement="Oracle correction improves Brier under prevalence shift", falsifiable_prediction="delta_brier < 0; one trial is exploratory")
                repo.save_hypothesis(h)
                spec = ExperimentSpec(hypothesis_id=h.id, seed=args.seed, rationale="Explicit CLI scientific experiment", parameters={"train_prevalence": args.train_prevalence, "evaluation_prevalence": args.evaluation_prevalence})
                repo.save_spec(s.id, spec)
                result = execute(spec, Path(config.artifact_dir)/s.id/"experiments",isolation=config.execution_isolation)
                repo.save_result(s.id, result)
                s.budget_consumed["experiments"] = 1
                s.budget_consumed["wall_seconds"] = result.runtime_seconds
                s.state = "COMPLETED" if result.status == "COMPLETED" else "FAILED"
                s.termination_reason = "Direct exploratory experiment; no autonomous inference"
                repo.save_session(s)
                print(result.model_dump_json(indent=2))
                print(generate_report(repo, s.id, config.artifact_dir))
                if result.status == "FAILED":
                    return 1
        return 0
    except (ValueError, KeyError, OSError, RuntimeError, ModelError, sqlite3.Error) as exc:
        print(f"slothlab: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
