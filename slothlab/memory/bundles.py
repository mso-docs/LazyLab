"""Portable, bounded research archives. Archive names never become disk paths."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from slothlab.memory.document import Document, DocumentRepository, MAX_DOCUMENT_BYTES
from slothlab.runtime.atomic import atomic_json

MAX_BUNDLE_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_FILES = 2048


class Artifact(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    member: str
    result_id: str
    original_path: str
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    size: int = Field(ge=0, le=MAX_UNCOMPRESSED_BYTES)


class Manifest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    format: str = 'slothlab-research-bundle'
    version: int = 1
    session_id: str
    scope: Literal['session', 'workspace'] = 'session'
    document: Document
    artifacts: list[Artifact]


def _safe_member(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or '\x00' in name or path.is_absolute() or ':' in name or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe archive path')
    return name


def _scrub(value):
    """Never export credentials accidentally placed in audit/config metadata."""
    if isinstance(value, dict):
        return {key: ('[redacted]' if ('/' not in str(key) and '\\' not in str(key) and re.search(r'(?i)(password|secret|authorization|api[_-]?key|credential|access[_-]?token|refresh[_-]?token|auth[_-]?token|bearer[_-]?token|^token$)', str(key))) else _scrub(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str) and value.startswith(('http://', 'https://')):
        from urllib.parse import urlsplit, urlunsplit
        parsed = urlsplit(value)
        # Endpoint query strings may carry credentials; Ollama endpoints need none.
        return urlunsplit((parsed.scheme, parsed.netloc.rsplit('@', 1)[-1], parsed.path, '', ''))
    return value


def export_bundle(repo, session_id: str, *, include_workspace: bool = False) -> bytes:
    """Export one session, or explicitly include the workspace's entire history."""
    selected = repo.get_session(session_id)
    sessions = repo.list_sessions() if include_workspace else [selected]
    objectives, hypotheses, specs, measurements = {}, {}, {}, {}
    evidence, decisions, events = {}, [], []
    for session in sessions:
        objectives[session.objective_id] = repo.get_objective(session.objective_id)
        hypotheses.update((v.id, v) for v in repo.hypotheses(session.id))
        specs.update((v.id, v) for v in repo.specs(session.id))
        session_results = repo.results(session.id)
        measurements.update((v.id, v) for v in session_results)
        evidence[session.id] = [v.id for v in session_results]
        decisions.extend(repo.decisions(session.id))
        events.extend(repo.events(session.id))
    results = list(measurements.values())
    if any(v.experiment_id not in specs for v in results):
        raise ValueError('This session reuses another session’s evidence. Export all workspace history to preserve its original provenance.')
    document = Document(objectives=list(objectives.values()), sessions=sessions,
                        hypotheses=list(hypotheses.values()), specs=list(specs.values()), results=results,
                        evidence=evidence, decisions=decisions, events=events).check()
    # Scrub only freeform metadata; schema-bound token budgets remain numeric.
    for event in document.events:
        event.payload = _scrub(event.payload)
    for result in document.results:
        result.environment_metadata = _scrub(result.environment_metadata)
    artifacts = []
    payloads = {}
    total = 0
    for result in results:
        hashes = result.environment_metadata.get('artifact_sha256', {})
        if not isinstance(hashes, dict):
            raise ValueError('Invalid artifact hash metadata')
        paths = list(dict.fromkeys([*result.artifact_paths, *hashes]))
        for path in paths:
            source = Path(path)
            if source.is_symlink() or not source.is_file():
                raise ValueError('Research artifact is missing or is a symbolic link')
            size = source.stat().st_size
            total += size
            if total > MAX_UNCOMPRESSED_BYTES or len(artifacts) >= MAX_FILES - 1:
                raise ValueError('Research artifacts exceed archive limits')
            with source.open('rb') as handle:
                data = handle.read(MAX_UNCOMPRESSED_BYTES + 1)
            total += len(data) - size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError('Research artifacts exceed archive limits')
            digest = hashlib.sha256(data).hexdigest()
            if path in hashes and digest != hashes[path]:
                raise ValueError('Research artifact hash mismatch')
            member = f'artifacts/{len(artifacts):06d}.bin'
            artifacts.append(Artifact(member=member, result_id=result.id, original_path=path, sha256=digest, size=len(data)))
            payloads[member] = data
    manifest = Manifest(session_id=session_id, scope='workspace' if include_workspace else 'session', document=document, artifacts=artifacts)
    manifest_data = manifest.model_dump_json().encode()
    if len(manifest_data) > MAX_DOCUMENT_BYTES:
        raise ValueError('Research manifest exceeds size limit')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('manifest.json', manifest_data)
        for name, data in payloads.items():
            archive.writestr(name, data)
    data = stream.getvalue()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError('Research archive exceeds size limit')
    return data


def import_bundle(data: bytes, workspace: Path) -> tuple[DocumentRepository, str]:
    """Validate fully, then create a fresh isolated folder beneath workspace."""
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError('Research archive exceeds size limit')
    payloads = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            names = [v.filename for v in infos]
            if len(infos) > MAX_FILES or len(set(names)) != len(names):
                raise ValueError('Duplicate or excessive archive entries')
            total = 0
            for item in infos:
                _safe_member(item.filename)
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode) or item.is_dir() or item.flag_bits & 1:
                    raise ValueError('Unsupported archive entry')
                total += item.file_size
                if total > MAX_UNCOMPRESSED_BYTES or item.file_size > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError('Research archive exceeds expanded size limit')
                if item.file_size > max(item.compress_size, 1) * 1000:
                    raise ValueError('Research archive compression ratio exceeds limit')
            if 'manifest.json' not in names:
                raise ValueError('Missing research manifest')
            if archive.getinfo('manifest.json').file_size > MAX_DOCUMENT_BYTES:
                raise ValueError('Research manifest exceeds size limit')
            manifest_bytes = archive.read('manifest.json')
            json.loads(manifest_bytes, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
            manifest = Manifest.model_validate_json(manifest_bytes)
            if manifest.format != 'slothlab-research-bundle' or manifest.version != 1:
                raise ValueError('Unsupported research archive format')
            manifest.document.check()
            session_ids = {v.id for v in manifest.document.sessions}
            if manifest.session_id not in session_ids:
                raise ValueError('Archive is missing its declared session')
            if manifest.scope == 'session' and len(session_ids) != 1:
                raise ValueError('Session archive must contain precisely its declared session')
            if {v.member for v in manifest.artifacts} | {'manifest.json'} != set(names):
                raise ValueError('Unexpected or missing artifact entries')
            if len({v.member for v in manifest.artifacts}) != len(manifest.artifacts):
                raise ValueError('Duplicate artifact entries')
            result_ids = {v.id for v in manifest.document.results}
            original_pairs = set()
            for artifact in manifest.artifacts:
                if artifact.result_id not in result_ids or (artifact.result_id, artifact.original_path) in original_pairs:
                    raise ValueError('Invalid artifact provenance')
                original_pairs.add((artifact.result_id, artifact.original_path))
                content = archive.read(artifact.member)
                if len(content) != artifact.size or hashlib.sha256(content).hexdigest() != artifact.sha256:
                    raise ValueError('Research artifact hash or size mismatch')
                payloads[artifact.member] = content
            for result in manifest.document.results:
                hashes = result.environment_metadata.get('artifact_sha256', {})
                if not isinstance(hashes, dict):
                    raise ValueError('Invalid artifact hash metadata')
                required = set(result.artifact_paths) | set(hashes)
                actual = {v.original_path for v in manifest.artifacts if v.result_id == result.id}
                if actual != required:
                    raise ValueError('Artifact manifest does not match result provenance')
                for artifact in manifest.artifacts:
                    if artifact.result_id == result.id and artifact.original_path in hashes and hashes[artifact.original_path] != artifact.sha256:
                        raise ValueError('Artifact hashes disagree with scientific provenance')
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ValueError('Invalid research archive') from exc
    # No filesystem mutations occur before complete structural and content verification.
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='research-', dir=workspace)).resolve()
    try:
        artifact_dir = root / 'artifacts'
        artifact_dir.mkdir()
        paths = {}
        for index, artifact in enumerate(manifest.artifacts):
            suffix = Path(artifact.original_path).suffix
            suffix = suffix if re.fullmatch(r'\.[a-zA-Z0-9]{1,12}', suffix) else '.bin'
            destination = artifact_dir / f'{index:06d}{suffix}'
            destination.write_bytes(payloads[artifact.member])
            paths[(artifact.result_id, artifact.original_path)] = str(destination)
        for result in manifest.document.results:
            original_paths = list(result.artifact_paths)
            original_hashes = dict(result.environment_metadata.get('artifact_sha256', {}))
            result.artifact_paths = [paths[(result.id, p)] for p in original_paths]
            result.environment_metadata['artifact_sha256'] = {paths[(result.id, a.original_path)]: a.sha256 for a in manifest.artifacts if a.result_id == result.id}
            # Keep source paths and hashes as audit metadata, never executable locations.
            result.environment_metadata.setdefault('bundle_origin', {'artifact_paths': original_paths, 'artifact_sha256': original_hashes})
        path = root / 'research.json'
        original_configurations = []
        for event in manifest.document.events:
            if event.kind == 'configuration' and isinstance(event.payload, dict):
                original_configurations.append({'session_id': event.session_id, 'configuration': event.payload.copy()})
                event.payload.update(db_path=str(path), artifact_dir=str(artifact_dir), storage_backend='document')
        manifest.document.check()
        atomic_json(path, manifest.document.model_dump(mode='json'))
        repo = DocumentRepository(path)
        for session in manifest.document.sessions:
            repo.event(session.id, 'bundle_import', {'source_session_id': session.id, 'scope': manifest.scope,
                       'archive_sha256': hashlib.sha256(data).hexdigest(),
                       'original_configurations': [v for v in original_configurations if v['session_id'] == session.id]})
        return repo, manifest.session_id
    except Exception:
        import shutil
        shutil.rmtree(root)
        raise
