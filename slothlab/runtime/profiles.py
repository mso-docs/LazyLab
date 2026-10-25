"""Private local workspace profiles; browser profiles are convenience, not authentication."""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
from slothlab.runtime.atomic import atomic_json
from slothlab.schemas import now

TOKEN_PATTERN = re.compile(r'[A-Za-z0-9_-]{43}')

@dataclass(frozen=True)
class Profile:
    id: str
    display_name: str
    directory: Path
    token: str | None = field(default=None, repr=False)

    @property
    def db_path(self): return self.directory / 'research.sqlite'
    @property
    def artifact_dir(self): return self.directory / 'artifacts'
    @property
    def job_dir(self): return self.directory / 'jobs'

class LocalProfileStore:
    def __init__(self, root='artifacts/profiles'):
        self.root = Path(root).resolve()

    @staticmethod
    def _name(name):
        name = str(name).strip()
        if not name or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Choose a profile name between 1 and 80 printable characters.')
        return name

    def _create(self, identifier, name, token=None):
        name = self._name(name)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        directory = self.root / identifier
        directory.mkdir(mode=0o700)
        atomic_json(directory / 'profile.json', {'version': 1, 'id': identifier,
                    'display_name': name, 'created_at': now()})
        (directory / 'profile.json').chmod(0o600)
        return Profile(identifier, name, directory, token)

    def create(self, display_name):
        self._name(display_name)
        for _ in range(8):
            token = secrets.token_urlsafe(32)
            identifier = hashlib.sha256(token.encode()).hexdigest()
            try:
                return self._create(identifier, display_name, token)
            except FileExistsError:
                continue
        raise RuntimeError('Unable to allocate a unique profile.')

    def _read(self, identifier, token=None):
        directory = self.root / identifier
        if directory.is_symlink():
            raise ValueError('Profile directory must not be a symbolic link.')
        path = directory / 'profile.json'
        if not path.exists(): return None
        if path.is_symlink(): raise ValueError('Profile metadata must not be a symbolic link.')
        data = json.loads(path.read_text())
        if data.get('version') != 1 or data.get('id') != identifier:
            raise ValueError('Invalid profile metadata.')
        return Profile(identifier, self._name(data.get('display_name', '')), directory, token)

    def open(self, token):
        if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
            raise ValueError('Invalid browser profile credential.')
        return self._read(hashlib.sha256(token.encode()).hexdigest(), token)

    def for_identity(self, issuer, subject, display_name, server_secret):
        if not issuer or not subject or not isinstance(server_secret, str) or len(server_secret) < 32:
            raise ValueError('Account profiles require issuer, subject and a stable secret of at least 32 characters.')
        message = json.dumps([issuer, subject], separators=(',', ':')).encode()
        identifier = 'oidc-' + hmac.new(server_secret.encode(), message, hashlib.sha256).hexdigest()
        profile = self._read(identifier)
        if profile: return profile
        try: return self._create(identifier, display_name)
        except FileExistsError: return self._read(identifier)
