"""Scientific workflows must remain functional with SQLite entirely prohibited."""
import json
from pathlib import Path
from unittest.mock import patch
from slothlab.config import Config
from slothlab.memory.factory import open_repository
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.evaluation.benchmark import run_benchmark
from test_agent import ScriptedResearchClient,candidate
from slothlab.schemas import Budget


def test_document_agent_executes_reuses_and_reports_without_database(tmp_path):
    config=Config(db_path=str(tmp_path/'research.json'),storage_backend='document',artifact_dir=str(tmp_path/'artifacts'),budget=Budget(max_rounds=3,max_tokens=100000,wall_seconds=60),execution_isolation='subprocess')
    with patch('sqlite3.connect',side_effect=AssertionError('No SQL allowed')):
        with open_repository(config.db_path,config.storage_backend) as repo:
            session=ResearchAgent(repo,ScriptedResearchClient([[candidate(1)],[candidate(1)],[candidate(2)]]),config).create()
            assert session.budget_consumed['experiments']==2
            assert session.budget_consumed['cache_hits']==1
            from slothlab.reporting.generator import generate_report
            path=generate_report(repo,session.id,config.artifact_dir)
            assert path.is_file()
    assert not list(tmp_path.rglob('*.sqlite*'))


def test_guest_replay_benchmark_uses_json_memory_for_all_arms(tmp_path):
    suite=tmp_path/'suite';suite.mkdir()
    (suite/'small.yaml').write_text('budget:\n  max_experiments: 1\n  max_rounds: 1\n  wall_seconds: 60\nobjective:\n  permitted_parameters:\n    sample_size: [100]\n')
    with patch('sqlite3.connect',side_effect=AssertionError('No SQL allowed')):
        path=run_benchmark(suite,tmp_path/'comparison',use_replay=True,config_overrides={'storage_backend':'document','execution_isolation':'subprocess'})
    data=json.loads(path.read_text())
    assert data['complete'] and data['failed_runs']==0
    assert len(data['runs'])==3
    assert all(row['db_path'].endswith('memory.json') for row in data['runs'])
    assert not list(tmp_path.rglob('*.sqlite*'))


def test_document_reference_grid_is_portable_without_sqlite(tmp_path):
    from slothlab.evaluation.reference import generate_reference_grid,load_reference_grid
    from slothlab.schemas import Parameters,ResearchObjective
    config=Config(storage_backend='document',objective=ResearchObjective(permitted_parameters={k:[v] for k,v in Parameters(sample_size=100).model_dump().items()}),budget=Budget(max_experiments=3,wall_seconds=60),execution_isolation='subprocess')
    with patch('sqlite3.connect',side_effect=AssertionError('No SQL allowed')):
        path=generate_reference_grid(config,tmp_path/'reference',max_conditions=1,seeds_per_condition=3)
        data=load_reference_grid(path)
    assert data['storage_backend']=='document'
    assert data['conditions'][0]['completed']==3
    assert not list(tmp_path.rglob('*.sqlite*'))
