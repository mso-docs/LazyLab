import json
from pathlib import Path
from unittest.mock import patch
import pytest
from slothlab.config import load_config
from slothlab.evaluation.benchmark import replay
from slothlab.schemas import ExperimentResult
from slothlab.lazyloop.fingerprint import fingerprint
from slothlab.memory.repository import Repository
from slothlab.reporting.generator import report_data

FIXTURES=Path(__file__).resolve().parents[1]/'benchmarks/behavioral'
NAMES={'exact_duplicate','valid_replication','contradictory_evidence','invalid_parameters','repeated_planning','resource_constraints','evidence_sufficiency','premature_stop_risk'}


def fixture_execution(spec,artifact_dir,**kwargs):
    delta=0.0 if spec.parameters.train_prevalence==spec.parameters.evaluation_prevalence else (.01 if spec.seed==0 else -.01)
    return ExperimentResult(experiment_id=spec.id,fingerprint=fingerprint(spec),status='COMPLETED',runtime_seconds=.01,
        metrics={'baseline_brier':.2,'corrected_brier':.2+delta,'delta_brier':delta,'baseline_log_loss':.5,'corrected_log_loss':.5+delta,'delta_log_loss':delta})


def test_behavioral_manifest_covers_all_eight_specification_cases():
    manifest=json.loads((FIXTURES/'manifest.json').read_text())
    assert manifest['fixture_count']==8
    assert {row['id'] for row in manifest['fixtures']}==NAMES
    for row in manifest['fixtures']:
        assert (FIXTURES/row['configuration']).is_file()
        assert (FIXTURES/row['protocol']).is_file()


@pytest.mark.parametrize('name',sorted(NAMES))
def test_behavioral_protocols_are_bounded_safe_and_honest(name,tmp_path):
    config=load_config(FIXTURES/f'{name}.yaml')
    config.mode='lazyloop';config.artifact_dir=str(tmp_path)
    protocol=json.loads((FIXTURES/f'{name}.replay.json').read_text())
    with Repository(tmp_path/'memory.sqlite') as repo,patch('slothlab.evaluation.benchmark.execute',side_effect=fixture_execution) as execute:
        session=replay(repo,config,protocol['schedule'])
        data=report_data(repo,session.id)
        expected=protocol['expected_behavior']
        count=expected.get('all_mode_executions',expected.get('optimized_executions'))
        assert execute.call_count==count
        assert session.budget_consumed['experiments']==count
        assert session.state==expected.get('terminal_state','STOPPED')
        assert data['telemetry']['premature_stops']==0
        assert data['telemetry']['failed_execution_attempts']==0
        assert session.budget_consumed['model_calls']==0
        if name=='invalid_parameters':
            assert data['telemetry']['rejected_proposals']==3
            assert all(call.args[0].parameters.sample_size==1000 for call in execute.call_args_list)
        if name=='resource_constraints':
            assert [call.args[0].seed for call in execute.call_args_list]==[1]
            assert any(d.decision=='DEFER' for d in repo.decisions(session.id))
        if name in {'evidence_sufficiency','premature_stop_risk'}:
            confirmed=[s for s in repo.specs(session.id) if s.phase=='confirmatory']
            assert len(confirmed)==expected['confirmations']
            assert data['telemetry']['supported_findings']==1
        if name=='premature_stop_risk':
            assert repo.events(session.id,'soft_stop_deferred')
            assert any('every predeclared confirmation' in e['payload']['reason'] for e in repo.events(session.id,'strategy_revision'))
