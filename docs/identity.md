# History, browser profiles and optional sign-in

The sidebar offers three modes without any account setup:

- **Workspace** keeps the existing research database and artifact paths. Existing history remains available.
- **Guest** writes research documents and artifacts to a temporary workspace, without SQL. Export a research bundle before leaving; a new browser session gets a new guest workspace. Temporary files can remain on the app host until its temporary directory is cleaned.
- **Browser profile** creates a separate server-side research workspace and remembers an opaque credential in this browser's local storage. Names are labels, not passwords. Reloading on the same origin restores the profile; another browser, port, hostname or device does not share it. Clearing browser data or choosing **Forget browser profile** removes the remembered credential, without deleting research files. Export bundles before doing so.

Appearance preferences are also stored in local storage. If browser storage is blocked, the application remains usable with session-only preferences. No CDN or external storage service is used. Profile credentials are never placed in URLs or rendered as text. Keep browser extensions and scripts on the app origin trusted: local storage is readable by same-origin JavaScript.

Browser profiles are a convenience for a trusted local installation, not a network authentication or OS security boundary. Keep the application bound to loopback. Profile directories use mode 0700 and profile metadata uses 0600. Research runs and artifacts remain on the app host. This is not a hardened public multi-tenant service.

## Optional real account sign-in

Streamlit's built-in OIDC login is supported when an operator supplies a complete default provider in `.streamlit/secrets.toml`. No login button is shown without configuration. Once configured, the sidebar offers only Account and Guest: anonymous visitors cannot select the legacy shared workspace or browser profiles. Before sign-in, research uses an isolated guest document workspace. Install Streamlit's auth extra (`pip install '.[auth]'` from this repository) for provider login. Register your own application with an OIDC provider, including the exact redirect URI, and set:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS"
client_id = "YOUR_REGISTERED_CLIENT_ID"
client_secret = "YOUR_PROVIDER_CLIENT_SECRET"
server_metadata_url = "YOUR_PROVIDER_OPENID_CONFIGURATION_URL"

[slothlab_identity]
namespace_secret = "A_DIFFERENT_STABLE_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS"
```

Keep secrets out of version control. The account workspace is derived from an HMAC of the verified issuer and subject claims, not email or display name. Keep `namespace_secret` stable: changing it selects a new account workspace. The optional namespace secret defaults to the cookie secret. Sign-in identifies an account on this installation; it does not synchronize research files between independently deployed app servers. Account tokens with an expired `exp` claim cannot select account history and must sign out and sign in again.

The implementation uses the documented [Streamlit v2 component API](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component) and [Streamlit user claims](https://docs.streamlit.io/develop/api-reference/user/st.user). Provider registration, real login and public deployment are operator tasks; no external login was performed during development.
