import json
from importlib import resources
from typing import Any, Callable

from jsonschema import ValidationError, validate


_SCHEMA_FILES = {
    "observation": "observation.schema.json",
    "summary": "summary.schema.json",
    "skill_index": "skill_index.schema.json",
}

_SCHEMA_CACHE: dict[str, dict[str, Any]] | None = None


def load_schemas() -> dict[str, dict[str, Any]]:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        package = resources.files("octopus_mem.domain.schemas")
        _SCHEMA_CACHE = {
            name: json.loads(package.joinpath(filename).read_text(encoding="utf-8"))
            for name, filename in _SCHEMA_FILES.items()
        }
    return _SCHEMA_CACHE


def schema_validator(schema_name: str) -> Callable[[Any], None]:
    """Return a callable that raises jsonschema.ValidationError on bad data."""
    schemas = load_schemas()
    if schema_name not in schemas:
        raise KeyError(f"Unknown schema: {schema_name}")

    schema = schemas[schema_name]
    schema_version = schema.get("version", "")
    schema_major = schema_version.split(".", 1)[0] if isinstance(schema_version, str) else None

    def _validate(data: Any) -> None:
        if isinstance(data, dict) and isinstance(data.get("version"), str) and schema_major is not None:
            data_major = data["version"].split(".", 1)[0]
            if data_major != schema_major:
                raise ValidationError(
                    f"{schema_name} major version mismatch: expected {schema_version}, got {data['version']}"
                )
        validate(data, schema)

    return _validate
