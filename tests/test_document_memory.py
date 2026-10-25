import json
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from slothlab.memory.document import DocumentRepository
from slothlab.schemas import ResearchObjective, ResearchSession, Hypothesis, ExperimentSpec, ExperimentResult


def seed(repo):
    objective = ResearchObjective()
    repo.save_objective(objective)
    session = ResearchSession(objective_id=objective.id, model_name='test-only')
    repo.save_session(session)
    hypothesis = Hypothesis(session_id=session.id, statement='Correction improves loss', falsifiable_prediction='delta_brier below zero')
    repo.save_hypothesis(hypothesis)
    spec = ExperimentSpec(hypothesis_id=hypothesis.id, seed=17, rationale='test prior shift')
    repo.save_spec(session.id, spec)
    return session, hypothesis, spec


def measured(spec, **kwargs):
    return ExperimentResult(experiment_id=spec.id, fingerprint='test-fingerprint', status='COMPLETED', runtime_seconds=.1,
        metrics={'baseline_brier': .2, 'corrected_brier': .1, 'delta_brier': -.1,
                 'baseline_log_loss': .5, 'corrected_log_loss': .3, 'delta_log_loss': -.2}, **kwargs)


def test_no_sqlite_roundtrip_and_refresh(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **k: pytest.fail('Guest attempted SQLite'))
    path = tmp_path / 'research.json'
    with DocumentRepository(path) as repo:
        session, _, spec = seed(repo)
        other = DocumentRepository(path)
        result = measured(spec)
        repo.save_result(session.id, result)
        assert other.results(session.id) == [result]
        assert other.find_completed(result.fingerprint) == result
        repo.event(session.id, 'audit', {'result': result.id})
    with DocumentRepository(path) as repo:
        assert repo.events(session.id)[0]['payload'] == {'result': result.id}
        assert repo.get_spec(spec.id) == spec
    assert not list(tmp_path.rglob('*.sqlite*'))


def test_immutable_science(tmp_path):
    repo = DocumentRepository(tmp_path / 'research.json')
    session, hypothesis, spec = seed(repo)
    result = measured(spec)
    repo.save_result(session.id, result)
    for obj, saver, field, value in [(repo.get_objective(session.objective_id), repo.save_objective, 'title', 'changed'),
            (session, repo.save_session, 'model_name', 'changed'),
            (hypothesis, repo.save_hypothesis, 'statement', 'changed'),
            (spec, lambda v: repo.save_spec(session.id, v), 'seed', 20),
            (result, lambda v: repo.save_result(session.id, v), 'fingerprint', 'changed')]:
        setattr(obj, field, value)
        with pytest.raises(ValueError, match='immutable'):
            saver(obj)
    assert repo.get_spec(spec.id).seed == 17


def test_concurrent_writes_do_not_drop_events(tmp_path):
    path = tmp_path / 'research.json'
    repo = DocumentRepository(path)
    session, _, _ = seed(repo)
    def append(index):
        with DocumentRepository(path) as writer:
            writer.event(session.id, 'concurrent', {'index': index})
    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(append, range(40)))
    events = repo.events(session.id)
    assert len(events) == 40
    assert len({e['id'] for e in events}) == 40


def test_strict_schema_and_relations(tmp_path):
    path = tmp_path / 'research.json'
    repo = DocumentRepository(path)
    session, _, _ = seed(repo)
    data = json.loads(path.read_text())
    data['unexpected'] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        repo.list_sessions()


def test_cross_process_refresh_and_session_lock(tmp_path):
    import subprocess
    import sys
    from slothlab.runtime.locking import AlreadyRunningError
    path = tmp_path / 'research.json'
    repo = DocumentRepository(path)
    session, _, _ = seed(repo)
    subprocess.run([sys.executable, '-c',
        'import sys; from slothlab.memory.document import DocumentRepository; '
        'r=DocumentRepository(sys.argv[1]); r.event(sys.argv[2], "child", {"ok":True})',
        str(path), session.id], check=True)
    assert repo.events(session.id, 'child')[0]['payload'] == {'ok': True}
    with repo.session_lock(session.id):
        with pytest.raises(AlreadyRunningError):
            with DocumentRepository(path).session_lock(session.id):
                pass


def test_size_limit_and_nonfinite_audit_roll_back(tmp_path, monkeypatch):
    import slothlab.memory.document as module
    path = tmp_path / 'research.json'
    repo = DocumentRepository(path)
    session, _, _ = seed(repo)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        repo.event(session.id, 'invalid', {'value': float('nan')})
    assert path.read_bytes() == before
    monkeypatch.setattr(module, 'MAX_DOCUMENT_BYTES', 100)
    with pytest.raises(ValueError, match='size limit'):
        repo.list_sessions()
