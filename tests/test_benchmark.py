"""Controller comparisons use deterministic measurement fixtures, never model claims."""
import json
from pathlib import Path

import pytest
import yaml
from slothlab.evaluation import benchmark
from slothlab.lazyloop.fingerprint import fingerprint
from slothlab.memory.repository import Repository
from slothlab.schemas import ExperimentResult


@pytest.fixture
def suite(tmp_path):
    folder = tmp_path / 'objectives'
    folder.mkdir()
    config = {
        'objective': {'title': 'Test prior correction', 'permitted_parameters': {'sample_size': [100], 'train_prevalence': [0.5], 'evaluation_prevalence': [0.2]}},
        'budget': {'max_experiments': 12, 'wall_seconds': 120},
        'exploratory_seeds': [11, 12, 13],
        'confirmatory_seeds': [101, 102, 103],
    }
    (folder / 'shift.yaml').write_text(yaml.safe_dump(config))
    return folder


@pytest.fixture
def measured_fixture(monkeypatch):
    calls = []

    def execute(spec, artifact_dir, **kwargs):
        calls.append((spec, Path(artifact_dir), kwargs))
        return ExperimentResult(
            experiment_id=spec.id, fingerprint=fingerprint(spec),
            status='COMPLETED', runtime_seconds=.125,
            metrics={
                'baseline_brier': .2, 'corrected_brier': .1, 'delta_brier': -.1,
                'baseline_log_loss': .5, 'corrected_log_loss': .3,
                'delta_log_loss': -.2,
            },
        )

    monkeypatch.setattr(benchmark, 'execute', execute)
    return calls


def test_modes_share_constraints_and_keep_cold_independent_memory(suite, tmp_path, measured_fixture):
    path = benchmark.run_benchmark(suite, tmp_path / 'comparison', use_replay=True)
    comparison = json.loads(path.read_text())
    assert comparison['evaluation_kind'].startswith('fixed proposal replay')
    runs = {row['mode']: row for row in comparison['runs']}
    assert set(runs) == {'baseline', 'cache_only', 'lazyloop'}
    assert {mode: row['experiment_count'] for mode, row in runs.items()} == {'baseline': 9, 'cache_only': 6, 'lazyloop': 6}
    assert {mode: row['cache_hits'] for mode, row in runs.items()} == {'baseline': 0, 'cache_only': 3, 'lazyloop': 3}
    assert len(measured_fixture) == 21
    assert len({row['db_path'] for row in runs.values()}) == 3
    budgets = []
    objectives = []
    for mode, row in runs.items():
        # Replay performs no inference; these zeros are observed and intentional.
        assert row['model_tokens'] == 0
        assert row['model_calls'] == 0
        assert row['token_reservations'] == 0
        assert row['inference_seconds'] == 0
        assert row['wall_seconds'] >= 0
        assert row['experiment_seconds'] == pytest.approx(row['experiment_count'] * .125)
        assert row['quality']['independent_seed_count'] == 6
        assert row['quality']['quality_score'] == 1.0
        assert row['quality']['protocol_supported_groups'] == 1
        assert row['quality']['groups'][0]['independent_confirmatory_seeds'] == [101, 102, 103]
        assert Path(row['report']).is_file()
        with Repository(row['db_path']) as repo:
            session = repo.get_session(row['session_id'])
            budgets.append(session.budget_configuration.model_dump())
            objective = repo.get_objective(session.objective_id).model_dump()
            objective.pop('id')
            objectives.append(objective)
            assert len(repo.list_sessions()) == 1
            assert len(repo.specs(session.id)) == 9
            assert all(spec.seed in {11, 12, 13, 101, 102, 103} for spec in repo.specs(session.id))
            assert len(repo.results(session.id)) == row['experiment_count']
            assert len(repo.decisions(session.id)) == 9
    assert all(budget == budgets[0] for budget in budgets)
    assert all(objective == objectives[0] for objective in objectives)
    # A new invocation cannot accidentally warm-start any comparison arm.
    with pytest.raises(ValueError, match='fresh storage'):
        benchmark.run_benchmark(suite, path.parent, use_replay=True)


def test_benchmark_preserves_unknown_token_telemetry(suite, tmp_path, measured_fixture, monkeypatch):
    original = benchmark.replay

    def with_missing_telemetry(repo, config):
        session = original(repo, config)
        session.budget_consumed['tokens'] = None
        repo.save_session(session)
        return session

    monkeypatch.setattr(benchmark, 'replay', with_missing_telemetry)
    path = benchmark.run_benchmark(suite, tmp_path / 'unknown', use_replay=True)
    comparison = json.loads(path.read_text())
    assert all(row['model_tokens'] is None for row in comparison['runs'])
    assert 'unknown' in path.with_suffix('.md').read_text()
    for row in comparison['runs']:
        metrics = json.loads(Path(row['report']).with_name('metrics.json').read_text())
        assert metrics['telemetry']['model_tokens'] is None


def test_benchmark_rejects_missing_suite(tmp_path):
    with pytest.raises(ValueError, match='No YAML'):
        benchmark.run_benchmark(tmp_path / 'missing', tmp_path / 'output', use_replay=True)


def test_failed_arms_remain_inspectable_and_do_not_abort_the_suite(suite,tmp_path,monkeypatch):
    def fail(repo,config):
        raise RuntimeError('deliberate fixture failure')
    monkeypatch.setattr(benchmark,'replay',fail)
    path=benchmark.run_benchmark(suite,tmp_path/'failed',use_replay=True)
    data=json.loads(path.read_text())
    assert data['complete'] is True
    assert len(data['runs'])==3
    assert all(r['state']=='FAILED' and r['model_tokens'] is None for r in data['runs'])
    assert all(Path(r['report']).is_file() for r in data['runs'])
    assert all(c['valid_pairs']==0 for c in data['paired_comparisons'])


def test_repeated_proposal_replay_exercises_adaptive_stop(suite,tmp_path,measured_fixture):
    protocol={'schedule':[{'phase':'exploratory','seed':11} for _ in range(9)]}
    (suite/'shift.replay.json').write_text(json.dumps(protocol))
    path=benchmark.run_benchmark(suite,tmp_path/'repetition',use_replay=True)
    runs={row['mode']:row for row in json.loads(path.read_text())['runs']}
    assert runs['baseline']['experiment_count']==9
    assert runs['cache_only']['experiment_count']==1
    assert runs['cache_only']['cache_hits']==8
    assert runs['lazyloop']['experiment_count']==1
    assert runs['lazyloop']['cache_hits']==3
    assert 'Repeated unproductive' in runs['lazyloop']['termination_reason']
    assert len({r['constraints_signature'] for r in runs.values()})==1


def test_runtime_overrides_cannot_change_scientific_constraints(suite,tmp_path,measured_fixture):
    with pytest.raises(ValueError,match='runtime settings only'):
        benchmark.run_benchmark(suite,tmp_path/'bad-override',use_replay=True,config_overrides={'budget':{'max_experiments':1}})
    path=benchmark.run_benchmark(suite,tmp_path/'runtime',use_replay=True,config_overrides={'inference_thinking':False,'inference_timeout_seconds':20})
    data=json.loads(path.read_text())
    for row in data['runs']:
        with Repository(row['db_path']) as repo:
            saved=repo.events(row['session_id'],'configuration')[0]['payload']
            assert saved['inference_thinking'] is False
            assert saved['budget']['max_experiments']==12


def test_trial_seed_partitions_are_independent_and_paired():
    from slothlab.config import Config
    config=Config(exploratory_seeds=[1,2,3],confirmatory_seeds=[10,11,12])
    partitions=benchmark.trial_seed_partitions(config,3)
    assert partitions[0]['exploratory_seeds']==[1,2,3]
    seeds=[set(part['exploratory_seeds']+part['confirmatory_seeds']) for part in partitions]
    assert all(not seeds[a]&seeds[b] for a in range(3) for b in range(a))


def test_adaptive_replay_does_not_discard_known_independent_confirmation(suite,tmp_path,measured_fixture):
    schedule=[{'phase':'exploratory','seed':seed} for seed in [11,12,13,11,12,13]]
    schedule += [{'phase':'confirmatory','seed':seed} for seed in [101,102,103]]
    (suite/'shift.replay.json').write_text(json.dumps({'schedule':schedule}))
    path=benchmark.run_benchmark(suite,tmp_path/'confirmation',use_replay=True)
    data=json.loads(path.read_text())
    full=next(row for row in data['runs'] if row['mode']=='lazyloop')
    assert full['experiment_count']==6
    assert full['quality']['groups'][0]['independent_confirmatory_seeds']==[101,102,103]
    with Repository(full['db_path']) as repo:
        assert repo.events(full['session_id'],'soft_stop_deferred')
