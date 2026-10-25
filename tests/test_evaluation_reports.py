from test_memory import setup,result_for
from slothlab.memory.repository import Repository
from slothlab.reporting.generator import report_data,generate_report


def test_report_resource_telemetry_missing_is_unknown(tmp_path):
    with Repository(tmp_path/'resources.sqlite') as repo:
        session,_,spec=setup(repo)
        result=result_for(spec)
        repo.save_result(session.id,result)
        data=report_data(repo,session.id)
        assert data['telemetry']['scientific_cpu_seconds'] is None
        assert data['telemetry']['peak_memory_bytes'] is None


def test_html_and_csv_exports_preserve_actual_measurements_and_escape_model_text(tmp_path):
    with Repository(tmp_path/'export.sqlite') as repo:
        session,h,spec=setup(repo)
        from slothlab.schemas import uid
        h=h.model_copy(update={'id':uid(),'statement':'<script>malicious()</script>'})
        repo.save_hypothesis(h)
        result=result_for(spec)
        repo.save_result(session.id,result)
        report=generate_report(repo,session.id,tmp_path/'artifacts')
        html=report.with_suffix('.html').read_text()
        assert '<script>malicious()' not in html
        assert '&lt;script&gt;' in html
        assert result.id in html
        assert report.with_name('experiments.csv').is_file()
        assert '-0.1' in report.with_name('experiments.csv').read_text()


def test_interrupted_execution_has_unknown_resource_and_runtime_totals(tmp_path):
    with Repository(tmp_path/'interrupted.sqlite') as repo:
        session,_,_=setup(repo)
        session.budget_consumed['experiments']=1
        repo.save_session(session)
        telemetry=report_data(repo,session.id)['telemetry']
        assert telemetry['execution_seconds'] is None
        assert telemetry['scientific_cpu_seconds'] is None
        assert telemetry['peak_memory_bytes'] is None
