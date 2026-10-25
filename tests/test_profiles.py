import hashlib
import json
import stat
import pytest
from slothlab.runtime.profiles import LocalProfileStore


def test_private_profile_roundtrip(tmp_path):
    store = LocalProfileStore(tmp_path/'profiles')
    profile = store.create('Ada')
    assert len(profile.token) == 43
    assert profile.id == hashlib.sha256(profile.token.encode()).hexdigest()
    assert store.open(profile.token) == profile
    assert profile.token not in repr(profile)
    assert profile.token not in (profile.directory/'profile.json').read_text()
    assert stat.S_IMODE(profile.directory.stat().st_mode) == 0o700
    assert stat.S_IMODE((profile.directory/'profile.json').stat().st_mode) == 0o600
    assert profile.db_path.parent == profile.artifact_dir.parent == profile.job_dir.parent
    assert not profile.db_path.exists()
    other = store.create('Ada')
    assert other.id != profile.id

@pytest.mark.parametrize('token', ['../etc/passwd', '', 'a'*42, 'a'*44, None, 'a'*42+'!'])
def test_invalid_credentials(tmp_path, token):
    with pytest.raises(ValueError): LocalProfileStore(tmp_path).open(token)


def test_missing_and_tampered_profiles(tmp_path):
    store = LocalProfileStore(tmp_path)
    assert store.open('a'*43) is None
    profile = store.create('Name')
    path = profile.directory/'profile.json'
    value = json.loads(path.read_text()); value['id'] = 'wrong'; path.write_text(json.dumps(value))
    with pytest.raises(ValueError): store.open(profile.token)


def test_account_identity_uses_issuer_subject_and_secret(tmp_path):
    store = LocalProfileStore(tmp_path)
    first = store.for_identity('https://issuer', 'subject', 'Ada', 'x'*32)
    assert store.for_identity('https://issuer', 'subject', 'Renamed', 'x'*32).id == first.id
    assert store.for_identity('https://other', 'subject', 'Ada', 'x'*32).id != first.id
    assert store.for_identity('https://issuer', 'different', 'Ada', 'x'*32).id != first.id
    assert store.for_identity('https://issuer', 'subject', 'Ada', 'y'*32).id != first.id
    with pytest.raises(ValueError): store.for_identity('issuer','subject','Ada','short')


def test_bridge_has_no_external_resources_or_query_secrets():
    from slothlab.ui.identity import BROWSER_JS
    assert 'localStorage.getItem' in BROWSER_JS
    assert 'localStorage.setItem' in BROWSER_JS
    assert 'setStateValue' in BROWSER_JS
    for forbidden in ('fetch(', 'XMLHttpRequest', 'location.', 'https://', 'innerHTML', 'document.cookie'):
        assert forbidden not in BROWSER_JS


def test_auth_is_optional_and_requires_complete_config(monkeypatch):
    import slothlab.ui.identity as identity
    monkeypatch.setattr(identity.st, 'secrets', {})
    assert identity.auth_settings() is None
    monkeypatch.setattr(identity.st, 'secrets', {'auth': {'redirect_uri':'http://localhost/oauth2callback',
        'cookie_secret':'x'*32, 'client_id':'id', 'client_secret':'secret', 'server_metadata_url':'https://issuer/config'}})
    assert identity.auth_settings() == {'namespace_secret':'x'*32}


def test_token_collision_retries_without_overwriting(tmp_path, monkeypatch):
    import slothlab.runtime.profiles as profiles
    store = LocalProfileStore(tmp_path)
    monkeypatch.setattr(profiles.secrets, 'token_urlsafe', lambda _: 'a'*43)
    first = store.create('First')
    values = iter(['a'*43, 'b'*43])
    monkeypatch.setattr(profiles.secrets, 'token_urlsafe', lambda _: next(values))
    second = store.create('Second')
    assert first.id != second.id
    assert store.open(first.token).display_name == 'First'


def test_identity_controls_guest_create_and_forget(tmp_path):
    from streamlit.testing.v1 import AppTest
    script = '''from slothlab.ui.identity import render_identity_controls
from slothlab.runtime.profiles import LocalProfileStore
import streamlit as st
context = render_identity_controls(LocalProfileStore(ROOT), ROOT+'/legacy.sqlite', ROOT+'/artifacts', ROOT+'/jobs')
st.write(context.mode)
'''.replace('ROOT', repr(str(tmp_path)))
    app = AppTest.from_string(script).run()
    assert not app.exception
    app.selectbox(key='history_mode').set_value('Guest').run()
    assert not app.exception
    assert not list(tmp_path.rglob('*.sqlite'))
    app.selectbox(key='history_mode').set_value('Browser profile').run()
    app.text_input[0].set_value('Ada').run()
    app.button[0].click().run()
    assert not app.exception
    assert len(list(tmp_path.rglob('profile.json'))) == 1
    app.button[0].click().run()
    assert not app.exception
    # Forgetting removes access rather than deleting scientific records.
    assert len(list(tmp_path.rglob('profile.json'))) == 1


def test_configured_account_hides_legacy_history_until_login(tmp_path):
    from streamlit.testing.v1 import AppTest
    script = '''import slothlab.ui.identity as identity
from slothlab.runtime.profiles import LocalProfileStore
identity.auth_settings = lambda: {'namespace_secret': 'x'*32}
context = identity.render_identity_controls(LocalProfileStore(ROOT), ROOT+'/legacy.sqlite', ROOT+'/a', ROOT+'/jobs')
import streamlit as st
st.write(context.storage_backend)
'''.replace('ROOT', repr(str(tmp_path)))
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert app.selectbox(key='history_mode').options == ['Account', 'Guest']
    assert app.markdown[-1].value == 'document'
    assert not list(tmp_path.rglob('*.sqlite'))
