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
) -> Any:
    """Atomically apply ``mutator`` to the JSON at ``path``.

    Holds ``fcntl.flock(LOCK_EX)`` for the **entire** read-modify-write
    window. No public path lets a caller read outside the lock and write
    inside it — that was the v2 bug.

    Steps (all inside one exclusive lock):
        1. Open the lockfile (created if absent) and acquire ``LOCK_EX``.
        2. Read the current JSON from ``path`` if it exists, else ``default_factory()``.
        3. Call ``mutator(current)`` to compute the new state.
        4. Write the new state to a sibling tempfile in the same directory
           so ``os.replace`` is atomic on the same filesystem.
        5. ``fsync`` the tempfile.
        6. ``os.replace`` the tempfile into ``path``.
        7. Release the lock when the lockfile is closed.

    Returns the new state, in case the caller wants to log it.

    Notes:
        - The same-directory tempfile is mandatory: ``os.replace`` is only
          atomic within a filesystem, and ``tempfile.gettempdir()`` is often
          a different mount.
        - The mutator MUST be a pure function of its input. It must not
          re-read ``path``, must not call ``locked_update_json`` recursively
          on the same path, and must not raise without leaving the file
          unchanged. (If it raises, ``os.replace`` never runs, the tempfile
          is unlinked, and the original is untouched.)
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

            new_state = mutator(current)

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
