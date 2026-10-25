import hashlib
import io
import json
import sqlite3
import stat
import zipfile

import pytest

from slothlab.memory.bundles import export_bundle, import_bundle
from slothlab.memory.document import DocumentRepository
from slothlab.config import Config
from test_document_memory import seed, measured


def bundle(tmp_path):
    repo = DocumentRepository(tmp_path / 'source' / 'research.json')
    session, _, spec = seed(repo)
    artifact = tmp_path / 'observations.json'
    artifact.write_bytes(b'{"observed": [1, 2, 3]}')
    result = measured(spec, artifact_paths=[str(artifact)],
                      environment_metadata={'artifact_sha256': {str(artifact): hashlib.sha256(artifact.read_bytes()).hexdigest()}})
    repo.save_result(session.id, result)
    config = Config(model='test-only', db_path=str(repo.path), artifact_dir=str(tmp_path))
    repo.event(session.id, 'configuration', config.model_dump(mode='json'))
    repo.event(session.id, 'audit', {'api_key': 'never-export-this-secret'})
    return export_bundle(repo, session.id), result, session.id


def rewrite(data, change):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    change(files)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def test_guest_bundle_roundtrip_without_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('Guest attempted SQLite'))
    data, original, identity = bundle(tmp_path)
    assert b'never-export-this-secret' not in data
    repo, sid = import_bundle(data, tmp_path / 'imported')
    assert sid == identity
    restored = repo.results(sid)[0]
    assert restored.id == original.id and restored.fingerprint == original.fingerprint
    assert repo.verified(restored)
    assert restored.artifact_paths != original.artifact_paths
    config = Config.model_validate(repo.events(sid, 'configuration')[0]['payload'])
    assert config.db_path == str(repo.path)
    assert config.storage_backend == 'document'
    assert repo.events(sid, 'bundle_import')
    assert not list(tmp_path.rglob('*.sqlite*'))
    twice, twice_sid = import_bundle(export_bundle(repo, sid), tmp_path / 'twice')
    assert twice.results(twice_sid)[0].environment_metadata['bundle_origin'] == restored.environment_metadata['bundle_origin']


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'C:/drive', 'artifacts/../../escape', 'a\\b'])
def test_reject_archive_paths_before_writes(tmp_path, name):
    data, _, _ = bundle(tmp_path)
    data = rewrite(data, lambda files: files.update({name: b'bad'}))
    target = tmp_path / 'destination'
    with pytest.raises(ValueError, match='Unsafe archive path'):
        import_bundle(data, target)
    assert not target.exists()


def test_reject_symlink(tmp_path):
    data, _, _ = bundle(tmp_path)
    stream = io.BytesIO(data)
    with zipfile.ZipFile(stream, 'a') as archive:
        info = zipfile.ZipInfo('artifacts/link')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, '/etc/passwd')
    with pytest.raises(ValueError, match='Unsupported archive entry'):
        import_bundle(stream.getvalue(), tmp_path / 'destination')


def test_reject_tamper_and_zip_bomb(tmp_path):
    data, _, _ = bundle(tmp_path)
    tampered = rewrite(data, lambda files: files.update({'artifacts/000000.bin': b'changed'}))
    with pytest.raises(ValueError, match='hash or size mismatch'):
        import_bundle(tampered, tmp_path / 'destination')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('huge', b'0' * 2_000_000)
    with pytest.raises(ValueError, match='compression ratio'):
        import_bundle(stream.getvalue(), tmp_path / 'destination')
    assert not (tmp_path / 'destination').exists()


def test_manifest_schema_and_provenance_hash_tampering(tmp_path):
    data, _, _ = bundle(tmp_path)
    def change(files):
        manifest = json.loads(files['manifest.json'])
        manifest['document']['results'][0]['environment_metadata']['artifact_sha256'] = {'unlisted': '0' * 64}
        files['manifest.json'] = json.dumps(manifest).encode()
    with pytest.raises(ValueError, match='provenance'):
        import_bundle(rewrite(data, change), tmp_path / 'destination')
    def extra(files):
        manifest = json.loads(files['manifest.json'])
        manifest['execute_code'] = 'forbidden'
        files['manifest.json'] = json.dumps(manifest).encode()
    with pytest.raises(ValueError):
        import_bundle(rewrite(data, extra), tmp_path / 'destination')
    assert not (tmp_path / 'destination').exists()


def test_cross_session_reuse_is_explicitly_not_exported(tmp_path):
    repo = DocumentRepository(tmp_path / 'research.json')
    first, _, spec = seed(repo)
    second, _, _ = seed(repo)
    result = measured(spec)
    repo.save_result(first.id, result)
    repo.save_result(second.id, result)
    with pytest.raises(ValueError, match='another session'):
        export_bundle(repo, second.id)
    exported = export_bundle(repo, first.id)
    with zipfile.ZipFile(io.BytesIO(exported)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
    assert len(manifest['document']['sessions']) == 1
    assert manifest['document']['sessions'][0]['id'] == first.id


def test_real_science_artifacts_remain_verified_after_reopen(tmp_path, monkeypatch):
    from slothlab.experiments.executor import execute
    from slothlab.lazyloop.fingerprint import fingerprint
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('Guest attempted SQLite'))
    repo = DocumentRepository(tmp_path / 'research.json')
    session, _, spec = seed(repo)
    result = execute(spec, tmp_path / 'experiments', isolation='subprocess')
    assert result.status == 'COMPLETED', result.error_details
    repo.save_result(session.id, result)
    reopened, identity = import_bundle(export_bundle(repo, session.id), tmp_path / 'imported')
    restored = reopened.results(identity)[0]
    assert reopened.verified(restored)
    assert restored.metrics == result.metrics
    assert restored.fingerprint == fingerprint(spec)
    assert reopened.find_completed(fingerprint(spec)).id == result.id


def test_explicit_workspace_bundle_preserves_cross_session_cached_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('Guest attempted SQLite'))
    repo = DocumentRepository(tmp_path / 'research.json')
    first, first_hypothesis, spec = seed(repo)
    second, second_hypothesis, second_spec = seed(repo)
    artifact = tmp_path / 'source-observations.json'
    artifact.write_bytes(b'{"observations": [0, 1, 1, 0]}')
    result = measured(spec, artifact_paths=[str(artifact)], environment_metadata={
        'artifact_sha256': {str(artifact): hashlib.sha256(artifact.read_bytes()).hexdigest()}})
    repo.save_result(first.id, result)
    repo.save_result(second.id, result)
    for session in (first, second):
        repo.event(session.id, 'configuration', Config(model='test-only').model_dump(mode='json'))
        repo.event(session.id, 'ownership', {'original_session_id': session.id})
    data = export_bundle(repo, second.id, include_workspace=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['scope'] == 'workspace'
        assert len(manifest['artifacts']) == 1
        assert len(manifest['document']['results']) == 1
    reopened, selected = import_bundle(data, tmp_path / 'imported')
    assert selected == second.id
    assert {v.id for v in reopened.list_sessions()} == {first.id, second.id}
    assert reopened.get_spec(spec.id).hypothesis_id == first_hypothesis.id
    assert reopened.get_spec(second_spec.id).hypothesis_id == second_hypothesis.id
    restored = reopened.results(first.id)[0]
    assert restored == reopened.results(second.id)[0]
    assert restored.experiment_id == spec.id and restored.id == result.id
    assert restored.fingerprint == result.fingerprint and reopened.verified(restored)
    for session in (first, second):
        config = Config.model_validate(reopened.events(session.id, 'configuration')[0]['payload'])
        assert config.storage_backend == 'document' and config.db_path == str(reopened.path)
        assert reopened.events(session.id, 'ownership')[0]['payload']['original_session_id'] == session.id
        assert reopened.events(session.id, 'bundle_import')[0]['payload']['source_session_id'] == session.id
    assert not list(tmp_path.rglob('*.sqlite*'))


def test_session_scope_cannot_smuggle_additional_sessions(tmp_path):
    repo = DocumentRepository(tmp_path / 'research.json')
    first, _, _ = seed(repo)
    seed(repo)
    data = export_bundle(repo, first.id, include_workspace=True)
    def force_scope(files):
        manifest = json.loads(files['manifest.json'])
        manifest['scope'] = 'session'
        files['manifest.json'] = json.dumps(manifest).encode()
    with pytest.raises(ValueError, match='precisely'):
        import_bundle(rewrite(data, force_scope), tmp_path / 'destination')
    assert not (tmp_path / 'destination').exists()
