import json
from pathlib import Path

import pytest
from slothlab.schemas import ResearchObjective, ResearchSession, Hypothesis, ExperimentSpec, ExperimentResult, LazyLoopDecision
from slothlab.memory.repository import Repository
from slothlab.reporting.generator import generate_report, report_data
from slothlab.evaluation.quality import assess_quality


def setup(repo):
    objective = ResearchObjective()
    repo.save_objective(objective)
    session = ResearchSession(objective_id=objective.id, model_name='test-only')
    repo.save_session(session)
    hypothesis = Hypothesis(session_id=session.id, statement='Correction improves loss', falsifiable_prediction='delta_brier below zero')
    repo.save_hypothesis(hypothesis)
    spec = ExperimentSpec(hypothesis_id=hypothesis.id, seed=17, rationale='test prior shift')
    repo.save_spec(session.id, spec)
    return session, hypothesis, spec


def result_for(spec, **kwargs):
    return ExperimentResult(experiment_id=spec.id, fingerprint='test-fingerprint', status='COMPLETED', runtime_seconds=0.1, metrics={'baseline_brier': .2, 'corrected_brier': .1, 'delta_brier': -.1, 'baseline_log_loss': .5, 'corrected_log_loss': .3, 'delta_log_loss': -.2}, **kwargs)


def test_results_survive_restart_and_reuse(tmp_path):
    path = tmp_path / 'research.sqlite'
    with Repository(path) as repo:
        session, _, spec = setup(repo)
        result = result_for(spec)
        repo.save_result(session.id, result)
        repo.event(session.id, 'execution', {'result_id': result.id})
    with Repository(path) as repo:
        assert repo.results(session.id) == [result]
        assert repo.find_completed(result.fingerprint) == result
        assert repo.events(session.id, 'execution')[0]['payload']['result_id'] == result.id
        session.state = 'STOPPED'
        session.budget_consumed['experiments'] = 1
        repo.save_session(session)
        assert repo.get_session(session.id).state == 'STOPPED'
        assert repo.connection.execute('SELECT count(*) FROM state_transitions').fetchone()[0] == 2
        assert repo.connection.execute('SELECT count(*) FROM budget_events').fetchone()[0] == 2


def test_failed_results_and_inconsistent_metrics_not_reused(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        session, _, spec = setup(repo)
        result = result_for(spec)
        result.status = 'FAILED'
        repo.save_result(session.id, result)
        assert repo.find_completed(result.fingerprint) is None
        result = result_for(spec)
        result.metrics['delta_brier'] = .9
        repo.save_result(session.id, result)
        assert repo.find_completed(result.fingerprint) is None


def test_missing_artifact_not_reused(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        session, _, spec = setup(repo)
        repo.save_result(session.id, result_for(spec, artifact_paths=[str(tmp_path / 'missing.npz')]))
        assert repo.find_completed('test-fingerprint') is None


def test_cross_session_reuse_preserves_original_measurement(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        first, _, spec = setup(repo)
        second, _, _ = setup(repo)
        result = result_for(spec)
        repo.save_result(first.id, result)
        repo.save_result(second.id, result)
        assert repo.results(second.id) == [result]
        assert report_data(repo, second.id)['quality']['valid_measurements'] == 1


def test_result_identity_immutable(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        session, _, spec = setup(repo)
        result = result_for(spec)
        repo.save_result(session.id, result)
        result.metrics['delta_brier'] = -.2
        with pytest.raises(ValueError, match='immutable'):
            repo.save_result(session.id, result)
        assert repo.results(session.id)[0].metrics['delta_brier'] == -.1


def test_report_grounded_and_unknown_tokens(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        session, _, spec = setup(repo)
        session.budget_consumed['tokens'] = None
        repo.save_session(session)
        result = result_for(spec)
        repo.save_result(session.id, result)
        report = generate_report(repo, session.id, tmp_path / 'artifacts')
        data = json.loads(report.with_name('metrics.json').read_text())
        assert result.id in report.read_text()
        assert data['telemetry']['model_tokens'] is None
        assert data['quality']['protocol_supported_groups'] == 0
        assert data['results'][0]['metrics']['delta_brier'] == -.1


def test_confirmatory_claim_requires_independent_seeds():
    spec = ExperimentSpec(hypothesis_id='h', seed=1, rationale='test', replicate_group='group')
    exploratory = spec.model_copy(update={'phase': 'exploratory'})
    specs = [exploratory]
    results = [result_for(exploratory)]
    for seed in [1, 2, 3]:
        s = spec.model_copy(update={'id': f'c{seed}', 'seed': seed, 'phase': 'confirmatory'})
        specs.append(s)
        results.append(result_for(s))
    quality = assess_quality(specs, results)
    assert quality['protocol_supported_groups'] == 0
    assert quality['groups'][0]['independent_confirmatory_seeds'] == [2, 3]
    s = spec.model_copy(update={'id': 'c4', 'seed': 4, 'phase': 'confirmatory'})
    quality = assess_quality([*specs, s], [*results, result_for(s)])
    assert quality['protocol_supported_groups'] == 1
    assert quality['groups'][0]['protocol_assessment'] == 'CONSISTENT_IMPROVEMENT'


def test_round_trip_all_contracts(tmp_path):
    with Repository(tmp_path / 'memory.sqlite') as repo:
        session, h, spec = setup(repo)
        result = result_for(spec)
        decision = LazyLoopDecision(session_id=session.id, experiment_id=spec.id, decision='EXECUTE', reason='valid')
        for model in [session, h, spec, result, decision, repo.get_objective(session.objective_id)]:
            assert type(model).model_validate_json(model.model_dump_json()) == model
