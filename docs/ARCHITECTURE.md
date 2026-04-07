# Octopus_mem Architecture

Canonical layout for the Phase 1 package structure:

```text
Octopus_mem/
├── octopus_mem/
│   ├── __init__.py
│   ├── cli.py
│   ├── manager.py
│   └── storage/
│       ├── __init__.py
│       └── locking.py
├── config/
├── docs/
│   └── ARCHITECTURE.md
├── indexes/
├── memory/
│   ├── daily/
│   ├── long_term/
│   └── skill_indexes/
├── skills/
│   ├── memory_molt/
│   ├── memory_dev/
│   ├── memory_content/
│   ├── memory_ops/
│   ├── memory_law/
│   └── memory_finance/
├── tests/
└── tools/
```

`core/` no longer exists. Importable Python code lives under `octopus_mem/`.

## Naming Contract

| Agent slug (`--skill`) | Display `skill_name` | On-disk index path |
| --- | --- | --- |
| `molt` | `orchestrator` | `memory/skill_indexes/molt.index.json` |
| `dev` | `development` | `memory/skill_indexes/dev.index.json` |
| `content` | `content_creation` | `memory/skill_indexes/content.index.json` |
| `ops` | `operations` | `memory/skill_indexes/ops.index.json` |
| `law` | `legal` | `memory/skill_indexes/law.index.json` |
| `finance` | `finance` | `memory/skill_indexes/finance.index.json` |

The CLI accepts only the agent slug. The display `skill_name` is documentation, not a routing key.

## Why No Reindex

The index file is the source of truth in this phase. Rebuilding from markdown would be lossy because `skill_name` is not preserved in the markdown source. A real reindex requires the append-only JSONL event log, which is out of scope for this plan.

## Lock Contract

The lock window covers the full read-modify-write. Callers may not read outside the mutator. `fcntl.flock` is advisory on both macOS and Linux; we only ever touch our own lockfiles, so BSD vs POSIX differences are invisible. Stale `.lock` files left behind by crashed processes are harmless disk noise because flock state lives in the kernel, not the filename.

Dev install: `pip install -e ".[dev]"` — runtime deps are minimal; `pytest`/`ruff`/`black` live in the dev extras.
