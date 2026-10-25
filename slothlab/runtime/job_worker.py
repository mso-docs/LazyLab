"""Private worker entrypoint; survives browser refresh and checkpoints SIGTERM."""
import argparse
import json
import logging
import signal
from pathlib import Path
from slothlab.config import Config
from slothlab.runtime.jobs import JobManager
from slothlab.schemas import now


class RuntimeInterrupted(BaseException):
    pass


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--job',required=True)
    args=parser.parse_args()
    manager=JobManager(args.root)
    job=manager._read(args.job)
    config=Config.model_validate(json.loads(Path(job['config_path']).read_text()))
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    def interrupt(signum, frame):
        raise RuntimeInterrupted()
    signal.signal(signal.SIGTERM,interrupt)
    signal.signal(signal.SIGINT,interrupt)
    from slothlab.memory.factory import open_repository
    from slothlab.models import client_from_config
    from slothlab.agent.orchestrator import ResearchAgent
    from slothlab.reporting.generator import generate_report
    session_id=job.get('session_id')
    try:
        if manager._read(args.job).get('stop_requested'):
            raise RuntimeInterrupted()
        if job.get('kind')=='benchmark':
            from slothlab.evaluation.benchmark import run_benchmark
            manager.update(args.job,state='running')
            fields=('model','base_url','inference_timeout_seconds','inference_context_tokens','inference_threads','inference_thinking','execution_isolation','storage_backend')
            overrides={name:getattr(config,name) for name in fields}
            path=run_benchmark(job['suite'],job['output_dir'],job['use_replay'],job['repeats'],reference_path=job.get('reference_path'),config_overrides=overrides)
            summary=json.loads(path.read_text())
            failed=summary.get('failed_runs',0)
            manager.update(args.job,state='failed' if failed else 'completed',comparison_path=str(path),report_path=str(path.with_suffix('.md')),return_code=1 if failed else 0,finished_at=now(),error=f'{failed} benchmark arms failed; inspect the comparison report' if failed else None)
            return 1 if failed else 0
        with open_repository(config.db_path,config.storage_backend) as repo:
            agent=ResearchAgent(repo,client_from_config(config),config)
            if session_id is None:
                session=agent.initialize()
                session_id=session.id
            manager.update(args.job,state='running',session_id=session_id)
            session=agent.run(session_id)
            report=generate_report(repo,session_id,config.artifact_dir)
            state='failed' if session.state=='FAILED' else 'completed'
            manager.update(args.job,state=state,report_path=str(report),return_code=1 if state=='failed' else 0,finished_at=now(),error=session.termination_reason if state=='failed' else None)
            return 1 if state=='failed' else 0
    except RuntimeInterrupted:
        if session_id:
            with open_repository(config.db_path,config.storage_backend) as repo:
                session=repo.get_session(session_id)
                if session.state not in {'COMPLETED','STOPPED','FAILED'}:
                    session.state='REPLANNING'
                    session.termination_reason='Paused by user; resumable'
                    repo.save_session(session)
                    repo.event(session_id,'user_pause',{'job_id':args.job})
        manager.update(args.job,state='stopped',session_id=session_id,return_code=0,finished_at=now())
        return 0
    except BaseException as exc:
        logging.exception('Investigation failed')
        manager.update(args.job,state='failed',session_id=session_id,error=str(exc),return_code=1,finished_at=now())
        return 1


if __name__=='__main__':
    raise SystemExit(main())
