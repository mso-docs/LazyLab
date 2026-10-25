import pytest
from pydantic import ValidationError
from slothlab.config import Config
from slothlab.schemas import Parameters, ExperimentSpec, ResearchObjective, Budget


def test_strict_contracts_reject_coercion_and_nonfinite():
    for values in ({'sample_size': '500'}, {'sample_size': True}, {'class_separation': float('nan')}, {'unknown': 4}):
        with pytest.raises(ValidationError):
            Parameters.model_validate(values)
    with pytest.raises(ValidationError):
        ExperimentSpec(hypothesis_id='h',seed=True,rationale='invalid')


def test_config_enforces_declared_protocol_and_seed_integrity():
    for values in ({'exploratory_seeds':[1],'confirmatory_seeds':[1]}, {'exploratory_seeds':[-1]}, {'objective':{'constraints':{'arbitrary_shell':True}}}, {'objective':{'permitted_parameters':{'sample_size':[1]}}}, {'objective':{'success_criteria':{'win':True}}}):
        with pytest.raises((ValidationError, ValueError)):
            Config.model_validate(values)
    config = Config(objective=ResearchObjective(success_criteria={'minimum_replications':5}))
    assert config.budget.minimum_replications == 5


def test_model_ids_and_timestamps_are_not_persistence_authority(tmp_path):
    from test_agent import ScriptedResearchClient
    from slothlab.agent.orchestrator import ResearchAgent
    from slothlab.memory.repository import Repository
    config = Config(db_path=str(tmp_path/'memory.sqlite'), budget=Budget(max_rounds=1,max_tokens=500000))
    with Repository(config.db_path) as repo:
        first = ResearchAgent(repo, ScriptedResearchClient([[]]), config).create()
        second = ResearchAgent(repo, ScriptedResearchClient([[]]), config).create()
        first_ids = {h.id for h in repo.hypotheses(first.id)}
        second_ids = {h.id for h in repo.hypotheses(second.id)}
        assert first_ids.isdisjoint(second_ids)
        assert all(h.session_id == second.id for h in repo.hypotheses(second.id))


def test_operational_configuration_rejects_invalid_endpoints_and_empty_domains():
    cases=[{'base_url':'file:///etc/passwd'}, {'base_url':'http://user:password@localhost:11434'}, {'db_path':''},
           {'objective':{'permitted_parameters':{'sample_size':[100]},'constraints':{'parameter_bounds':{'sample_size':{'min':500}}}}},
           {'objective':{'success_criteria':{'require_confirmation':True}},'budget':{'max_candidates':1}}]
    for values in cases:
        with pytest.raises((ValueError,ValidationError)):
            Config.model_validate(values)


def test_configuration_reports_invalid_yaml_as_actionable_input_error(tmp_path):
    from slothlab.config import load_config
    for content in ('- item\n- item\n','objective: [\n'):
        path=tmp_path/'invalid.yaml';path.write_text(content)
        with pytest.raises(ValueError,match='YAML|mapping'):
            load_config(path)
