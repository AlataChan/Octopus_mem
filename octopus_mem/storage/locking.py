import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


def locked_update_json(
    path: Path,
    mutator: Callable[[Any], Any],
    *,
    default_factory: Callable[[], Any] = dict,
    lock_path: Path | None = None,
    validate_in: Callable[[Any], None] | None = None,
    validate_out: Callable[[Any], None] | None = None,
) -> Any:
    """Atomically apply ``mutator`` to the JSON at ``path``.

    Same as Phase 2, with optional validation inside the lock window.

    If ``validate_in`` is given, it runs on the loaded state before the
    mutator. If ``validate_out`` is given, it runs on the new state
    before the tempfile write. Both run **inside** the lock so a
    failed validation leaves the file untouched.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(lock_path) if lock_path else path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "a+") as lock_fp:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as fp:
                    current = json.load(fp)
            else:
                current = default_factory()

            if validate_in is not None:
                validate_in(current)

            new_state = mutator(current)

            if validate_out is not None:
                validate_out(new_state)

            fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_fp:
                    json.dump(new_state, tmp_fp, ensure_ascii=False, indent=2)
                    tmp_fp.flush()
                    os.fsync(tmp_fp.fileno())
                os.replace(tmp_name, path)
            except Exception:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise

            return new_state
        finally:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)


def read_json_validated(
    path: Path,
    *,
    validator: Callable[[Any], None] | None = None,
    lock_path: Path | None = None,
) -> Any:
    """Read JSON under a shared lock and optionally validate the result."""
    path = Path(path)
    lock_path = Path(lock_path) if lock_path else path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "a+") as lock_fp:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_SH)
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if validator is not None:
                validator(data)
            return data
        finally:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
