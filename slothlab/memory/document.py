"""Database-free scientific memory stored as a bounded, atomic JSON document."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from slothlab.memory.repository import Repository
from slothlab.runtime.atomic import atomic_json
from slothlab.runtime.locking import file_lock, session_lock
from slothlab.schemas import (ResearchObjective, ResearchSession, Hypothesis,
    ExperimentSpec, ExperimentResult, LazyLoopDecision, now)

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    id: int
    session_id: str
    kind: str
    timestamp: str
    payload: Any


class Document(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    version: int = 1
    objectives: list[ResearchObjective] = Field(default_factory=list)
    sessions: list[ResearchSession] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    specs: list[ExperimentSpec] = Field(default_factory=list)
    results: list[ExperimentResult] = Field(default_factory=list)
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    decisions: list[LazyLoopDecision] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)

    def check(self):
        if self.version != 1:
            raise ValueError('Unsupported research document version')
        for name in ('objectives', 'sessions', 'hypotheses', 'specs', 'results', 'events'):
            values = getattr(self, name)
            if len({item.id for item in values}) != len(values):
                raise ValueError('Duplicate document identities')
        objectives = {v.id for v in self.objectives}
        sessions = {v.id for v in self.sessions}
        hypotheses = {v.id: v for v in self.hypotheses}
        specs = {v.id for v in self.specs}
        results = {v.id for v in self.results}
        if any(v.objective_id not in objectives for v in self.sessions):
            raise ValueError('Unknown objective')
        if any(v.session_id not in sessions for v in self.hypotheses):
            raise ValueError('Unknown hypothesis session')
        if any(v.hypothesis_id not in hypotheses for v in self.specs):
            raise ValueError('Unknown experiment hypothesis')
        if any(v.experiment_id not in specs for v in self.results):
            raise ValueError('Unknown result experiment')
        if any(sid not in sessions or len(ids) != len(set(ids)) or any(i not in results for i in ids)
               for sid, ids in self.evidence.items()):
            raise ValueError('Invalid evidence links')
        if any(v.session_id not in sessions for v in [*self.decisions, *self.events]):
            raise ValueError('Unknown audit session')
        return self


def parse_document(data: bytes) -> Document:
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError('Research document exceeds size limit')
    json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
    return Document.model_validate_json(data).check()


class DocumentRepository:
    verified = staticmethod(Repository.verified)

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._closed = False
        with file_lock(self.path.with_name('.' + self.path.name + '.write.lock'), blocking=True):
            if not self.path.exists():
                atomic_json(self.path, Document().model_dump(mode='json'))
            self._read()

    def close(self):
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def session_lock(self, session_id):
        return session_lock(self.path, session_id)

    def _read(self):
        if self._closed:
            raise RuntimeError('Research document is closed')
        if self.path.stat().st_size > MAX_DOCUMENT_BYTES:
            raise ValueError('Research document exceeds size limit')
        with self.path.open('rb') as handle:
            return parse_document(handle.read(MAX_DOCUMENT_BYTES + 1))

    @contextmanager
    def _write(self):
        with file_lock(self.path.with_name('.' + self.path.name + '.write.lock'), blocking=True):
            doc = self._read()
            yield doc
            doc.check()
            json.dumps(doc.model_dump(mode='python'), allow_nan=False)
            data = doc.model_dump(mode='json')
            if len(json.dumps(data, allow_nan=False, indent=2).encode()) + 1 > MAX_DOCUMENT_BYTES:
                raise ValueError('Research document exceeds size limit')
            # Validate serialization too: arbitrary audit metadata cannot bypass JSON safety.
            parse_document(json.dumps(data, allow_nan=False).encode())
            atomic_json(self.path, data)

    def snapshot(self):
        return self._read()

    @staticmethod
    def _get(doc, name, identity):
        for item in getattr(doc, name):
            if item.id == identity:
                return item
        raise KeyError(f'{name}: unknown id {identity}')

    def save_objective(self, obj):
        with self._write() as doc:
            existing = next((v for v in doc.objectives if v.id == obj.id), None)
            if existing is not None and existing != obj:
                raise ValueError('Research objective identities are immutable')
            if existing is None:
                doc.objectives.append(obj)

    def get_objective(self, identity):
        return self._get(self._read(), 'objectives', identity)

    def save_session(self, session):
        with self._write() as doc:
            existing = next((v for v in doc.sessions if v.id == session.id), None)
            if existing:
                changed = [name for name in ('objective_id', 'model_name', 'mode', 'budget_configuration', 'started_at') if getattr(existing, name) != getattr(session, name)]
                if changed:
                    raise ValueError('Research session metadata is immutable: ' + ', '.join(changed))
                doc.sessions[doc.sessions.index(existing)] = session
            else:
                doc.sessions.append(session)

    def get_session(self, identity):
        return self._get(self._read(), 'sessions', identity)

    def list_sessions(self):
        return self._read().sessions

    def save_hypothesis(self, hypothesis):
        with self._write() as doc:
            existing = next((v for v in doc.hypotheses if v.id == hypothesis.id), None)
            if existing:
                if existing.model_dump(exclude={'status'}) != hypothesis.model_dump(exclude={'status'}):
                    raise ValueError('Scientific hypothesis declarations are immutable; create a new hypothesis for a revision')
                doc.hypotheses[doc.hypotheses.index(existing)] = hypothesis
            else:
                doc.hypotheses.append(hypothesis)

    def hypotheses(self, session_id):
        return [v for v in self._read().hypotheses if v.session_id == session_id]

    def save_spec(self, session_id, spec):
        with self._write() as doc:
            if self._get(doc, 'hypotheses', spec.hypothesis_id).session_id != session_id:
                raise ValueError('Experiment hypothesis belongs to a different session')
            existing = next((v for v in doc.specs if v.id == spec.id), None)
            if existing is not None and existing != spec:
                raise ValueError('Experiment identities are immutable')
            if existing is None:
                doc.specs.append(spec)

    def get_spec(self, identity):
        return self._get(self._read(), 'specs', identity)

    def specs(self, session_id):
        doc = self._read()
        ids = {h.id for h in doc.hypotheses if h.session_id == session_id}
        return [v for v in doc.specs if v.hypothesis_id in ids]

    def save_result(self, session_id, result):
        with self._write() as doc:
            self._get(doc, 'sessions', session_id)
            existing = next((v for v in doc.results if v.id == result.id), None)
            if existing is not None and existing != result:
                raise ValueError('Result identities are immutable')
            if existing is None:
                doc.results.append(result)
            ids = doc.evidence.setdefault(session_id, [])
            if result.id not in ids:
                ids.append(result.id)

    def results(self, session_id):
        doc = self._read()
        ids = set(doc.evidence.get(session_id, []))
        return [v for v in doc.results if v.id in ids]

    def find_completed(self, fingerprint):
        return next((v for v in reversed(self._read().results) if v.fingerprint == fingerprint and self.verified(v)), None)

    def save_decision(self, decision):
        with self._write() as doc:
            doc.decisions.append(decision)

    def decisions(self, session_id):
        return [v for v in self._read().decisions if v.session_id == session_id]

    def event(self, session_id, kind, payload):
        with self._write() as doc:
            doc.events.append(Event(id=max((v.id for v in doc.events), default=0) + 1,
                                    session_id=session_id, kind=kind, timestamp=now(), payload=payload))

    def events(self, session_id, kind=None):
        return [v.model_dump() for v in self._read().events if v.session_id == session_id and (kind is None or v.kind == kind)]
