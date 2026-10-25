"""Real process lifecycle against an explicitly scripted test-only HTTP model."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading
import time
import pytest
from slothlab.config import Config
from slothlab.schemas import Budget,ResearchObjective,Parameters
from slothlab.runtime.jobs import JobManager
from slothlab.memory.repository import Repository
from slothlab.memory.factory import open_repository


@pytest.fixture
def scripted_server():
    request_started=threading.Event(); release=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            prompt=body['messages'][0]['content']
            context=json.JSONDecoder().raw_decode(prompt.split('Context: ',1)[1])[0]
            if 'Generate two competing' in prompt:
                if not request_started.is_set():
                    request_started.set(); release.wait(10)
                payload={'hypotheses':[{'statement':'Correction helps under shift','falsifiable_prediction':'delta_brier < 0','expected_delta_direction':'negative','assumptions':['Oracle prevalence']},{'statement':'Correction can worsen finite samples','falsifiable_prediction':'delta_brier > 0','expected_delta_direction':'positive','assumptions':['Finite samples']}]}
            elif 'Interpret recorded' in prompt:
                payload={'assessments':[{'hypothesis_id':context['hypotheses'][0]['id'],'status':'INCONCLUSIVE','evidence_ids':[r['id'] for r in context['evidence']],'explanation':'One trial cannot confirm the prediction'}],'next_direction':'Replicate independently'}
            else:
                payload={'candidates':[{'hypothesis_id':context['hypotheses'][0]['id'],'parameters':Parameters(sample_size=100).model_dump(),'seed':0,'phase':'exploratory','rationale':'Test-only scripted proposal'}]}
            response=json.dumps({'done':True,'message':{'content':json.dumps(payload)},'prompt_eval_count':20,'eval_count':20}).encode()
            try:
                self.send_response(200);self.send_header('Content-Length',str(len(response)));self.end_headers();self.wfile.write(response)
            except (BrokenPipeError,ConnectionResetError): pass
    try:
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    except PermissionError:
        pytest.skip('Local socket permission required for subprocess lifecycle test')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}',request_started,release
    release.set();server.shutdown();server.server_close()


def wait_for(manager,identity,states,seconds=20):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        job=manager.get(identity)
        if job['state'] in states:
            return job
        time.sleep(.05)
    raise AssertionError(f'Timed out waiting for {states}; last state: {job}')


@pytest.mark.parametrize('storage_backend',['sqlite','document'])
def test_background_pause_during_inference_and_resume_survives_manager_restart(tmp_path,scripted_server,storage_backend):
    endpoint,started,release=scripted_server
    config=Config(model='explicit-test-http-fixture',base_url=endpoint,storage_backend=storage_backend,db_path=str(tmp_path/('memory.json' if storage_backend=='document' else 'memory.sqlite')),artifact_dir=str(tmp_path/'artifacts'),budget=Budget(max_experiments=1,max_rounds=2,max_tokens=50000,wall_seconds=60),execution_isolation='subprocess')
    manager=JobManager(tmp_path/'jobs')
    first=manager.launch(config)
    try:
        assert started.wait(15),'Worker never contacted the test-only model'
        manager.stop(first['id'])
        paused=wait_for(manager,first['id'],{'stopped'})
        assert paused['session_id']
        with open_repository(config.db_path,storage_backend) as repo:
            session=repo.get_session(paused['session_id'])
            assert session.state=='REPLANNING'
            assert session.budget_consumed['tokens'] is None
            assert repo.events(session.id,'user_pause')
        release.set()
        second=JobManager(tmp_path/'jobs').resume(config,paused['session_id'])
        finished=wait_for(manager,second['id'],{'completed','failed'})
        assert finished['state']=='completed',manager.logs(second['id'])
        assert finished['report_path']
        with open_repository(config.db_path,storage_backend) as repo:
            session=repo.get_session(paused['session_id'])
            assert session.budget_consumed['experiments']==1
            assert len(repo.results(session.id))==1
            assert session.budget_consumed['tokens'] is None
    finally:
        release.set()
        for job in manager.list_jobs():
            if job['state'] in {'queued','running','stopping'}:
                manager.stop(job['id'])


def test_background_replay_benchmark_finishes_and_keeps_comparison(tmp_path):
    suite=tmp_path/'suite';suite.mkdir()
    (suite/'small.yaml').write_text('budget:\n  max_experiments: 2\n  wall_seconds: 60\nobjective:\n  permitted_parameters:\n    sample_size: [100]\n')
    config=Config(db_path=str(tmp_path/'unused.sqlite'),artifact_dir=str(tmp_path/'artifacts'),execution_isolation='subprocess')
    manager=JobManager(tmp_path/'jobs')
    job=manager.launch_benchmark(config,suite,repeats=1,use_replay=True)
    finished=wait_for(manager,job['id'],{'completed','failed'},seconds=40)
    assert finished['state']=='completed',manager.logs(job['id'])
    comparison=json.loads(__import__('pathlib').Path(finished['comparison_path']).read_text())
    assert comparison['complete'] is True
    assert comparison['failed_runs']==0
    assert len(comparison['runs'])==3
