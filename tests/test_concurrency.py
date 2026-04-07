import json
import multiprocessing as mp
from pathlib import Path

from octopus_mem import MemoryManager


def _worker_distinct(args):
    base_path, i = args
    mm = MemoryManager(base_path=base_path)
    mm.store_memory(f"entry {i} unique-{i}", memory_type="daily", skill_name="dev")


def test_concurrent_store_does_not_corrupt_index(tmp_path):
    """Catches torn JSON / partial writes."""
    with mp.Pool(8) as pool:
        pool.map(_worker_distinct, [(str(tmp_path), i) for i in range(50)])

    index_path = Path(tmp_path) / "memory" / "skill_indexes" / "dev.index.json"
    index = json.loads(index_path.read_text())  # raises if torn JSON
    assert "memory_entries" in index


def test_concurrent_store_does_not_lose_updates(tmp_path):
    """Catches lost updates — the v2 bug Codex round-2 caught.

    With 50 distinct workers each appending one entry, the final index
    must contain exactly 50 entries. If the lock window only covers the
    write phase (not the read), some workers will read a stale state and
    overwrite a sibling's append, producing fewer than 50 entries.
    """
    with mp.Pool(8) as pool:
        pool.map(_worker_distinct, [(str(tmp_path), i) for i in range(50)])

    index_path = Path(tmp_path) / "memory" / "skill_indexes" / "dev.index.json"
    index = json.loads(index_path.read_text())

    assert len(index["memory_entries"]) == 50, (
        f"lost-update bug: expected 50 entries, got {len(index['memory_entries'])}"
    )
    contents = {e["content_preview"] for e in index["memory_entries"]}
    assert len(contents) == 50, "duplicates or losses from racy R-M-W"
