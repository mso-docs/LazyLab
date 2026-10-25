"""Choose durable SQLite or a database-free portable JSON research document."""
from pathlib import Path


def open_repository(path: str | Path, backend: str = 'sqlite'):
    if backend=='document':
        from slothlab.memory.document import DocumentRepository
        return DocumentRepository(path)
    if backend=='sqlite':
        from slothlab.memory.repository import Repository
        return Repository(path)
    raise ValueError('Unknown research storage backend')
