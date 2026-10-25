"""Finite known-protocol stopping audit, never counterfactual scientific grading."""
import pytest
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.config import Config
from slothlab.lazyloop.audit import SCOPE
from slothlab.memory.repository import Repository
from slothlab.models import FakeModelClient
from slothlab.schemas import Budget, ExperimentSpec, LazyLoopDecision, uid
from test_research_protocol import setup, measurement


def unfinished_batch(repo,tmp_path):
    config=Config(db_path=str(tmp_path/'memory.sqlite'),artifact_dir=str(tmp_path/'artifacts'),
                  budget=Budget(max_experiments=10,max_rounds=10,wall_seconds=60,max_tokens=20000))
    session,hypothesis=setup(repo,config)
    expected=[]
    for seed in [10000,10001,10002]:
        spec=ExperimentSpec(hypothesis_id=hypothesis.id,seed=seed,phase='confirmatory',replicate_group='g',rationale='predeclared final batch')
        repo.save_spec(session.id,spec);expected.append(spec.id)
        if seed!=10002:
            repo.save_result(session.id,measurement(spec))
        else:
            pending=spec
    repo.event(session.id,'confirmation_batch',{'experiment_ids':expected})
    session.budget_consumed['experiments']=2
    session.budget_consumed['tokens']=100
    session.budget_consumed['token_reservations']=100
    session.iteration_count=1
    repo.save_session(session)
    agent=ResearchAgent(repo,FakeModelClient([]),config);agent.session=session
    return agent,pending


@pytest.mark.parametrize('terminal',['STOPPED','COMPLETED'])
def test_soft_or_completion_stop_flags_known_unfinished_protocol(tmp_path,terminal):
    with Repository(tmp_path/'memory.sqlite') as repo:
        agent,pending=unfinished_batch(repo,tmp_path)
        agent.session.termination_reason='Repeated unproductive planning' if terminal=='STOPPED' else 'Operational goal satisfied'
        agent.transition(terminal)
        audit=repo.events(agent.session.id,'termination_audit')[-1]['payload']
        assert audit['known_protocol_premature_stop'] is True
        assert audit['remaining_confirmation_ids']==[pending.id]
        assert audit['scope']==SCOPE


@pytest.mark.parametrize('boundary',['count','wall','tokens','rounds','failure'])
def test_hard_limits_and_critical_failures_are_justified(tmp_path,boundary):
    with Repository(tmp_path/'memory.sqlite') as repo:
        agent,pending=unfinished_batch(repo,tmp_path)
        session,budget=agent.session,agent.session.budget_configuration
        if boundary=='count':session.budget_consumed['experiments']=budget.max_experiments
        elif boundary=='wall':agent._base_wall=budget.wall_seconds
        elif boundary=='tokens':session.budget_consumed['token_reservations']=budget.max_tokens
        elif boundary=='rounds':session.iteration_count=budget.max_rounds
        agent.stop('Critical execution failure' if boundary=='failure' else 'Controller soft stop at an actual hard boundary',failed=boundary=='failure')
        audit=repo.events(session.id,'termination_audit')[-1]['payload']
        assert audit['known_protocol_premature_stop'] is False
        assert audit['remaining_confirmation_ids']==[pending.id]


def test_verified_reuse_fulfills_final_proposal_without_false_omission(tmp_path):
    with Repository(tmp_path/'memory.sqlite') as repo:
        agent,pending=unfinished_batch(repo,tmp_path)
        original=measurement(pending);repo.save_result(agent.session.id,original)
        alias=pending.model_copy(update={'id':uid()})
        repo.save_spec(agent.session.id,alias)
        repo.save_decision(LazyLoopDecision(session_id=agent.session.id,experiment_id=alias.id,decision='REUSE',reason='verified exact result',evidence_references=[original.id]))
        repo.event(agent.session.id,'confirmation_batch',{'experiment_ids':[alias.id]})
        agent.stop('Final confirmation completed')
        audit=repo.events(agent.session.id,'termination_audit')[-1]['payload']
        assert audit['known_protocol_premature_stop'] is False
        assert audit['remaining_confirmation_ids']==[]


def test_no_recorded_batch_does_not_infer_unknown_future_research(tmp_path):
    config=Config(db_path=str(tmp_path/'memory.sqlite'))
    with Repository(config.db_path) as repo:
        session,_=setup(repo,config)
        agent=ResearchAgent(repo,FakeModelClient([]),config);agent.session=session
        agent.stop('Repeated unproductive planning')
        audit=repo.events(session.id,'termination_audit')[-1]['payload']
        assert audit['known_protocol_premature_stop'] is False
        assert 'not inferred' in audit['reason']
