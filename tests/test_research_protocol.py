"""Scientific autonomy contracts, numerical completion, and honest recovery."""
import json
from unittest.mock import patch
import pytest
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.agent.planner import planning_schema
from slothlab.lazyloop.controller import validate_proposal
from slothlab.lazyloop.stopping import objective_completion
from slothlab.memory.repository import Repository
from slothlab.schemas import (Analysis, Assessment, ExperimentResult, ExperimentSpec,
                              Hypothesis, LazyLoopDecision, Parameters, ResearchObjective, ResearchSession)
from slothlab.config import Config
from test_agent import ScriptedResearchClient, candidate, configured


def measurement(spec, delta=-.01):
    return ExperimentResult(experiment_id=spec.id,fingerprint='test-only-measurement',status='COMPLETED',runtime_seconds=.2,
        metrics={'baseline_brier':.2,'corrected_brier':.2+delta,'delta_brier':delta,
                 'baseline_log_loss':.5,'corrected_log_loss':.5+delta,'delta_log_loss':delta})


def setup(repo, config):
    repo.save_objective(config.objective)
    s = ResearchSession(objective_id=config.objective.id,model_name='scripted-test',budget_configuration=config.budget)
    repo.save_session(s)
    h = Hypothesis(session_id=s.id,statement='Correction improves Brier',falsifiable_prediction='delta_brier is negative',expected_delta_direction='negative')
    repo.save_hypothesis(h)
    return s,h


def test_compact_planning_schema_exposes_only_scientific_choices():
    config = Config(objective=ResearchObjective(permitted_parameters={k:[v] for k,v in Parameters().model_dump().items()}))
    h = Hypothesis(session_id='s',statement='a',falsifiable_prediction='b')
    previous = ExperimentSpec(hypothesis_id=h.id,seed=0,rationale='already measured')
    schema = planning_schema(config,[h],False,True,[previous])
    props = schema['properties']['candidates']['items']['properties']
    assert set(props) == {'hypothesis_id','parameters','seed','phase','rationale'}
    assert 0 not in props['seed']['enum']
    assert 1 in props['seed']['enum']
    assert 'source' not in json.dumps(schema)


def test_parameter_bounds_and_phase_constraints_are_hard_authorization():
    config=Config(objective=ResearchObjective(constraints={'parameter_bounds':{'sample_size':{'min':500,'max':1000}},'allowed_phases':['exploratory'],'require_replication_group':True,'max_estimated_compute_seconds':2}))
    with pytest.raises(ValueError,match='bounds'):
        validate_proposal(ExperimentSpec(hypothesis_id='h',seed=0,rationale='x',parameters={'sample_size':100}),config,{'h'})
    with pytest.raises(ValueError,match='phase'):
        validate_proposal(ExperimentSpec(hypothesis_id='h',seed=10000,phase='confirmatory',rationale='x'),config,{'h'})


def test_completion_requires_predeclared_independent_confirmation():
    config=Config(objective=ResearchObjective(success_criteria={'minimum_replications':3,'minimum_conditions':1,'minimum_exploratory_experiments':1,'require_confirmation':True,'effect_direction':'negative'}))
    exploratory=ExperimentSpec(hypothesis_id='h',seed=1,rationale='explore')
    specs=[exploratory];results=[measurement(exploratory)]
    for seed in [10000,10001]:
        s=ExperimentSpec(hypothesis_id='h',seed=seed,phase='confirmatory',rationale='confirm')
        specs.append(s);results.append(measurement(s))
    assert not objective_completion(config,specs,results,Repository.verified)['satisfied']
    s=ExperimentSpec(hypothesis_id='h',seed=10002,phase='confirmatory',rationale='confirm')
    specs.append(s);results.append(measurement(s))
    verdict=objective_completion(config,specs,results,Repository.verified)
    assert verdict['satisfied']
    assert len(verdict['evidence_ids'])==3
    results[-1]=measurement(s,.01)
    assert not objective_completion(config,specs,results,Repository.verified)['satisfied']
    # Repeated results with the same seed cannot inflate the independent count.
    assert not objective_completion(config,specs,results[:-1]+[results[1]],Repository.verified)['satisfied']


def test_revision_uses_valid_evidence_and_creates_untested_new_hypothesis(tmp_path):
    config=configured(tmp_path,max_rounds=1)
    with Repository(config.db_path) as repo:
        s,h=setup(repo,config)
        spec=ExperimentSpec(hypothesis_id=h.id,seed=1,rationale='observation')
        repo.save_spec(s.id,spec)
        result=measurement(spec,.02)
        repo.save_result(s.id,result)
        agent=ResearchAgent(repo,ScriptedResearchClient([]),config);agent.session=s
        assessment=Assessment(hypothesis_id=h.id,status='SUPPORTED',evidence_ids=[result.id],explanation='A positive measured delta challenges the claim',revised_statement='Correction can worsen this condition',revised_prediction='delta_brier is positive in this condition',revised_direction='positive')
        agent.apply_analysis(Analysis(assessments=[assessment],next_direction='Replicate the counterexample on new seeds'))
        hypotheses=repo.hypotheses(s.id)
        assert len(hypotheses)==2
        assert hypotheses[1].status=='PROPOSED'
        assert hypotheses[1].id!=h.id
        assert repo.events(s.id,'hypothesis_revision')[0]['payload']['evidence_ids']==[result.id]
        assert agent.context()['latest_research_direction']=='Replicate the counterexample on new seeds'
        agent.apply_analysis(Analysis(assessments=[assessment],next_direction='Repeat'))
        assert len(repo.hypotheses(s.id))==2  # no recursive duplicate revision


def test_resume_reconciles_verified_manifest_without_execution(tmp_path):
    config=configured(tmp_path,max_rounds=1)
    with Repository(config.db_path) as repo:
        s,h=setup(repo,config)
        spec=ExperimentSpec(hypothesis_id=h.id,seed=1,rationale='interrupted persistence')
        repo.save_spec(s.id,spec)
        repo.save_decision(LazyLoopDecision(session_id=s.id,experiment_id=spec.id,decision='EXECUTE',reason='authorized'))
        s.budget_consumed['experiments']=1;repo.save_session(s)
        recovered=measurement(spec)
        with patch('slothlab.agent.orchestrator.recover',return_value=recovered),patch('slothlab.agent.orchestrator.execute') as execute:
            resumed=ResearchAgent(repo,ScriptedResearchClient([[]]),config).run(s.id)
        assert resumed.budget_consumed['experiments']==1
        assert repo.results(s.id)==[recovered]
        assert repo.events(s.id,'execution_reconciled')
        execute.assert_not_called()


def test_declared_numerical_completion_reaches_completed_state(tmp_path):
    config=configured(tmp_path,max_rounds=1)
    config.objective.success_criteria={'minimum_replications':3,'require_confirmation':False,'minimum_conditions':1,'effect_direction':'negative'}
    with Repository(config.db_path) as repo:
        s,h=setup(repo,config)
        for seed in range(3):
            spec=ExperimentSpec(hypothesis_id=h.id,seed=seed,rationale='replicated controlled fixture')
            repo.save_spec(s.id,spec);repo.save_result(s.id,measurement(spec))
        with patch('slothlab.agent.orchestrator.execute') as execute:
            completed=ResearchAgent(repo,ScriptedResearchClient([]),config).run(s.id)
        assert completed.state=='COMPLETED'
        assert 'Predeclared' in completed.termination_reason
        assert repo.events(s.id,'completion_check')[-1]['payload']['satisfied']
        execute.assert_not_called()


@pytest.mark.parametrize('interrupted_state',['REPLANNING','HYPOTHESIZING'])
def test_resume_interrupted_before_hypotheses_exist(tmp_path,interrupted_state):
    config=configured(tmp_path,max_rounds=1)
    with Repository(config.db_path) as repo:
        repo.save_objective(config.objective)
        session=ResearchSession(objective_id=config.objective.id,model_name='test',state=interrupted_state,budget_configuration=config.budget)
        session.termination_reason='Paused by user; resumable'
        session.budget_consumed['token_reservations']=100
        repo.save_session(session)
        resumed=ResearchAgent(repo,ScriptedResearchClient([[]]),config).run(session.id)
        assert resumed.state=='STOPPED'
        assert len(repo.hypotheses(session.id))==2
        assert resumed.budget_consumed['token_reservations']>=100
        assert resumed.termination_reason!='Paused by user; resumable'
        transition=next(e for e in repo.events(session.id,'state_transition') if e['payload']['to']=='HYPOTHESIZING')
        assert transition['payload']['recovery'] is True


def test_resume_finishes_predeclared_confirmation_before_assessing_success(tmp_path):
    config=configured(tmp_path,max_rounds=1)
    config.objective.success_criteria={'minimum_replications':3,'require_confirmation':True,'effect_direction':'negative'}
    with Repository(config.db_path) as repo:
        s,h=setup(repo,config)
        exploratory=ExperimentSpec(hypothesis_id=h.id,seed=1,rationale='explore',replicate_group='g')
        repo.save_spec(s.id,exploratory);repo.save_result(s.id,measurement(exploratory))
        ids=[]
        for seed in [10000,10001,10002,10003]:
            spec=ExperimentSpec(hypothesis_id=h.id,seed=seed,phase='confirmatory',rationale='predeclared final batch',replicate_group='g')
            repo.save_spec(s.id,spec);ids.append(spec.id)
            if seed!=10003:
                repo.save_result(s.id,measurement(spec))
            else:
                pending=spec
        s.state='EXECUTING';s.budget_consumed['experiments']=4;repo.save_session(s)
        repo.event(s.id,'confirmation_batch',{'experiment_ids':ids})
        with patch('slothlab.agent.orchestrator.execute',return_value=measurement(pending,.01)) as execute:
            resumed=ResearchAgent(repo,ScriptedResearchClient([]),config).run(s.id)
        execute.assert_called_once()
        assert resumed.state=='STOPPED'
        assert len(repo.results(s.id))==5
        assert not repo.events(s.id,'completion_check')[-1]['payload']['satisfied']


def test_phase_and_seed_are_correlated_in_model_contract():
    config=Config()
    h=Hypothesis(session_id='s',statement='a',falsifiable_prediction='b')
    schema=planning_schema(config,[h],True,True)
    branches=schema['properties']['candidates']['items']['anyOf']
    by_phase={item['properties']['phase']['enum'][0]:item['properties']['seed']['enum'] for item in branches}
    assert by_phase=={'exploratory':config.exploratory_seeds,'confirmatory':config.confirmatory_seeds}
    final=planning_schema(config,[h],True,True,require_confirmation=True)
    candidates=final['properties']['candidates']
    assert candidates['minItems']==config.budget.minimum_replications
    assert candidates['items']['properties']['phase']['enum']==['confirmatory']
    assert candidates['items']['properties']['seed']['enum']==config.confirmatory_seeds


def test_exhausted_fixed_domain_never_restores_used_seeds():
    from slothlab.agent.planner import NoViablePlan
    config=Config(objective=ResearchObjective(permitted_parameters={k:[v] for k,v in Parameters().model_dump().items()}),exploratory_seeds=[0])
    h=Hypothesis(session_id='s',statement='a',falsifiable_prediction='b')
    previous=ExperimentSpec(hypothesis_id=h.id,seed=0,rationale='already measured')
    with pytest.raises(NoViablePlan):
        planning_schema(config,[h],False,True,[previous])
    remaining=planning_schema(config,[h],True,True,[previous])
    assert remaining['properties']['candidates']['items']['properties']['phase']['enum']==['confirmatory']


def test_predeclared_exploration_target_requests_final_confirmation_and_repairs_bad_phase(tmp_path):
    config=configured(tmp_path,max_rounds=3,max_candidates=3,max_experiments=6)
    config.objective.permitted_parameters={k:[v] for k,v in Parameters().model_dump().items()}
    config.objective.success_criteria={'minimum_replications':3,'minimum_exploratory_experiments':1,'require_confirmation':True,'effect_direction':'negative'}
    params=Parameters().model_dump()
    first=[candidate(0,parameters=params)]
    malformed_final=[candidate(10000,parameters=params,phase='exploratory')]
    valid_final=[candidate(seed,parameters=params,phase='confirmatory') for seed in [10000,10001,10002]]
    client=ScriptedResearchClient([first,malformed_final,valid_final])
    with Repository(config.db_path) as repo,patch('slothlab.agent.orchestrator.execute',side_effect=lambda spec,*args,**kwargs:measurement(spec)) as execute:
        session=ResearchAgent(repo,client,config).create()
        assert session.state=='COMPLETED'
        assert execute.call_count==4
        assert len(repo.events(session.id,'invalid_model_output'))==1
        assert repo.events(session.id,'confirmation_strategy')
        final_calls=[call for call in client.calls if 'PROTOCOL PHASE: FINAL CONFIRMATION' in call['prompt']]
        assert len(final_calls)==2
        assert all(call['schema']['properties']['candidates']['items']['properties']['phase']['enum']==['confirmatory'] for call in final_calls)


def test_multiple_conditions_share_one_final_heldout_batch(tmp_path):
    config=configured(tmp_path,max_rounds=3,max_candidates=6,max_experiments=8)
    config.objective.permitted_parameters={k:[v] for k,v in Parameters().model_dump().items()}
    config.objective.permitted_parameters['evaluation_prevalence']=[.2,.8]
    config.objective.success_criteria={'minimum_replications':3,'minimum_exploratory_experiments':2,'minimum_conditions':2,'require_confirmation':True,'minimum_confirmatory_groups':2,'effect_direction':'negative'}
    conditions=[Parameters(evaluation_prevalence=value).model_dump() for value in [.2,.8]]
    exploratory=[candidate(0,parameters=p) for p in conditions]
    final=[candidate(seed,parameters=p,phase='confirmatory') for p in conditions for seed in [10000,10001,10002]]
    client=ScriptedResearchClient([exploratory,final])
    with Repository(config.db_path) as repo,patch('slothlab.agent.orchestrator.execute',side_effect=lambda spec,*args,**kwargs:measurement(spec)) as execute:
        session=ResearchAgent(repo,client,config).create()
        assert session.state=='COMPLETED'
        assert execute.call_count==8
        assert repo.events(session.id,'completion_check')[-1]['payload']['qualifying_groups']==2
        assert len(repo.events(session.id,'confirmation_batch'))==1
        schema=next(call['schema'] for call in client.calls if 'PROTOCOL PHASE: FINAL CONFIRMATION' in call['prompt'])
        assert schema['properties']['candidates']['minItems']==6


def test_confirmation_cannot_start_before_predeclared_exploration_target(tmp_path):
    config=configured(tmp_path,max_rounds=3,max_candidates=3,max_experiments=6)
    config.objective.permitted_parameters={k:[v] for k,v in Parameters().model_dump().items()}
    config.objective.success_criteria={'minimum_replications':3,'minimum_exploratory_experiments':2,'require_confirmation':True,'effect_direction':'negative'}
    params=Parameters().model_dump()
    plans=[[candidate(0,parameters=params)],[candidate(1,parameters=params)],
           [candidate(seed,parameters=params,phase='confirmatory') for seed in [10000,10001,10002]]]
    client=ScriptedResearchClient(plans)
    with Repository(config.db_path) as repo,patch('slothlab.agent.orchestrator.execute',side_effect=lambda spec,*args,**kwargs:measurement(spec)):
        session=ResearchAgent(repo,client,config).create()
        assert session.state=='COMPLETED'
        plans=[call['schema'] for call in client.calls if 'candidates' in call['schema'].get('properties',{})]
        assert len(plans)==3
        assert [schema['properties']['candidates']['items']['properties']['phase']['enum'] for schema in plans]==[['exploratory'],['exploratory'],['confirmatory']]
