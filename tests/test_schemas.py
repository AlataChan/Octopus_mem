import json
from pathlib import Path

import pytest

from octopus_mem import MemoryManager
from octopus_mem.domain.validate import schema_validator
from octopus_mem.storage import locked_update_json, read_json_validated


def _valid_observation():
    return {
        "version": "1.0.0",
        "id": "mem_deadbeef",
        "content": "Observation content",
        "timestamp": "2026-04-07T18:57:19.000000",
        "type": "daily",
        "skill": "dev",
        "metadata": {"tags": ["test"]},
    }


def _valid_summary():
    return {
        "version": "1.0.0",
        "date": "2026-04-07",
        "entries": ["entry one", "entry two"],
    }


def _valid_skill_index():
    return {
        "version": "1.0.0",
        "skill_name": "dev",
        "last_updated": "2026-04-07T18:57:19.000000",
        "memory_entries": [
            {
                "id": "mem_deadbeef",
                "timestamp": "2026-04-07T18:57:19.000000",
                "content_preview": "phase schema test",
                "search_text": "phase schema test",
                "tags": [],
                "source": "memory/daily/mem_deadbeef",
            }
        ],
        "statistics": {
            "total_memories": 1,
            "last_memory_id": "mem_deadbeef",
        },
    }


def test_observation_schema_accepts_valid_fixture():
    schema_validator("observation")(_valid_observation())


def test_observation_schema_rejects_malformed_fixture():
    bad = _valid_observation()
    bad["type"] = "weekly"
    with pytest.raises(Exception):
        schema_validator("observation")(bad)


def test_summary_schema_accepts_valid_fixture():
    schema_validator("summary")(_valid_summary())


def test_summary_schema_rejects_malformed_fixture():
    bad = _valid_summary()
    bad["entries"] = ["ok", 2]
    with pytest.raises(Exception):
        schema_validator("summary")(bad)


def test_skill_index_schema_accepts_valid_fixture():
    schema_validator("skill_index")(_valid_skill_index())


def test_skill_index_schema_rejects_malformed_fixture():
    bad = _valid_skill_index()
    bad["statistics"]["total_memories"] = "1"
    with pytest.raises(Exception):
        schema_validator("skill_index")(bad)


def test_read_json_validated_returns_data(tmp_path):
    path = tmp_path / "skill.index.json"
    payload = _valid_skill_index()
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = read_json_validated(path, validator=schema_validator("skill_index"))

    assert loaded == payload


def test_locked_update_json_validate_out_failure_leaves_file_untouched(tmp_path):
    from jsonschema import ValidationError

    path = tmp_path / "skill.index.json"
    original = _valid_skill_index()
    path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    def _make_invalid(current):
        broken = dict(current)
        broken["statistics"] = {
            "total_memories": "bad",
            "last_memory_id": current["statistics"]["last_memory_id"],
        }
        return broken

    with pytest.raises(ValidationError):
        locked_update_json(
            path,
            _make_invalid,
            validate_in=schema_validator("skill_index"),
            validate_out=schema_validator("skill_index"),
        )

    assert path.read_text(encoding="utf-8") == before


def test_manager_validation_can_be_disabled_with_env_var(tmp_path, monkeypatch):
    index_path = tmp_path / "memory" / "skill_indexes" / "dev.index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    invalid_index = _valid_skill_index()
    invalid_index.pop("version")
    index_path.write_text(json.dumps(invalid_index, ensure_ascii=False, indent=2), encoding="utf-8")

    mm = MemoryManager(base_path=str(tmp_path))

    with pytest.raises(Exception):
        mm._search_skill_index("dev", "phase", 5)

    monkeypatch.setenv("OCTOPUS_MEM_VALIDATE", "0")
    results = mm._search_skill_index("dev", "phase", 5)

    assert len(results) == 1
    assert results[0]["id"] == "mem_deadbeef"
