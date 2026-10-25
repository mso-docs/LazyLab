"""Durability and process-ownership tests; no real inference required."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
import pytest
from slothlab.config import Config
from slothlab.runtime.atomic import atomic_json
from slothlab.runtime.jobs import JobManager
from slothlab.runtime.locking import AlreadyRunningError, session_lock
from slothlab.memory.repository import Repository
from slothlab.schemas import ResearchObjective, ResearchSession


def test_session_lock_rejects_second_process_and_releases_on_exit(tmp_path):
    db=tmp_path/'memory.sqlite'
    code="from slothlab.runtime.locking import session_lock; import sys;\nwith session_lock(sys.argv[1],'s'): pass"
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    with session_lock(db,'s'):
        child=subprocess.run([sys.executable,'-c',code,str(db)],capture_output=True,text=True,env=env)
        assert child.returncode != 0 and 'already running' in child.stderr
    child=subprocess.run([sys.executable,'-c',code,str(db)],capture_output=True,text=True,env=env)
    assert child.returncode == 0


def test_atomic_json_never_leaves_partial_snapshot(tmp_path):
    path=tmp_path/'snapshot.json'
    atomic_json(path,{'a':1})
    with pytest.raises(ValueError):
        atomic_json(path,{'a':float('nan')})
    assert json.loads(path.read_text()) == {'a':1}
    assert not list(tmp_path.glob('.snapshot.json.*'))


def test_job_stale_pid_reconciles_without_signaling_reused_process(tmp_path):
    manager=JobManager(tmp_path)
    identity='a'*32
    path=manager._path(identity)
    atomic_json(path,{'id':identity,'state':'running','pid':os.getpid(),'process_started':0,'created_epoch':0,'created_at':'','stop_requested':False})
    with patch('slothlab.runtime.jobs.os.kill') as kill:
        result=manager.stop(identity)
    assert result['state']=='failed'
    kill.assert_not_called()


def test_job_identifier_is_not_a_path(tmp_path):
    with pytest.raises(ValueError):
        JobManager(tmp_path).get('../../secret')


def test_background_failure_is_durable_after_manager_restart(tmp_path):
    config=Config(model='not-an-installed-model',base_url='http://127.0.0.1:1',db_path=str(tmp_path/'memory.sqlite'),artifact_dir=str(tmp_path/'artifacts'),inference_timeout_seconds=1)
    manager=JobManager(tmp_path/'jobs')
    job=manager.launch(config)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        job=JobManager(tmp_path/'jobs').get(job['id'])
        if job['state'] not in {'queued','running','stopping'}:
            break
        time.sleep(.05)
    assert job['state']=='failed'
    assert job['error']
    assert Path(job['config_path']).is_file()
    assert Path(job['log_path']).is_file()
    assert job['session_id']
    with Repository(config.db_path) as repo:
        session=repo.get_session(job['session_id'])
        assert session.state=='FAILED'
        assert session.budget_consumed['tokens'] is None


def test_repeated_resume_for_terminal_session_is_rejected(tmp_path):
    config=Config(model='local',db_path=str(tmp_path/'memory.sqlite'))
    with Repository(config.db_path) as repo:
        repo.save_objective(config.objective)
        session=ResearchSession(objective_id=config.objective.id,model_name='local',state='STOPPED')
        repo.save_session(session)
    with pytest.raises(ValueError,match='terminal'):
        JobManager(tmp_path/'jobs').resume(config,session.id)
