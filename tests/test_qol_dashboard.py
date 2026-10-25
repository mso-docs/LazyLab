"""Quality-of-life integration tests: real UI, isolated histories, no SQL guests."""
from pathlib import Path
from unittest.mock import patch
from test_dashboard import ui_env,run_app,button,text
from slothlab.config import Config
from slothlab.memory.document import DocumentRepository
from slothlab.schemas import ResearchObjective,ResearchSession


def test_theme_switch_is_session_scoped_and_learn_center_has_real_video(ui_env):
    app=run_app()
    app.selectbox(key='appearance_theme').set_value('Dark').run()
    assert not app.exception
    assert app.selectbox(key='appearance_theme').value=='Dark'
    assert any('color-scheme:dark' in element.value for element in app.markdown)
    assert any(tab.label=='Learn & help' for tab in app.tabs)
    assert any('84-second' in item.value for item in app.caption)


def test_guest_mode_never_opens_sqlite_and_launches_document_job(ui_env):
    _,jobs=ui_env
    app=run_app()
    with patch('sqlite3.connect',side_effect=AssertionError('Guest must not open SQL')):
        app.selectbox(key='history_mode').set_value('Guest').run()
        assert not app.exception
        assert not any(item.label=='Research memory' for item in app.text_input)
        text(app,'Ollama model').set_value('test-model')
        button(app,'Start investigation').click().run()
    assert not app.exception
    assert jobs.launched[-1].storage_backend=='document'
    assert jobs.launched[-1].db_path.endswith('research.json')


def test_history_switch_clears_other_workspace_form_state(ui_env):
    app=run_app()
    text(app,'Investigation title').set_value('Private research title').run()
    app.selectbox(key='history_mode').set_value('Guest').run()
    assert not app.exception
    assert text(app,'Investigation title').value!='Private research title'


def test_imported_guest_requires_review_before_resume(ui_env):
    _,jobs=ui_env
    app=run_app()
    app.selectbox(key='history_mode').set_value('Guest').run()
    root=Path(app.session_state['_guest_directory'])
    with DocumentRepository(root/'research.json') as repo:
        objective=ResearchObjective(title='Imported history')
        repo.save_objective(objective)
        session=ResearchSession(objective_id=objective.id,model_name='test',state='REPLANNING')
        repo.save_session(session)
        config=Config(objective=objective,model='test',db_path=str(repo.path),storage_backend='document')
        repo.event(session.id,'configuration',config.model_dump(mode='json'))
        repo.event(session.id,'bundle_import',{'source_session_id':session.id})
    with patch('sqlite3.connect',side_effect=AssertionError('Guest must not open SQL')):
        app.run()
        assert not app.exception
        assert button(app,'Resume investigation').disabled
        app.checkbox(key='review_import_'+session.id).check().run()
        button(app,'Resume investigation').click().run()
    assert not app.exception
    assert jobs.resumed[-1][0].storage_backend=='document'
    assert jobs.resumed[-1][1]==session.id


def test_configured_auth_never_exposes_legacy_workspace_to_anonymous_user(ui_env):
    tmp_path,_=ui_env
    from test_dashboard import saved_session
    saved_session(tmp_path/'memory.sqlite')
    with patch('slothlab.ui.identity.auth_settings',return_value={'namespace_secret':'x'*32}),patch('sqlite3.connect',side_effect=AssertionError('Anonymous must not read legacy history')):
        app=run_app()
    assert not app.exception
    assert app.selectbox(key='history_mode').options==['Account','Guest']
    assert not any(item.label=='Research memory' for item in app.text_input)
    assert not any(item.value=='Dashboard test objective' for item in app.subheader)
