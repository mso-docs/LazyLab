"""Durable, bounded local processes; scientific state remains in SQLite."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import psutil
from slothlab.config import Config
from slothlab.runtime.atomic import atomic_json
from slothlab.runtime.locking import file_lock, AlreadyRunningError
from slothlab.schemas import uid, now

ACTIVE = {'queued', 'running', 'stopping'}
_CHILDREN = {}


class JobManager:
    def __init__(self, root_dir=Path('artifacts/jobs'), max_active=1):
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if not 1 <= max_active <= 4:
            raise ValueError('max_active must be between one and four')
        self.max_active = max_active

    def _path(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Invalid job identifier')
        return self.root/job_id/'job.json'

    def _read(self, job_id):
        return json.loads(self._path(job_id).read_text())

    def update(self, job_id, **changes):
        path = self._path(job_id)
        with file_lock(path.with_suffix('.lock'), blocking=True):
            data = json.loads(path.read_text())
            data.update(changes, updated_at=now())
            atomic_json(path, data)
        return data

    @staticmethod
    def _alive(data):
        if not data.get('pid') or data.get('process_started') is None:
            return False
        try:
            process = psutil.Process(data['pid'])
            return abs(process.create_time()-data['process_started']) < .01 and process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def get(self, job_id):
        child = _CHILDREN.get(job_id)
        if child and child.poll() is not None:
            _CHILDREN.pop(job_id, None)
        path=self._path(job_id)
        # Re-read, test and commit under one lock. A stale observer must never
        # overwrite a completion receipt committed by the worker in the meantime.
        with file_lock(path.with_suffix('.lock'),blocking=True):
            data=json.loads(path.read_text())
            if data['state'] in ACTIVE and not self._alive(data):
                if not data.get('pid') and time.time()-data.get('created_epoch',0) < 5:
                    return data
                state='stopped' if data.get('stop_requested') else 'failed'
                data.update(state=state,error=None if state=='stopped' else 'Worker exited before recording completion; persisted session can be inspected and resumed',finished_at=now(),updated_at=now())
                atomic_json(path,data)
        return data

    def list_jobs(self):
        jobs = []
        for path in self.root.glob('*/job.json'):
            try:
                jobs.append(self.get(path.parent.name))
            except (OSError, ValueError, KeyError):
                continue
        return sorted(jobs, key=lambda data:data.get('created_at',''), reverse=True)

    def launch(self, config: Config):
        return self._launch(config, None)

    def launch_benchmark(self, config: Config, suite='benchmarks/objectives', repeats=1, use_replay=False, reference_path=None):
        from slothlab.assets import asset_path
        if type(repeats) is not int or not 1 <= repeats <= 20:
            raise ValueError('Benchmark repeats must be between one and twenty')
        suite=asset_path(suite).resolve()
        if not suite.is_dir() or not list(suite.glob('*.yaml')):
            raise ValueError('Select a benchmark suite containing YAML objectives')
        return self._launch(config,None, task={'kind':'benchmark','suite':str(suite),'repeats':repeats,'use_replay':use_replay,'reference_path':str(Path(reference_path).resolve()) if reference_path else None})

    def resume(self, config: Config, session_id: str):
        from slothlab.memory.factory import open_repository
        with open_repository(config.db_path,config.storage_backend) as repo:
            session = repo.get_session(session_id)
            if session.state in {'COMPLETED','STOPPED','FAILED'}:
                raise ValueError('This investigation is terminal; start a new investigation to continue research')
            saved = repo.events(session_id, 'configuration')
            if saved:
                data = saved[0]['payload'] | {'db_path':str(Path(config.db_path).resolve()), 'artifact_dir':str(Path(config.artifact_dir).resolve()),'storage_backend':config.storage_backend}
                config = Config.model_validate(data)
        return self._launch(config, session_id)

    def _launch(self, config, session_id, task=None):
        task=task or {'kind':'research'}
        if not config.model and not task.get('use_replay'):
            raise ValueError('Select an installed Ollama model before starting research')
        # Round-trip before any process creation; mutated unchecked configurations
        # must not bypass the same validation applied to the CLI.
        config = Config.model_validate(config.model_dump(mode='json'))
        if config.db_path==':memory:':
            raise ValueError('Background investigations require a persistent SQLite database')
        config.db_path = str(Path(config.db_path).resolve())
        config.artifact_dir = str(Path(config.artifact_dir).resolve())
        with file_lock(self.root/'.manager.lock', blocking=True):
            active = [j for j in self.list_jobs() if j['state'] in ACTIVE]
            if any(session_id and j.get('session_id')==session_id and j['db_path']==config.db_path for j in active):
                raise AlreadyRunningError('This session already has an active research job')
            if len(active) >= self.max_active:
                raise AlreadyRunningError('The local research worker is busy. Pause the active job or wait for completion')
            identity = uid()
            directory = self.root/identity
            directory.mkdir()
            config_path = directory/'config.json'
            atomic_json(config_path, config.model_dump(mode='json'))
            data = {'id':identity, 'session_id':session_id, 'state':'queued', 'pid':None,
                    'process_started':None, 'created_at':now(), 'created_epoch':time.time(),
                    'updated_at':now(), 'finished_at':None, 'db_path':config.db_path,
                    'artifact_dir':config.artifact_dir, 'storage_backend':config.storage_backend, 'config_path':str(config_path),
                    'log_path':str(directory/'worker.log'), 'report_path':None,
                    'error':None, 'return_code':None, 'stop_requested':False}
            data.update(task)
            if task['kind']=='benchmark':
                data['output_dir']=str(Path(config.artifact_dir)/'benchmarks'/identity)
                data['comparison_path']=None
            atomic_json(directory/'job.json',data)
            env = {k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL','SYSTEMROOT','SLOTHLAB_LOG_LEVEL'}}
            env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2])
            env['PYTHONUNBUFFERED'] = '1'
            try:
                with (directory/'worker.log').open('ab') as log:
                    child = subprocess.Popen([sys.executable,'-m','slothlab.runtime.job_worker','--root',str(self.root),'--job',identity], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
                _CHILDREN[identity] = child
                try:
                    created = psutil.Process(child.pid).create_time()
                except psutil.NoSuchProcess:
                    created = None
                return self.update(identity, pid=child.pid, process_started=created)
            except OSError as exc:
                self.update(identity,state='failed',error=str(exc),finished_at=now())
                raise

    def stop(self, job_id):
        self.get(job_id)  # Reconcile already-dead workers before admitting a stop.
        # Publication of a newly created PID and stop admission cannot interleave.
        with file_lock(self.root/'.manager.lock',blocking=True):
            path=self._path(job_id)
            with file_lock(path.with_suffix('.lock'),blocking=True):
                data=json.loads(path.read_text())
                if data['state'] not in ACTIVE:
                    return data
                data.update(state='stopping',stop_requested=True,updated_at=now())
                atomic_json(path,data)
                try:
                    process=psutil.Process(data['pid']) if data.get('pid') else None
                    if process and data.get('process_started') is not None and abs(process.create_time()-data['process_started']) < .01:
                        # psutil terminate additionally detects PID reuse between
                        # this birth-time check and delivery of the signal.
                        process.terminate()
                except (psutil.NoSuchProcess,psutil.AccessDenied):
                    pass
        return self.get(job_id)

    def logs(self, job_id, max_bytes=65536):
        data = self.get(job_id)
        path = Path(data['log_path'])
        if not path.is_file():
            return ''
        with path.open('rb') as handle:
            handle.seek(max(0,path.stat().st_size-max_bytes))
            return handle.read().decode('utf-8',errors='replace')
