import json
import pytest
from slothlab.config import Config
from slothlab.schemas import ExperimentResult,ResearchObjective,Budget
from slothlab.evaluation import reference
from slothlab.evaluation.quality import condition_key


def test_reference_seeds_and_conditions_are_independent_and_diverse():
    config=Config(objective=ResearchObjective(permitted_parameters={'sample_size':[100,500,1000],'evaluation_prevalence':[.1,.5,.8]}))
    seeds=reference.reference_seeds(config,3)
    assert not set(seeds)&set(config.exploratory_seeds+config.confirmatory_seeds)
    conditions=reference.reference_conditions(config,4)
    assert len(conditions)==4
    assert len({condition_key(p) for p in conditions})==4


def test_reference_generation_is_cold_real_runner_contract_and_final_only(tmp_path,monkeypatch):
    calls=[]
    def execute(spec,artifact_dir,**kwargs):
        calls.append(spec)
        return ExperimentResult(experiment_id=spec.id,fingerprint='fixture',status='COMPLETED',runtime_seconds=.1,
           metrics={'baseline_brier':.2,'corrected_brier':.1,'delta_brier':-.1,'baseline_log_loss':.5,'corrected_log_loss':.4,'delta_log_loss':-.1})
    monkeypatch.setattr(reference,'execute',execute)
    config=Config(objective=ResearchObjective(permitted_parameters={'sample_size':[100]}))
    path=reference.generate_reference_grid(config,tmp_path/'reference',max_conditions=1)
    data=json.loads(path.read_text())
    assert data['planner_access'] is False
    assert data['conditions'][0]['completed']==3
    assert len(calls)==3
    assert not set(data['reference_seeds'])&set(config.exploratory_seeds+config.confirmatory_seeds)
    assert (path.parent/'reference.sqlite').is_file()
    with pytest.raises(ValueError,match='fresh storage'):
        reference.generate_reference_grid(config,path.parent,max_conditions=1)
    with pytest.raises(ValueError,match='max_experiments'):
        reference.generate_reference_grid(Config(budget=Budget(max_experiments=1)),tmp_path/'too-many',max_conditions=1)


def test_modified_reference_summary_is_not_used_as_ground_truth(tmp_path,monkeypatch):
    def execute(spec,artifact_dir,**kwargs):
        return ExperimentResult(experiment_id=spec.id,fingerprint='fixture',status='COMPLETED',runtime_seconds=.1,
           metrics={'baseline_brier':.2,'corrected_brier':.1,'delta_brier':-.1,'baseline_log_loss':.5,'corrected_log_loss':.4,'delta_log_loss':-.1})
    monkeypatch.setattr(reference,'execute',execute)
    path=reference.generate_reference_grid(Config(),tmp_path/'reference',max_conditions=1)
    assert reference.load_reference_grid(path)['conditions'][0]['mean_delta_brier']==pytest.approx(-.1)
    data=json.loads(path.read_text());data['conditions'][0]['mean_delta_brier']=-.9;path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='persisted measurements'):
        reference.load_reference_grid(path)
