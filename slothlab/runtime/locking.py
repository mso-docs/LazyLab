"""Crash-released advisory locks for local single-host operation."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import os


class AlreadyRunningError(RuntimeError):
    pass


@contextmanager
def file_lock(path: Path, blocking=False):
    import fcntl
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise AlreadyRunningError('This investigation is already running in another process') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def session_lock(database, session_id):
    if str(database) == ':memory:':
        yield
        return
    database = Path(database).resolve()
    identity = hashlib.sha256(session_id.encode()).hexdigest()
    with file_lock(database.parent / f'.{database.name}.locks' / identity):
        yield
