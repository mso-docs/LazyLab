"""Behavior-level tests for the real Streamlit workspace, without fake app findings."""
import io
import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pytest
pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest
from slothlab.config import Config
from slothlab.memory.repository import Repository
from slothlab.schemas import ResearchObjective, ResearchSession

DASHBOARD = Path(__file__).resolve().parents[1]/'slothlab'/'ui'/'dashboard.py'


class Jobs:
    def __init__(self):
        self.launched=[]
        self.resumed=[]
        self.stopped=[]
        self.benchmarks=[]
        self.jobs=[]
    def list_jobs(self):
        return self.jobs
    def launch(self,config):
        self.launched.append(config)
        return {'id':'a'*32,'session_id':None,'state':'queued'}
    def resume(self,config,session_id):
        self.resumed.append((config,session_id))
        return {'id':'b'*32,'session_id':session_id,'state':'queued'}
    def launch_benchmark(self,config,**kwargs):
        self.benchmarks.append((config,kwargs))
        return {'id':'c'*32,'state':'queued','kind':'benchmark'}
    def stop(self,job_id):
        self.stopped.append(job_id)
        self.jobs=[]
        return {'id':job_id,'state':'stopped'}


@pytest.fixture
def ui_env(tmp_path,monkeypatch):
    monkeypatch.setenv('SLOTHLAB_DB_PATH',str(tmp_path/'memory.sqlite'))
    monkeypatch.setenv('SLOTHLAB_ARTIFACT_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setenv('SLOTHLAB_JOB_DIR',str(tmp_path/'jobs'))
    monkeypatch.delenv('OLLAMA_MODEL',raising=False)
    jobs=Jobs()
    with patch('slothlab.runtime.jobs.JobManager',return_value=jobs):
        yield tmp_path,jobs


def run_app():
    return AppTest.from_file(str(DASHBOARD),default_timeout=15).run()


def button(app,label):
    return next(item for item in app.button if item.label==label)


def text(app,label):
    return next(item for item in app.text_input if item.label==label)


def number(app,label):
    return next(item for item in app.number_input if item.label==label)


def saved_session(path,state='INITIALIZED'):
    with Repository(path) as repo:
        objective=ResearchObjective(title='Dashboard test objective')
        repo.save_objective(objective)
        session=ResearchSession(objective_id=objective.id,model_name='test-no-inference',state=state)
        session.budget_consumed['tokens']=None
        repo.save_session(session)
        repo.event(session.id,'configuration',Config(objective=objective,model='installed-model',db_path=str(path)).model_dump(mode='json'))
    return objective,session


def test_dashboard_empty_workspace_can_start_without_preexisting_memory(ui_env):
    tmp_path,jobs=ui_env
    app=run_app()
    assert not app.exception
    assert any('No research memory found' in item.value for item in app.info)
    assert not (tmp_path/'memory.sqlite').exists()
    assert [tab.label for tab in app.tabs][:4]==['Research','New investigation','Comparisons','Learn & help']
    assert not button(app,'Start investigation').disabled
    assert jobs.launched==[]


def test_dashboard_renders_persisted_session_and_unknown_telemetry(ui_env):
    tmp_path,jobs=ui_env
    objective,session=saved_session(tmp_path/'memory.sqlite')
    app=run_app()
    assert not app.exception
    metrics={item.label:item.value for item in app.metric}
    assert {key:metrics[key] for key in ['State','Executed','Cache hits','Model tokens']}=={'State':'INITIALIZED','Executed':'0','Cache hits':'0','Model tokens':'Unknown'}
    assert any(item.value==objective.title for item in app.subheader)
    assert app.selectbox(key='selected_session').value==session.id
    assert not button(app,'Resume investigation').disabled
    assert jobs.launched==[]


def test_launch_validates_model_before_background_start(ui_env):
    _,jobs=ui_env
    app=run_app()
    button(app,'Start investigation').click().run()
    assert not app.exception
    assert any('installed Ollama model' in item.value for item in app.error)
    assert jobs.launched==[]


def test_launch_passes_validated_objective_parameters_and_budget(ui_env):
    tmp_path,jobs=ui_env
    app=run_app()
    text(app,'Ollama model').set_value('my-local-model')
    number(app,'Maximum experiments').set_value(7)
    button(app,'Start investigation').click().run()
    assert not app.exception
    assert len(jobs.launched)==1
    config=jobs.launched[0]
    assert config.model=='my-local-model'
    assert config.budget.max_experiments==7
    assert config.objective.permitted_parameters['sample_size']==[500,1000,2000]
    assert config.db_path==str(tmp_path/'memory.sqlite')
    assert any('started in the background' in item.value for item in app.success)


def test_launch_rejects_empty_parameter_authorization(ui_env):
    _,jobs=ui_env
    app=run_app()
    text(app,'Ollama model').set_value('my-model')
    next(item for item in app.multiselect if item.label=='Sample sizes per split').set_value([])
    button(app,'Start investigation').click().run()
    assert not app.exception
    assert any('at least one allowed value' in item.value for item in app.error)
    assert not jobs.launched


def test_model_discovery_is_explicit_and_populates_model(ui_env):
    app=run_app()
    with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'models':[{'name':'installed-model'}]}).encode())) as request:
        button(app,'Discover installed models').click().run()
    assert not app.exception
    assert request.call_count==1
    assert text(app,'Ollama model').value=='installed-model'


def test_model_discovery_failure_is_actionable(ui_env):
    app=run_app()
    with patch('urllib.request.urlopen',side_effect=URLError('unavailable')):
        button(app,'Discover installed models').click().run()
    assert not app.exception
    assert any('Start Ollama' in item.value for item in app.error)


def test_resume_uses_saved_configuration_without_inference_in_ui(ui_env):
    tmp_path,jobs=ui_env
    _,session=saved_session(tmp_path/'memory.sqlite',state='REPLANNING')
    app=run_app()
    button(app,'Resume investigation').click().run()
    assert not app.exception
    assert jobs.resumed[0][1]==session.id
    assert jobs.resumed[0][0].model=='installed-model'


def test_stop_background_job_uses_manager(ui_env):
    _,jobs=ui_env
    jobs.jobs=[{'id':'a'*32,'session_id':None,'state':'running'}]
    app=run_app()
    button(app,'Stop run').click().run()
    assert not app.exception
    assert jobs.stopped==['a'*32]


def test_comparison_discovery_and_invalid_json_are_handled(ui_env):
    tmp_path,_=ui_env
    folder=tmp_path/'artifacts'/'benchmarks'/'trial'
    folder.mkdir(parents=True)
    path=folder/'comparison.json'
    path.write_text('not json')
    app=run_app()
    app.selectbox(key='comparison_picker').set_value(str(path)).run()
    assert not app.exception
    assert any('Cannot open comparison' in item.value for item in app.error)


def test_corrupt_database_renders_error_instead_of_crashing(ui_env):
    tmp_path,_=ui_env
    (tmp_path/'memory.sqlite').write_text('not a sqlite database')
    app=run_app()
    assert not app.exception
    assert any('Cannot read research memory' in item.value for item in app.error)


def test_recorded_measurements_chart_export_and_provenance(ui_env):
    from slothlab.schemas import Hypothesis,ExperimentSpec,ExperimentResult
    tmp_path,_=ui_env
    _,session=saved_session(tmp_path/'memory.sqlite',state='STOPPED')
    with Repository(tmp_path/'memory.sqlite') as repo:
        hypothesis=Hypothesis(session_id=session.id,statement='Controlled test hypothesis',falsifiable_prediction='A test-only directional claim')
        repo.save_hypothesis(hypothesis)
        spec=ExperimentSpec(hypothesis_id=hypothesis.id,seed=13,rationale='UI test fixture, not research evidence')
        repo.save_spec(session.id,spec)
        result=ExperimentResult(experiment_id=spec.id,fingerprint='test-fixture-only',status='COMPLETED',runtime_seconds=.1,metrics={'baseline_brier':.2,'corrected_brier':.1,'delta_brier':-.1,'baseline_log_loss':.5,'corrected_log_loss':.3,'delta_log_loss':-.2})
        repo.save_result(session.id,result)
    app=run_app()
    assert not app.exception
    assert len(app.get('vega_lite_chart'))==1
    assert any(item.label=='Download experiment table' for item in app.get('download_button'))
    button(app,'Prepare Markdown report').click().run()
    assert not app.exception
    assert any(item.label=='Download Markdown report' for item in app.get('download_button'))
    report=tmp_path/'artifacts'/session.id/'reports/report.md'
    assert result.id in report.read_text()


def test_measured_comparison_renders_modes_and_charts(ui_env):
    tmp_path,_=ui_env
    folder=tmp_path/'artifacts'/'benchmarks'/'trial'
    folder.mkdir(parents=True)
    path=folder/'comparison.json'
    path.write_text(json.dumps({'evaluation_kind':'test-only controlled comparison','runs':[{'scenario':'controlled fixture','trial':0,'mode':mode,'experiment_count':count,'cache_hits':9-count,'wall_seconds':float(count),'model_tokens':None,'quality':{'quality_score':1.0},'session_id':mode} for mode,count in [('baseline',9),('cache_only',6),('lazyloop',6)]],'limitations':['Test fixture, not measured research.']}))
    app=run_app()
    app.selectbox(key='comparison_picker').set_value(str(path)).run()
    assert not app.exception
    assert len(app.get('vega_lite_chart'))==2
    assert any('test-only controlled comparison' in item.value for item in app.info)


def test_proposal_ledger_preserves_cache_measurement_identity():
    from slothlab.ui.presentation import proposal_frame
    measured={'id':'r','experiment_id':'first','status':'COMPLETED','runtime_seconds':2.0,'metrics':{'delta_brier':-.1,'delta_log_loss':-.2}}
    frame=proposal_frame({'experiments':[{'id':'first','seed':1},{'id':'repeat','seed':1}], 'results':[measured], 'decisions':[{'experiment_id':'first','decision':'EXECUTE','reason':'new'},{'experiment_id':'repeat','decision':'REUSE','reason':'cached','evidence_references':['r']}]})
    assert frame['result_id'].tolist()==['r','r']
    assert frame['action'].tolist()==['EXECUTE','REUSE']
    assert frame.iloc[1]['delta_brier']==-.1
    assert __import__('pandas').isna(frame.iloc[1]['runtime_seconds'])


def test_browser_benchmark_replay_is_explicit_and_starts_durable_job(ui_env):
    _,jobs=ui_env
    app=run_app()
    app.selectbox(key='benchmark_protocol').set_value('Fixed proposal replay')
    button(app,'Start benchmark').click().run()
    assert not app.exception
    config,arguments=jobs.benchmarks[0]
    assert config.model is None
    assert arguments['use_replay'] is True
    assert arguments['repeats']==1
    assert arguments['suite']=='benchmarks/objectives'


def test_browser_autonomous_benchmark_requires_real_model(ui_env):
    _,jobs=ui_env
    app=run_app()
    button(app,'Start benchmark').click().run()
    assert not app.exception
    assert not jobs.benchmarks
    assert any('installed benchmark model' in item.value for item in app.error)


def test_model_prose_does_not_render_remote_images_or_html():
    from slothlab.ui.dashboard import safe_prose
    with patch('streamlit.markdown') as render:
        safe_prose('![image](https://example.invalid/image.png)<script>bad()</script>',strong=True)
    markup=render.call_args.args[0]
    assert '![' not in markup
    assert '<script>' not in markup
    assert '&#91;' in markup
    assert '&lt;script&gt;' in markup


def test_active_worker_prevents_conflicting_browser_launches(ui_env):
    _,jobs=ui_env
    jobs.jobs=[{'id':'a'*32,'state':'running','session_id':None}]
    app=run_app()
    assert not app.exception
    assert button(app,'Start investigation').disabled
    assert button(app,'Start benchmark').disabled
    assert not button(app,'Stop run').disabled


def test_browser_completion_and_execution_policy_are_explicit(ui_env):
    _,jobs=ui_env
    app=run_app()
    text(app,'Ollama model').set_value('local-model')
    next(item for item in app.selectbox if item.label=='Execution isolation').set_value('bubblewrap')
    next(item for item in app.selectbox if item.label=='Model thinking').set_value('Disabled')
    number(app,'Inference CPU threads · 0 for auto').set_value(4)
    button(app,'Start investigation').click().run()
    assert not app.exception
    config=jobs.launched[0]
    assert config.execution_isolation=='bubblewrap'
    assert config.inference_thinking is False
    assert config.inference_threads==4
    assert config.objective.success_criteria['require_confirmation'] is True
    assert config.objective.success_criteria['minimum_exploratory_experiments']==3
    assert config.objective.success_criteria['minimum_conditions']==1


def test_browser_rejects_infeasible_confirmation_batch(ui_env):
    _,jobs=ui_env
    app=run_app()
    text(app,'Ollama model').set_value('local-model')
    number(app,'Candidates per round').set_value(1)
    button(app,'Start investigation').click().run()
    assert not app.exception
    assert not jobs.launched
    assert any('candidates per round' in item.value for item in app.error)
