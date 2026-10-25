"""Regression coverage from an independent durability and identity audit."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from slothlab.runtime.locking import file_lock
import pytest
from slothlab.cli import main as cli_main
from slothlab.config import Config
from slothlab.memory.repository import Repository
from slothlab.runtime.atomic import atomic_json
from slothlab.runtime.jobs import JobManager
from slothlab.schemas import ResearchObjective, ResearchSession


def job_fixture(manager,state='running',**changes):
    identity='c'*32
    data={'id':identity,'state':state,'pid':2147483647,'process_started':1.0,
          'created_epoch':time.time()-30,'created_at':'2026-10-25T00:00:00Z',
          'stop_requested':False,'session_id':None,'error':None,'return_code':None}
    data.update(changes)
    atomic_json(manager._path(identity),data)
    return identity,data


def test_stale_liveness_read_cannot_overwrite_worker_completion(tmp_path):
    manager=JobManager(tmp_path)
    identity,previous=job_fixture(manager)
    probed=Event()
    def exited(data):
        probed.set()
        return False
    with patch.object(manager,'_alive',side_effect=exited),ThreadPoolExecutor(max_workers=1) as pool:
        # Mimic the worker holding the receipt lock while committing completion.
        # The old reader ignored this lock, observed the old running state, then
        # overwrote completion when its delayed update acquired the lock.
        with file_lock(manager._path(identity).with_suffix('.lock'),blocking=True):
            observed=pool.submit(manager.get,identity)
            probed.wait(.1)
            atomic_json(manager._path(identity),previous|{'state':'completed','return_code':0,'finished_at':'done'})
        result=observed.result(timeout=3)
    assert result['state']=='completed'
    assert manager._read(identity)['return_code']==0


def test_stop_cannot_overwrite_or_signal_a_just_completed_job(tmp_path):
    manager=JobManager(tmp_path)
    identity,previous=job_fixture(manager)
    reads=0
    def worker_finished_after_read(job_id):
        nonlocal reads
        reads+=1
        if reads==1:
            manager.update(identity,state='completed',return_code=0)
            return previous
        return manager._read(identity)
    with patch.object(manager,'get',side_effect=worker_finished_after_read),patch.object(manager,'_alive',return_value=True),patch('slothlab.runtime.jobs.os.kill') as kill:
        result=manager.stop(identity)
    assert result['state']=='completed'
    assert not result.get('stop_requested')
    kill.assert_not_called()


def test_worker_honors_pause_requested_before_pid_publication(tmp_path,monkeypatch):
    from slothlab.runtime.job_worker import main
    manager=JobManager(tmp_path/'jobs')
    config=Config(model='scripted-test',db_path=str(tmp_path/'memory.sqlite'),artifact_dir=str(tmp_path/'artifacts'))
    config_path=tmp_path/'config.json';atomic_json(config_path,config.model_dump(mode='json'))
    identity,_=job_fixture(manager,state='stopping',pid=None,process_started=None,
        config_path=str(config_path),stop_requested=True,kind='research',db_path=config.db_path,artifact_dir=config.artifact_dir)
    client=Mock(name='model_client');client.name='scripted-test'
    client.generate.side_effect=AssertionError('Paused jobs must not perform inference')
    monkeypatch.setattr(sys,'argv',['job_worker','--root',str(manager.root),'--job',identity])
    with patch('slothlab.models.client_from_config',return_value=client),patch('slothlab.runtime.job_worker.signal.signal'):
        code=main()
    assert code==0
    assert manager._read(identity)['state']=='stopped'
    client.generate.assert_not_called()


def test_hard_worker_exit_keeps_unknown_usage_and_session_resumable(tmp_path):
    db=tmp_path/'memory.sqlite'
    code='''import os,sys
from slothlab.memory.repository import Repository
from slothlab.schemas import ResearchObjective,ResearchSession
with Repository(sys.argv[1]) as repo:
 objective=ResearchObjective(id='objective');repo.save_objective(objective)
 session=ResearchSession(id='session',objective_id=objective.id,model_name='test',state='PLANNING')
 session.budget_consumed['tokens']=None
 session.budget_consumed['token_reservations']=900
 session.budget_consumed['model_calls']=1
 repo.save_session(session)
 os._exit(137)
'''
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    child=subprocess.Popen([sys.executable,'-c',code,str(db)],env=env)
    assert child.wait(timeout=15)==137
    manager=JobManager(tmp_path/'jobs')
    identity,_=job_fixture(manager,pid=child.pid,process_started=0,session_id='session',db_path=str(db))
    assert manager.get(identity)['state']=='failed'
    with Repository(db) as repo:
        saved=repo.get_session('session')
        assert saved.state=='PLANNING'
        assert saved.budget_consumed['tokens'] is None
        assert saved.budget_consumed['token_reservations']==900


def test_objective_identity_preserves_historical_question(tmp_path):
    with Repository(tmp_path/'memory.sqlite') as repo:
        objective=ResearchObjective(question='Original declared question')
        repo.save_objective(objective)
        session=ResearchSession(objective_id=objective.id,model_name='test')
        repo.save_session(session)
        altered=objective.model_copy(update={'question':'A different question after seeing results'})
        with pytest.raises(ValueError,match='immutable'):
            repo.save_objective(altered)
        assert repo.get_objective(session.objective_id).question=='Original declared question'


def test_session_cannot_change_objective_ownership_after_creation(tmp_path):
    with Repository(tmp_path/'memory.sqlite') as repo:
        first,second=ResearchObjective(),ResearchObjective()
        repo.save_objective(first);repo.save_objective(second)
        session=ResearchSession(objective_id=first.id,model_name='test')
        repo.save_session(session)
        session.objective_id=second.id
        with pytest.raises(ValueError,match='immutable'):
            repo.save_session(session)
        assert repo.get_session(session.id).objective_id==first.id


def saved_session(path,artifact_dir,state='REPLANNING',saved_db=None):
    config=Config(model='scripted-test',db_path=str(saved_db or path),artifact_dir=str(artifact_dir))
    with Repository(path) as repo:
        repo.save_objective(config.objective)
        session=ResearchSession(objective_id=config.objective.id,model_name='scripted-test',state=state)
        repo.save_session(session)
        repo.event(session.id,'configuration',config.model_dump(mode='json'))
    return session


def test_cli_background_resume_uses_selected_database_after_relocation(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    selected=tmp_path/'relocated.sqlite'
    session=saved_session(selected,tmp_path/'original-artifacts',saved_db=tmp_path/'old-location.sqlite')
    with patch('slothlab.runtime.jobs.JobManager.resume',return_value={'id':'d'*32}) as resume:
        assert cli_main(['--db',str(selected),'resume',session.id,'--background'])==0
    assert Path(resume.call_args.args[0].db_path).resolve()==selected.resolve()


def test_report_uses_saved_session_artifact_root(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('SLOTHLAB_ARTIFACT_DIR',raising=False)
    path=tmp_path/'memory.sqlite'
    artifacts=tmp_path/'original-artifacts'
    session=saved_session(path,artifacts,state='STOPPED')
    assert cli_main(['--db',str(path),'report',session.id])==0
    report=artifacts/session.id/'reports'/'report.md'
    assert report.is_file()
    assert str(report.resolve()) in capsys.readouterr().out


def test_persisted_hard_budget_cannot_be_expanded_in_place(tmp_path):
    with Repository(tmp_path/'memory.sqlite') as repo:
        objective=ResearchObjective();repo.save_objective(objective)
        session=ResearchSession(objective_id=objective.id,model_name='test')
        repo.save_session(session)
        authorized=session.budget_configuration.max_experiments
        session.budget_configuration.max_experiments=authorized+1
        with pytest.raises(ValueError,match='immutable'):
            repo.save_session(session)
        assert repo.get_session(session.id).budget_configuration.max_experiments==authorized
