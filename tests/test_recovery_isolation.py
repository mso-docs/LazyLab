from pathlib import Path
from unittest.mock import patch
import pytest
from slothlab.experiments.executor import execute,recover
from slothlab.experiments.isolation import command,isolation_status
from slothlab.schemas import ExperimentSpec


def test_committed_worker_manifest_recovers_without_reexecution(tmp_path):
    spec=ExperimentSpec(hypothesis_id='h',seed=5,rationale='Recovery test',parameters={'sample_size':100})
    result=execute(spec,tmp_path,isolation='subprocess')
    assert result.status=='COMPLETED',result.error_details
    assert recover(spec,tmp_path)==result
    Path(result.artifact_paths[0]).write_bytes(b'corrupted')
    assert recover(spec,tmp_path) is None


def test_incomplete_or_different_protocol_receipt_never_recovers(tmp_path):
    spec=ExperimentSpec(hypothesis_id='h',seed=5,rationale='Recovery test',parameters={'sample_size':100})
    assert recover(spec,tmp_path) is None
    execute(spec,tmp_path,isolation='subprocess')
    altered=spec.model_copy(update={'seed':6})
    assert recover(altered,tmp_path) is None


def test_required_isolation_fails_closed_when_namespaces_unavailable(tmp_path):
    spec=ExperimentSpec(hypothesis_id='h',seed=5,rationale='Isolation test')
    with patch('slothlab.experiments.isolation.isolation_status',return_value={'available':False,'reason':'disabled'}):
        result=execute(spec,tmp_path,isolation='bubblewrap')
        assert result.status=='FAILED'
        assert 'Required Bubblewrap' in result.error_details
        args,boundary=command(tmp_path,'auto')
        assert boundary['os_network_isolation'] is False
        assert boundary['fallback_reason']=='disabled'


def test_bubblewrap_command_has_private_network_and_minimal_mounts(tmp_path):
    with patch('slothlab.experiments.isolation.isolation_status',return_value={'available':True,'binary':'bwrap'}):
        args,boundary=command(tmp_path,'bubblewrap')
    assert '--unshare-all' in args
    assert '--cap-drop' in args
    assert boundary['os_filesystem_isolation']
    assert '--bind' in args and '/work' in args
    assert not any(args[i:i+3]==['--ro-bind','/','/'] for i in range(len(args)))
