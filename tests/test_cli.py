from slothlab.cli import main
from slothlab.memory.repository import Repository


def test_init_creates_config_and_status_reports_unknown_session(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['init']) == 0
    assert (tmp_path/'configs/calibration.yaml').is_file()
    assert (tmp_path/'artifacts/slothlab.sqlite').is_file()
    assert main(['status','missing']) == 1
    assert 'unknown id' in capsys.readouterr().err


def test_run_requires_model_without_fake_fallback(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('OLLAMA_MODEL',raising=False)
    path=tmp_path/'config.yaml'
    path.write_text('{}')
    assert main(['run','--config',str(path)]) == 1
    assert 'Set OLLAMA_MODEL' in capsys.readouterr().err
    with Repository('artifacts/slothlab.sqlite') as repo:
        assert repo.list_sessions() == []


def test_direct_experiment_cli_persists_real_evidence_and_report(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['experiment','--seed','7']) == 0
    with Repository('artifacts/slothlab.sqlite') as repo:
        session = repo.list_sessions()[0]
        result = repo.results(session.id)[0]
        assert result.status == 'COMPLETED'
        assert result.metrics['delta_brier'] == result.metrics['corrected_brier']-result.metrics['baseline_brier']
        assert session.budget_consumed['model_calls'] == 0
        assert (tmp_path/'artifacts'/session.id/'reports/report.md').is_file()
