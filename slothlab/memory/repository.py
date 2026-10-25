"""Transactional SQLite scientific memory with immutable evidence identities."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

from slothlab.schemas import (
    ResearchObjective, ResearchSession, Hypothesis, ExperimentSpec,
    ExperimentResult, LazyLoopDecision, now,
)


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path) if str(path) != ':memory:' else path
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.executescript('''
        CREATE TABLE IF NOT EXISTS research_objectives (
            id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_sessions (
            id TEXT PRIMARY KEY, objective_id TEXT NOT NULL REFERENCES research_objectives(id),
            data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS experiment_specs (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id), data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS experiment_results (
            id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiment_specs(id),
            fingerprint TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS result_fingerprint ON experiment_results(fingerprint,status);
        CREATE TABLE IF NOT EXISTS evidence_records (
            session_id TEXT NOT NULL REFERENCES research_sessions(id),
            result_id TEXT NOT NULL REFERENCES experiment_results(id),
            PRIMARY KEY(session_id,result_id));
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            experiment_id TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            kind TEXT NOT NULL, timestamp TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS state_transitions (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            timestamp TEXT NOT NULL, old_state TEXT, new_state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS budget_events (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES research_sessions(id),
            timestamp TEXT NOT NULL, data TEXT NOT NULL);
        ''')
        self.connection.commit()

    def close(self):
        self.connection.close()

    def session_lock(self, session_id):
        from slothlab.runtime.locking import session_lock
        return session_lock(self.path, session_id)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, table, identity, cls):
        row = self.connection.execute(f'SELECT data FROM {table} WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise KeyError(f'{table}: unknown id {identity}')
        return cls.model_validate_json(row['data'])

    def _list(self, table, cls, session_id=None):
        query, args = f'SELECT data FROM {table}', ()
        if session_id is not None:
            query += ' WHERE session_id=?'
            args = (session_id,)
        query += ' ORDER BY rowid'
        return [cls.model_validate_json(r['data']) for r in self.connection.execute(query, args)]

    def save_objective(self, obj: ResearchObjective):
        with self.connection:
            row=self.connection.execute('SELECT data FROM research_objectives WHERE id=?',(obj.id,)).fetchone()
            if row is not None and ResearchObjective.model_validate_json(row['data']) != obj:
                raise ValueError('Research objective identities are immutable')
            self.connection.execute('INSERT OR IGNORE INTO research_objectives VALUES (?,?)', (obj.id, obj.model_dump_json()))

    def get_objective(self, identity):
        return self._get('research_objectives', identity, ResearchObjective)

    def save_session(self, session: ResearchSession):
        with self.connection:
            row = self.connection.execute('SELECT data FROM research_sessions WHERE id=?', (session.id,)).fetchone()
            previous = ResearchSession.model_validate_json(row['data']) if row else None
            if previous is not None:
                immutable = ('objective_id', 'model_name', 'mode', 'budget_configuration', 'started_at')
                changed = [name for name in immutable if getattr(previous, name) != getattr(session, name)]
                if changed:
                    raise ValueError('Research session metadata is immutable: ' + ', '.join(changed))
            self.connection.execute('INSERT INTO research_sessions VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (session.id, session.objective_id, session.model_dump_json()))
            if previous is None or previous.state != session.state:
                self.connection.execute('INSERT INTO state_transitions(session_id,timestamp,old_state,new_state) VALUES (?,?,?,?)', (session.id, now(), previous.state if previous else None, session.state))
            if previous is None or previous.budget_consumed != session.budget_consumed:
                self.connection.execute('INSERT INTO budget_events(session_id,timestamp,data) VALUES (?,?,?)', (session.id, now(), json.dumps(session.budget_consumed, allow_nan=False)))

    def get_session(self, identity):
        return self._get('research_sessions', identity, ResearchSession)

    def list_sessions(self):
        return self._list('research_sessions', ResearchSession)

    def save_hypothesis(self, hypothesis: Hypothesis):
        with self.connection:
            existing = self.connection.execute('SELECT session_id,data FROM hypotheses WHERE id=?', (hypothesis.id,)).fetchone()
            if existing is not None and existing['session_id'] != hypothesis.session_id:
                raise ValueError('Hypothesis identity already belongs to another session')
            if existing is not None:
                original=Hypothesis.model_validate_json(existing['data'])
                if original.model_dump(exclude={'status'}) != hypothesis.model_dump(exclude={'status'}):
                    raise ValueError('Scientific hypothesis declarations are immutable; create a new hypothesis for a revision')
            self.connection.execute('INSERT INTO hypotheses VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (hypothesis.id, hypothesis.session_id, hypothesis.model_dump_json()))

    def hypotheses(self, session_id):
        return self._list('hypotheses', Hypothesis, session_id)

    def save_spec(self, session_id, spec: ExperimentSpec):
        hypothesis = self._get('hypotheses', spec.hypothesis_id, Hypothesis)
        if hypothesis.session_id != session_id:
            raise ValueError('Experiment hypothesis belongs to a different session')
        with self.connection:
            self.connection.execute('INSERT INTO experiment_specs VALUES (?,?,?,?) ON CONFLICT(id) DO NOTHING', (spec.id, session_id, spec.hypothesis_id, spec.model_dump_json()))
            existing = self._get('experiment_specs', spec.id, ExperimentSpec)
            if existing != spec:
                raise ValueError('Experiment identities are immutable')

    def get_spec(self, identity):
        return self._get('experiment_specs', identity, ExperimentSpec)

    def specs(self, session_id):
        return self._list('experiment_specs', ExperimentSpec, session_id)

    def save_result(self, session_id, result: ExperimentResult):
        # A cache hit links the existing measurement; it does not fabricate a new one.
        with self.connection:
            self.connection.execute('INSERT INTO experiment_results VALUES (?,?,?,?,?) ON CONFLICT(id) DO NOTHING', (result.id, result.experiment_id, result.fingerprint, result.status, result.model_dump_json()))
            existing = self._get('experiment_results', result.id, ExperimentResult)
            if existing != result:
                raise ValueError('Result identities are immutable')
            self.connection.execute('INSERT OR IGNORE INTO evidence_records VALUES (?,?)', (session_id, result.id))

    def results(self, session_id):
        rows = self.connection.execute('SELECT r.data FROM experiment_results r JOIN evidence_records e ON r.id=e.result_id WHERE e.session_id=? ORDER BY r.rowid', (session_id,))
        return [ExperimentResult.model_validate_json(r['data']) for r in rows]

    @staticmethod
    def verified(result: ExperimentResult) -> bool:
        required = ('baseline_brier', 'corrected_brier', 'delta_brier', 'baseline_log_loss', 'corrected_log_loss', 'delta_log_loss')
        if result.status != 'COMPLETED' or any(key not in result.metrics or not math.isfinite(result.metrics[key]) for key in required):
            return False
        if any(result.metrics[key] < 0 for key in ('baseline_log_loss', 'corrected_log_loss')):
            return False
        if any(not 0 <= result.metrics[key] <= 1 for key in ('baseline_brier', 'corrected_brier')):
            return False
        if not math.isclose(result.metrics['corrected_brier'] - result.metrics['baseline_brier'], result.metrics['delta_brier'], abs_tol=1e-10):
            return False
        if not math.isclose(result.metrics['corrected_log_loss'] - result.metrics['baseline_log_loss'], result.metrics['delta_log_loss'], abs_tol=1e-10):
            return False
        for artifact in result.artifact_paths:
            if not Path(artifact).is_file():
                return False
        hashes = result.environment_metadata.get('artifact_sha256', {})
        for filename, expected in hashes.items():
            path = Path(filename)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return False
        return True

    def find_completed(self, fingerprint):
        rows = self.connection.execute('SELECT data FROM experiment_results WHERE fingerprint=? AND status=? ORDER BY rowid DESC', (fingerprint, 'COMPLETED'))
        for row in rows:
            result = ExperimentResult.model_validate_json(row['data'])
            if self.verified(result):
                return result
        return None

    def save_decision(self, decision: LazyLoopDecision):
        with self.connection:
            self.connection.execute('INSERT INTO agent_decisions(session_id,experiment_id,data) VALUES (?,?,?)', (decision.session_id, decision.experiment_id, decision.model_dump_json()))

    def decisions(self, session_id):
        return self._list('agent_decisions', LazyLoopDecision, session_id)

    def event(self, session_id, kind, payload):
        with self.connection:
            self.connection.execute('INSERT INTO events(session_id,kind,timestamp,payload) VALUES (?,?,?,?)', (session_id, kind, now(), json.dumps(payload, allow_nan=False)))

    def events(self, session_id, kind=None):
        query = 'SELECT * FROM events WHERE session_id=?'
        args = [session_id]
        if kind is not None:
            query += ' AND kind=?'
            args.append(kind)
        return [dict(r) | {'payload': json.loads(r['payload'])} for r in self.connection.execute(query + ' ORDER BY id', args)]
