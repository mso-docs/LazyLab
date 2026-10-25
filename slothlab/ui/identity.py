"""Browser-scoped preferences and optional configured OIDC identity controls."""
from dataclasses import dataclass
from pathlib import Path
import tempfile
import importlib.util
import time
import streamlit as st
from slothlab.runtime.profiles import LocalProfileStore, TOKEN_PATTERN

# Static trusted code only. localStorage is same-origin; no fetch, CDN or URL secrets.
BROWSER_JS = """
export default function({data, setStateValue}) {
 const key = 'slothlab.browser.v1';
 let value = {}; let available = true;
 try {
   value = JSON.parse(localStorage.getItem(key) || '{}');
   if (!value || typeof value !== 'object' || Array.isArray(value)) value = {};
   if (data && data.desired) {
     value = {...value, ...data.desired};
     if (value.token === null) delete value.token;
     localStorage.setItem(key, JSON.stringify(value));
   }
 } catch (_) { available = false; }
 const safe = {browser_ready:true, storage_available:available,
   theme:['System','Light','Dark'].includes(value.theme) ? value.theme : 'System',
   mode:['Workspace','Guest','Browser profile','Account'].includes(value.mode) ? value.mode : 'Workspace'};
 const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
 safe.system_dark = media ? media.matches : false;
 if (typeof value.token === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value.token)) safe.token=value.token;
 if (JSON.stringify(data && data.observed) !== JSON.stringify(safe)) setStateValue('preferences',safe);
 if (media && media.addEventListener) {
   const changed = event => setStateValue('preferences', {...safe, system_dark:event.matches});
   media.addEventListener('change', changed);
   return () => media.removeEventListener('change', changed);
 }
}
"""
_bridge = st.components.v2.component('slothlab_browser_preferences', js=BROWSER_JS)

def browser_preferences(desired=None):
    """Read/write origin-scoped preferences; no handshake is required to render."""
    result = _bridge(key='slothlab_browser_preferences', data={'desired': desired, 'observed': st.session_state.get('_identity_browser_observed', {})},
                     default={'preferences': {}}, on_preferences_change=lambda: None, height=0)
    value = result.preferences or {}
    st.session_state['_identity_browser_observed'] = dict(value)
    safe = {k: value[k] for k in ('browser_ready', 'storage_available', 'theme', 'mode','system_dark') if k in value}
    if isinstance(value.get('token'), str) and TOKEN_PATTERN.fullmatch(value['token']):
        safe['token'] = value['token']
    return safe

@dataclass(frozen=True)
class IdentityContext:
    mode: str
    db_path: Path
    artifact_dir: Path
    job_dir: Path
    storage_backend: str
    profile_label: str
    theme: str
    workspace_id: str

def auth_settings():
    """Only offer login with a complete operator-supplied default OIDC provider."""
    try:
        auth = dict(st.secrets.get('auth', {}))
        identity = dict(st.secrets.get('slothlab_identity', {}))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return None
    required = ('redirect_uri', 'cookie_secret', 'client_id', 'client_secret', 'server_metadata_url')
    if not all(auth.get(k) for k in required): return None
    secret = identity.get('namespace_secret', auth['cookie_secret'])
    if not isinstance(secret, str) or len(secret) < 32: return None
    return {'namespace_secret': secret}

def _queue_preferences():
    st.session_state['_identity_browser_write'] = {
        'mode': st.session_state.get('history_mode', 'Workspace'),
        'theme': st.session_state.get('appearance_theme', 'System')}

def render_identity_controls(store: LocalProfileStore, default_db_path, default_artifact_dir, default_job_dir):
    pending = st.session_state.pop('_identity_browser_write', None)
    preferences = browser_preferences(pending)
    modes = ['Workspace', 'Guest', 'Browser profile']
    auth = auth_settings()
    if auth: modes = ['Account', 'Guest']
    if st.session_state.get('history_mode') not in modes:
        st.session_state['history_mode'] = modes[0]
    if '_identity_initialized' not in st.session_state and preferences.get('browser_ready'):
        remembered = preferences.get('mode', 'Workspace')
        st.session_state['history_mode'] = remembered if remembered in modes else modes[0]
        st.session_state['appearance_theme'] = preferences.get('theme', 'System')
        st.session_state['_identity_initialized'] = True
    mode = st.sidebar.selectbox('History mode', modes, key='history_mode', on_change=_queue_preferences)
    theme = st.sidebar.selectbox('Appearance', ['System', 'Light', 'Dark'], key='appearance_theme', on_change=_queue_preferences)
    desired = {'mode': mode, 'theme': theme}
    if any(preferences.get(k) != v for k, v in desired.items()) and preferences.get('browser_ready'):
        st.session_state['_identity_browser_write'] = desired
    if preferences.get('browser_ready') and not preferences.get('storage_available'):
        st.sidebar.caption('Browser storage is unavailable. Preferences last for this app session only.')
    if mode == 'Guest':
        if '_guest_directory' not in st.session_state:
            st.session_state['_guest_directory'] = tempfile.mkdtemp(prefix='slothlab-guest-')
        directory = Path(st.session_state['_guest_directory'])
        st.sidebar.caption('Guest history uses files, with no SQL database. Download a research bundle to keep your work.')
        return IdentityContext('guest', directory/'research.json', directory/'artifacts', directory/'jobs',
                               'document', 'Guest', theme, directory.name)
    profile = None
    if mode == 'Browser profile':
        token = None if st.session_state.get('_browser_profile_forgotten') else (st.session_state.get('_browser_profile_token') or preferences.get('token'))
        if token:
            try: profile = store.open(token)
            except (ValueError, OSError): pass
        if profile:
            st.sidebar.text(f'Browser profile: {profile.display_name}')
            if st.sidebar.button('Forget browser profile'):
                st.session_state.pop('_browser_profile_token', None)
                st.session_state['_identity_browser_write'] = {'token': None, 'mode': 'Workspace'}
                st.session_state['_browser_profile_forgotten'] = True
                st.rerun()
        else:
            name = st.sidebar.text_input('Profile name', max_chars=80)
            if st.sidebar.button('Create browser profile', disabled=not name.strip()):
                profile = store.create(name)
                st.session_state.pop('_browser_profile_forgotten', None)
                st.session_state['_browser_profile_token'] = profile.token
                st.session_state['_identity_browser_write'] = {**desired, 'token': profile.token}
                st.rerun()
        st.sidebar.caption('A remembered profile on this browser, not an authenticated account. Clearing browser data removes access; export bundles first.')
    if mode == 'Account' and auth:
        user = st.user.to_dict()
        if not user.get('is_logged_in'):
            available = importlib.util.find_spec('authlib') is not None
            if not available:
                st.sidebar.info('Install slothlab[auth] on the app host to enable account sign-in.')
            if st.sidebar.button('Sign in with configured provider', disabled=not available): st.login()
        elif user.get('exp') and float(user['exp']) <= time.time():
            st.sidebar.warning('Your account session has expired. Sign in again.')
            if st.sidebar.button('Sign out'): st.logout()
        elif user.get('iss') and user.get('sub'):
            profile = store.for_identity(user['iss'], user['sub'], user.get('name') or 'Account', auth['namespace_secret'])
            st.sidebar.text(f'Signed in: {profile.display_name}')
            if st.sidebar.button('Sign out'): st.logout()
        else:
            st.sidebar.error('Provider did not supply issuer and subject claims.')
    if profile:
        return IdentityContext('account' if mode == 'Account' else 'profile', profile.db_path,
            profile.artifact_dir, profile.job_dir, 'sqlite', profile.display_name, theme, profile.id)
    if mode != 'Workspace':
        if '_guest_directory' not in st.session_state:
            st.session_state['_guest_directory'] = tempfile.mkdtemp(prefix='slothlab-guest-')
        directory = Path(st.session_state['_guest_directory'])
        label = 'Create a browser profile' if mode == 'Browser profile' else 'Sign in to account history'
        st.sidebar.caption('Until then, research uses your isolated guest workspace.')
        return IdentityContext('guest', directory/'research.json', directory/'artifacts', directory/'jobs',
                               'document', label, theme, directory.name)
    return IdentityContext('workspace', Path(default_db_path), Path(default_artifact_dir), Path(default_job_dir),
                           'sqlite', 'Workspace', theme, 'workspace')
