from pathlib import Path
from slothlab.assets import asset_path
from slothlab.config import load_config
from slothlab.cli import main


def test_bundled_defaults_work_outside_checkout(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    config=load_config('configs/demo.yaml')
    assert config.objective.experiment_family=='prior_correction'
    suite=asset_path('benchmarks/objectives')
    assert len(list(suite.glob('*.yaml')))>=7
    assert list(suite.glob('*.replay.json'))
    assert asset_path('/missing/custom.yaml')==Path('/missing/custom.yaml')


def test_doctor_can_verify_core_without_inference(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['doctor','--skip-model'])==0
    assert '"ready": true' in capsys.readouterr().out
