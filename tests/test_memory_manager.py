import json
import subprocess
import sys
import pytest

from octopus_mem import MemoryManager


# --- F0.1 regression ---
def test_retrieve_on_empty_store_does_not_crash(tmp_path):
    mm = MemoryManager(base_path=str(tmp_path))
    assert mm.retrieve_memory("anything") == []


# --- F0.2 regression ---
def test_long_term_scan_finds_recent_entries(tmp_path):
    mm = MemoryManager(base_path=str(tmp_path))
    for i in range(20):
        mm.store_memory(
            f"long term entry number {i} unique-marker-{i}",
            memory_type="long_term",
        )
    results = mm.retrieve_memory("unique-marker-19")
    assert any("unique-marker-19" in r["content_preview"] for r in results)


# --- F0.3 regression: stable IDs across two python processes ---
def test_long_term_id_stable_across_processes(tmp_path):
    script = (
        "import json;"
        "from octopus_mem import MemoryManager;"
        f"mm = MemoryManager(base_path={str(tmp_path)!r});"
        "mm.store_memory('stable content for hashing', memory_type='long_term');"
        "print(json.dumps([r['id'] for r in mm.retrieve_memory('stable')]))"
    )
    env = {"PYTHONHASHSEED": "random"}
    out1 = subprocess.check_output([sys.executable, "-c", script], text=True, env=env).strip()
    out2 = subprocess.check_output([sys.executable, "-c", script], text=True, env=env).strip()
    assert out1 == out2 and out1 != "[]"


# --- F0.4 regression: traversal rejected ---
@pytest.mark.parametrize(
    "evil",
    [
        "../evil",
        "../../etc/passwd",
        "name/slash",
        "name\\backslash",
        "",
        "x" * 65,
        ".",
        "..",
        "-leading-hyphen",
        "_leading_underscore",
        "trailing-hyphen-",
    ],
)
def test_skill_name_rejects_traversal(tmp_path, evil):
    mm = MemoryManager(base_path=str(tmp_path))
    with pytest.raises(ValueError):
        mm.store_memory("p", memory_type="daily", skill_name=evil)


# --- F0.4 positive: legit names accepted ---
@pytest.mark.parametrize("good", ["molt", "dev", "content", "ops", "law", "finance", "a", "a1", "skill_one", "skill-one"])
def test_skill_name_accepts_legit_names(tmp_path, good):
    mm = MemoryManager(base_path=str(tmp_path))
    mm.store_memory("p", memory_type="daily", skill_name=good)  # must not raise


# --- F0.5 regression ---
@pytest.mark.parametrize("bad", ["Daily", "tmp", "../evil", "", "long-term"])
def test_memory_type_rejects_unknown_values(tmp_path, bad):
    mm = MemoryManager(base_path=str(tmp_path))
    with pytest.raises(ValueError):
        mm.store_memory("p", memory_type=bad)


# --- F0.7 regression: index entry shape ---
def test_index_entry_has_no_keyword_field(tmp_path):
    mm = MemoryManager(base_path=str(tmp_path))
    mm.store_memory("hello world", memory_type="daily", skill_name="dev")
    index = json.loads((tmp_path / "memory/skill_indexes/dev.index.json").read_text())
    entry = index["memory_entries"][0]
    assert "keywords" not in entry


def test_index_entry_has_search_text(tmp_path):
    mm = MemoryManager(base_path=str(tmp_path))
    mm.store_memory("Hello WORLD", memory_type="daily", skill_name="dev")
    index = json.loads((tmp_path / "memory/skill_indexes/dev.index.json").read_text())
    entry = index["memory_entries"][0]
    assert entry["search_text"] == "hello world"


# --- F0.8 regression: config landmine ---
def test_data_repo_config_has_no_landmine_field():
    import pathlib
    cfg = json.loads((pathlib.Path(__file__).parent.parent / "data_repo_config.json").read_text())
    assert "exclude_patterns" not in cfg.get("sync", {})


def test_long_term_dedup_collapses_identical_content(tmp_path):
    """Phase 0 introduced retrieval-time dedup of long-term entries
    with identical content (same content-hash ID). Lock the behavior
    so Phase 2-5 refactors don't accidentally re-introduce duplicates.
    """
    from octopus_mem import MemoryManager
    mm = MemoryManager(base_path=str(tmp_path))
    for _ in range(3):
        mm.store_memory('identical long term content', memory_type='long_term')
    results = mm.retrieve_memory('identical')
    matching = [r for r in results
                if 'identical long term content' in r['content_preview']]
    assert len(matching) == 1, (
        f'expected dedup to 1 entry, got {len(matching)}: {results}'
    )
