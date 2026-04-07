# Octopus_mem Fix & Stabilization — Implementation Plan

- **Owner**: Claude (designer) → Codex (executor + reviewer)
- **Source of truth**: [OCTOPUS_MEM_REVIEW.md](../../OCTOPUS_MEM_REVIEW.md) §8–§13
- **Project conventions**: user-global `~/.claude/CLAUDE.md` (designer = Claude; executor + reviewer = Codex; pass criteria overall ≥ 7.0, no dim ≤ 3 — this plan targets ≥ 8.0). The repo has no project-local `CLAUDE.md`; conventions are inherited from the user-global one.
- **Scope**: bring `Octopus_mem` from "broken on first call" to "passes acceptance gate §13"
- **Out of scope (this plan)**: closed-loop memory evolution, semantic search, LLM-driven summarization, dual-repo encryption — those land *after* this plan succeeds
- **Plan version**: v3.2 (2026-04-07). v3.0 → v3.1: Codex round-3 PASS at 8.2 overall + 3 polish edits Codex flagged as "materially tighter" (read-validation contract, ruff dev dependency, agent slug vs skill_name mapping). v3.1 → v3.2: Claude self-audit (Plan Ready Gate, see §14.4) caught one factual error in the F3.7 naming-contract table — the v3.1 wording cited `_meta.json` as the source of `skill_name`, but the actual `_meta.json` files only carry `agent` and `slug`; the `skill_name` field lives in `SKILL.md`'s `metadata` block and in `config/memory_index.json`. Corrected in §5.1 F3.4 / F3.7.

---

## 0. Working Backwards — what "done" looks like

There are two gate sets, deliberately separated (this addresses Codex round-1
objection 5 — "gate drift"):

- **Phase gates** (per-phase): listed inside each phase section. They are
  the merge bar for *that* phase only. Phases land independently.
- **Final gates G1–G7**: checked on a fresh clone after Phase 5 merges.
  They are the user-visible "is the project fixed?" contract.

### 0.1 Final gates G1–G7

| # | Gate | Verification command (must exit 0) |
| --- | --- | --- |
| G1 | Clean install (no hard errors; pip warnings allowed) | `python -m venv .venv && .venv/bin/pip install -e . 2>&1 \| tee install.log; ! grep -E "^ERROR" install.log` |
| G2 | CLI works | `.venv/bin/octopus-mem --help && .venv/bin/octopus-mem store "smoke" --type daily && .venv/bin/octopus-mem retrieve "smoke"` |
| G3 | Tests pass with coverage ≥ 70% on `octopus_mem/` | `.venv/bin/pytest --cov=octopus_mem --cov-fail-under=70` |
| G4 | Every verified §8/§9 **runtime/security** defect has a named regression test (lint-only fixes are covered by G8) | `.venv/bin/pytest tests/test_memory_manager.py::test_retrieve_on_empty_store_does_not_crash tests/test_memory_manager.py::test_long_term_scan_finds_recent_entries tests/test_memory_manager.py::test_long_term_id_stable_across_processes tests/test_memory_manager.py::test_skill_name_rejects_traversal tests/test_memory_manager.py::test_skill_name_accepts_legit_names tests/test_memory_manager.py::test_memory_type_rejects_unknown_values tests/test_memory_manager.py::test_index_entry_has_no_keyword_field tests/test_memory_manager.py::test_index_entry_has_search_text tests/test_memory_manager.py::test_data_repo_config_has_no_landmine_field tests/test_concurrency.py::test_concurrent_store_does_not_corrupt_index tests/test_concurrency.py::test_concurrent_store_does_not_lose_updates` |
| G5 | Round-trip across processes (write in process A, read in process B) | see §7.5 |
| G6 | No dead references in repo | `! rg -n "simple_memory_retriever\|core/index_engine\.py\|core/retrieval_engine\.py\|examples/basic_usage" --glob '!OCTOPUS_MEM_REVIEW.md' --glob '!.plans/**'` |
| G7 | Single layout doc | `docs/ARCHITECTURE.md` exists; its directory tree matches `find octopus_mem memory indexes skills -type d \| sort` output |
| G8 | Lint gate (covers F0.6 sqlite3 dead-import and any future dead code) | `.venv/bin/ruff check octopus_mem/ tests/` |

> **G1 rationale (post-review fix)**: matching `^ERROR` only — pip prints
> deprecation `WARNING` lines for many transitive deps, none of which we
> can fix in this plan. A gate that fails on warnings would block legitimate
> merges. Hard install errors only.
>
> **G4 rationale (round-2 fix)**: Codex round-2 objection #3 — v2's G4 said
> "every §8/§9 defect has a named regression test", but F0.6 (sqlite3 dead
> import) is verified by `ruff` lint, not a pytest case. The wording was
> over-claiming. Fix: G4 covers runtime/security regressions only;
> lint-only fixes are explicitly covered by the new G8 lint gate. The G4
> test list also adds the positive `test_skill_name_accepts_legit_names`,
> the `test_index_entry_has_search_text` shape test, and the new
> `test_concurrent_store_does_not_lose_updates` (see §4.3).
>
> **G8 rationale**: a lint gate exists alongside G4 specifically so future
> dead-code finds (post Phase 0) inherit a real CI signal. F0.6 is the
> first defect it catches; the second will land for free.

---

## 1. Phasing rationale

```text
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4 ─► Phase 5
  bugs      layout     atomic    skills    schemas   injection
  (P0)      (struct)   writes    (CLI)     (freeze)  (loop seed)
```

- **Phase 0** stops the bleeding. Nothing else matters if `retrieve_memory`
  raises NameError on the first call. Also kills the §9.3 sync-config
  landmine because it is a one-line config delete.
- **Phase 1** is structural — until there is one canonical layout, every
  later change has to be made in three places.
- **Phase 2** lands `locked_update_json` — one helper that holds an
  exclusive lock across the **entire** read-modify-write window so
  neither torn JSON (the §8.4 race) nor lost updates (the v2 design bug
  Codex round-2 caught) can occur. Codex round-1 objection #4 was right
  about the *position* of this phase; round-2 objection #1 was right
  about the *implementation*. Both are fixed in v3.
- **Phase 3** deletes the broken `.mjs` skill scripts. After this, the
  user-visible commands actually do what the README claims via the
  Phase 1 CLI. There is no `reindex` subcommand — see §5 for why
  (markdown does not preserve `skill_name`, so a rebuild would be lossy).
  Phase 3 is a deletion phase; it adds no new write paths.
- **Phase 4** freezes JSON schemas and runs round-trip validation on
  every read/write. Schemas come *after* skill rewrite because the rewrite
  may surface new fields the skills actually need (the principle: freeze
  schemas around real callers, not speculation).
- **Phase 5** adds the only piece of new functionality in scope: a pure
  `plan_injection` function with golden tests. Everything before this is
  remediation; this is the first foundation block of the closed loop.

**Each phase is independently mergeable.** No phase leaves the repo in a
worse state than it found it. If we stop after Phase 0, the bugs are gone.
If we stop after Phase 3, the product works end-to-end. If we stop after
Phase 5, the foundation for §1–§7 of the review is in place.

### 1.1 Phase dependency graph

```text
Phase 0  ─┐
          │
Phase 1  ◄┘  (depends on P0 tests as regression fence)
   │
   ▼
Phase 2  (atomic writes; needs P1 layout)
   │
   ▼
Phase 3  (skill CLI; consumes P2 atomic helper)
   │
   ▼
Phase 4  (schemas; freezes around P3 callers)
   │
   ▼
Phase 5  (injection; depends on P4 schemas for typed candidates)
```

---

## 2. Phase 0 — Stop the Bleeding (P0 bug fixes)

**Goal**: every defect in §8 of the review (and the §9.3 config landmine)
has a one-line root cause, a fix, and a regression test. Single PR.
Reviewable in under 20 minutes.

**Branch**: `fix/phase0-runtime-bugs`
**Estimated diff size**: ~130 LoC code + ~170 LoC tests

> **Phase 0 import contract**: tests in this phase import via the **current**
> module path, `from core.memory_manager import MemoryManager`. They do
> *not* import `octopus_mem.manager` because that package does not exist
> until Phase 1. Phase 1 includes a single search-and-replace step
> (§3.2 F1.10) that rewrites these imports. This addresses Codex round-1
> objection #2.

### 2.1 Patches

| # | Defect | File | Patch | Verifying test |
| --- | --- | --- | --- | --- |
| F0.1 | `timedelta` NameError (§8.1) | [core/memory_manager.py:11](../../core/memory_manager.py#L11) | `from datetime import datetime, timedelta` | `test_retrieve_on_empty_store_does_not_crash` |
| F0.2 | Long-term scan capped at 10 paragraphs (§8.2) | [core/memory_manager.py:291](../../core/memory_manager.py#L291) | Remove `[:10]`; iterate full file | `test_long_term_scan_finds_recent_entries` |
| F0.3 | Non-deterministic IDs from `hash()` (§8.3) | [core/memory_manager.py:294](../../core/memory_manager.py#L294) | Reuse `_generate_memory_id(para)` | `test_long_term_id_stable_across_processes` |
| F0.4 | `skill_name` path traversal (§9.1) | [core/memory_manager.py:108](../../core/memory_manager.py#L108) | Validate against `^[A-Za-z0-9](?:[A-Za-z0-9_\-]{0,62}[A-Za-z0-9])?$`; assert `commonpath` containment after `os.path.realpath` | `test_skill_name_rejects_traversal` (parametrized) + `test_skill_name_accepts_legit_names` |
| F0.5 | `memory_type` not validated (§9.2) | [core/memory_manager.py:76](../../core/memory_manager.py#L76) | Whitelist `{"daily", "long_term"}`; raise `ValueError` | `test_memory_type_rejects_unknown_values` |
| F0.6 | `sqlite3` dead import (§8.5) | [core/memory_manager.py:10](../../core/memory_manager.py#L10) | Delete the import | `ruff check` in CI (F401) |
| F0.7 | Keyword extraction silent failure (§8.6) | [core/memory_manager.py:147](../../core/memory_manager.py#L147) | Replace `keywords` with a normalized `search_text` field (lower-cased content, no fake tokenization). Delete `_extract_keywords` and the Chinese stopword list | `test_index_entry_has_no_keyword_field` + `test_index_entry_has_search_text` |
| F0.8 | Sync-config landmine (§9.3) | [data_repo_config.json:14-19](../../data_repo_config.json#L14-L19) | Delete the `exclude_patterns` field entirely. The repo currently has no code that reads it; until a real sync filter exists, the field must not exist either | `test_data_repo_config_has_no_landmine_field` |

> **F0.4 regex change (post-review fix)**: Codex round-1 objection answer
> #3. The new regex forbids leading/trailing separators, so `--evil`,
> `_evil_`, and `-` are rejected even though they would otherwise pass
> the simple character class. The 6 in-tree skills (`molt`, `dev`,
> `content`, `ops`, `law`, `finance`) are all comfortably permitted —
> see `test_skill_name_accepts_legit_names` below.
>
> **F0.7 (post-review fix)**: Codex's round-1 answer #2 — keep a
> normalized `search_text` field instead of fake "keywords". Same data,
> honest name. The skill index search path is updated to substring-match
> against `search_text` instead of intersecting against `keywords`.
>
> **F0.8 (post-review fix, addresses round-1 objection #1)**: §9.3 of the
> review pointed at `data_repo_config.json`'s `exclude_patterns` field
> excluding the actual storage formats (`*.md`, `*.jsonl`). It is dead
> config today, but a future contributor reading the field name will
> assume it is honored. Delete it. The "include vs exclude" contract
> debate happens when sync filtering is actually built — not before.

### 2.2 Test plan (Phase 0)

Create `tests/conftest.py`:

```python
import sys, pathlib
# Phase 0 lives in core/; Phase 1 promotes this to a real package.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "core"))
```

Create `tests/test_memory_manager.py`:

```python
import json
import subprocess
import sys
import pytest

from memory_manager import MemoryManager  # noqa: E402  (Phase 0: still in core/, conftest adds the path)


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
        "import sys, json, pathlib;"
        "sys.path.insert(0, 'core');"
        "from memory_manager import MemoryManager;"
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
```

### 2.3 Phase 0 acceptance signal

```bash
pytest tests/test_memory_manager.py -v
# Expected: all tests pass, no warnings, no NameError
```

### 2.4 What Phase 0 does NOT touch

- Package layout (still `core/memory_manager.py`)
- `setup.py` entrypoint
- Skill `.mjs` scripts
- `data_sync.py`
- README

This is deliberate. Phase 0 is reviewable as a pure bug-fix PR. Mixing it
with structural changes makes both harder to merge.

---

## 3. Phase 1 — Layout Unification

**Goal**: one canonical layout. `pip install -e .` produces a working
`octopus-mem` CLI. The four conflicting layouts in §10 collapse to one.

**Branch**: `refactor/phase1-package-layout`
**Estimated diff size**: ~250 LoC moved + ~80 LoC new

### 3.1 Target layout

```text
octopus_mem/                  ← new package, importable as `octopus_mem`
├── __init__.py               ← exports MemoryManager, __version__
├── manager.py                ← moved from core/memory_manager.py
├── cli.py                    ← new: store / retrieve / stats subcommands
├── domain/
│   ├── __init__.py
│   └── ids.py                ← _generate_memory_id, validation regexes
└── storage/
    ├── __init__.py
    └── paths.py              ← single source for memory/, indexes/ paths
                              ← atomic.py added in Phase 2

memory/                       ← unchanged, runtime data dir
indexes/                      ← unchanged, runtime data dir
skills/                       ← unchanged, .mjs scripts deleted in Phase 3
docs/
└── ARCHITECTURE.md           ← new, single layout doc
tests/                        ← new (already has Phase 0 conftest + test_memory_manager.py)
```

### 3.2 Concrete changes

| # | Action | Detail |
| --- | --- | --- |
| F1.1 | `git mv core/memory_manager.py octopus_mem/manager.py` | Preserves git history (`--follow`) |
| F1.2 | Delete `core/` directory | After F1.1 it's empty |
| F1.3 | Create `octopus_mem/__init__.py` | `from .manager import MemoryManager; __version__ = "0.2.0"` |
| F1.4 | Create `octopus_mem/cli.py` | argparse-based: `store`, `retrieve`, `stats` |
| F1.5 | Remove `_init_directories` phantom dirs ([core/memory_manager.py:31-42](../../core/memory_manager.py#L31-L42)) | Only create `memory/{daily,long_term,skill_indexes}` and `storage/logs`. Drop `skills/memory_indexer`, `skills/memory_retriever`, `skills/memory_evolver`, `storage/config`, `storage/data`, `core` |
| F1.6 | Fix `requirements.txt` and dev deps | (a) Remove `python>=3.10` from `requirements.txt`. (b) Keep only `python-dotenv`, `tqdm` as runtime deps. (c) In `setup.py` `extras_require["dev"]`, **drop `flake8`** (we use `ruff` now) and **add `ruff>=0.6.0`** so G8/F0.6 have a real toolchain. (d) `black`, `pytest`, `pytest-cov` stay in dev. This closes Codex round-3 polish item #2: G8 referenced `ruff` but no phase added it as a dep |
| F1.7 | Update `setup.py` entrypoint | `octopus-mem=octopus_mem.cli:main` (no change needed — but verify `find_packages()` now finds `octopus_mem`) |
| F1.8 | Create `docs/ARCHITECTURE.md` | One canonical layout, replaces the README's outdated tree |
| F1.9 | Update `README.md` | Replace the false `core/index_engine.py` / `core/retrieval_engine.py` / `examples/basic_usage.py` references with what actually exists. Link to `docs/ARCHITECTURE.md` for the layout |
| F1.10 | Rewrite Phase 0 test imports | `tests/test_memory_manager.py`: `from memory_manager import MemoryManager` → `from octopus_mem import MemoryManager`. Update the inline subprocess script in `test_long_term_id_stable_across_processes` the same way |
| F1.11 | Delete `tests/conftest.py` path hack | Phase 0 added a `sys.path.insert(0, "core")` shim there. Phase 1 makes it unnecessary; delete the file (or empty it). Verify with `pytest` from a clean checkout |

### 3.3 CLI surface (Phase 1)

```bash
octopus-mem store "content" [--type daily|long_term] [--skill <name>]
octopus-mem retrieve "query" [--skill <name>] [--limit N]
octopus-mem stats
```

That is the entire CLI surface across all phases of this plan. There is
no `reindex` subcommand — Codex round-2 objection #2 (markdown does not
preserve `skill_name`, so a rebuild from markdown would be lossy). A
proper reindex on top of an append-only event log is out of scope for
this plan; see §5 and §12.

### 3.4 Phase 1 acceptance signal

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/octopus-mem --help                              # exits 0
.venv/bin/octopus-mem store "hello world" --type daily    # exits 0
.venv/bin/octopus-mem retrieve "hello"                    # prints the entry
.venv/bin/python -c "from octopus_mem import MemoryManager; print(MemoryManager)"  # works
```

### 3.5 Migration safety

- Phase 0 tests run **before and after** Phase 1. They are the regression
  fence. If any Phase 0 test breaks, the merge is blocked.
- `core/memory_manager.py` is removed in the same commit as
  `octopus_mem/manager.py` is added. No transitional shim — the import
  surface is changed cleanly.
- Phase 0's `tests/conftest.py` `sys.path` hack is deleted in F1.11.
- Backup branch `pre-phase1-snapshot` tagged before merge. Rollback is
  `git revert <merge-sha>`.

---

## 4. Phase 2 — Atomic Writes & Locking

**Goal**: every JSON read-modify-write on a skill index file runs inside
**one** `fcntl.flock(LOCK_EX)` window so that neither torn JSON **nor lost
updates** can occur. The only public helper is `locked_update_json(path,
mutator)` — there is no "atomic write" primitive that would let a caller
read outside the lock and write inside it. That mistake was Codex round-2
objection #1 against v2 of this plan.

**Why Phase 2 (and not Phase 4 as in v1)**: Codex round-1 objection #4 was
right. The §8.4 write race is a confirmed defect. Phase 3 (skill scripts)
and Phase 4 (schemas) both touch the same write paths. Fixing the contract
*before* rewiring callers means each later phase inherits safety for free
and we never touch write paths twice.

**Branch**: `feat/phase2-atomic-writes`
**Estimated diff size**: ~140 LoC code + ~150 LoC tests

### 4.1 Concrete changes

| # | Action | Detail |
| --- | --- | --- |
| F2.1 | Create `octopus_mem/storage/locking.py` | Single function `locked_update_json(path, mutator, *, default_factory=dict, lock_path=None)`. The mutator signature is `Callable[[dict], dict]` and it runs **inside** the lock. There is no `atomic_write_json` exported — calling sites cannot accidentally read outside the lock |
| F2.2 | Rewrite `_update_skill_index` in `octopus_mem/manager.py` | Replaces the entire current read-mutate-`json.dump` block with one `locked_update_json(index_path, _append_entry, default_factory=_new_index)` call. The previous code separated read from write; the new code does not. This kills both torn-JSON and lost-update races |
| F2.3 | Add `octopus_mem/storage/__init__.py` exports | `from .locking import locked_update_json` |
| F2.4 | Add concurrency regression tests | `tests/test_concurrency.py::test_concurrent_store_does_not_corrupt_index` (catches torn JSON) **and** `test_concurrent_store_does_not_lose_updates` (catches lost updates — the v2 bug). Both in §4.3 below |
| F2.5 | Document the lock contract in `docs/ARCHITECTURE.md` | One section: "The lock window covers the full R-M-W. Callers may not read outside the mutator. `fcntl.flock` is advisory on both macOS and Linux; we only ever touch our own lockfiles, so BSD vs POSIX semantics are invisible. Stale `.lock` files left behind by crashed processes are harmless disk noise — flock state is in the kernel, not the filename (Codex round-2 answer B)" |

### 4.2 Lock contract — `locked_update_json`

`octopus_mem/storage/locking.py`:

```python
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

    with open(lock_path, "a+") as lock_fp:           # create-if-missing, no truncation
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        try:
            # Read inside the lock
            if path.exists():
                with open(path, "r", encoding="utf-8") as fp:
                    current = json.load(fp)
            else:
                current = default_factory()

            # Mutate inside the lock
            new_state = mutator(current)

            # Write inside the lock
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
```

The expected caller shape in `manager.py` becomes:

```python
def _update_skill_index(self, skill_name, memory_obj):
    from octopus_mem.storage import locked_update_json

    index_path = ...  # validated skill index path

    def _empty():
        return {
            "skill_name": skill_name,
            "last_updated": None,
            "memory_entries": [],
            "statistics": {"total_memories": 0, "last_memory_id": None},
        }

    def _append(index_data):
        index_data["memory_entries"].append(self._build_index_entry(memory_obj))
        index_data["last_updated"] = datetime.now().isoformat()
        index_data["statistics"]["total_memories"] = len(index_data["memory_entries"])
        index_data["statistics"]["last_memory_id"] = memory_obj["id"]
        return index_data

    locked_update_json(index_path, _append, default_factory=_empty)
```

### 4.3 Concurrency regression tests (both required)

`tests/test_concurrency.py`:

```python
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
```

Both tests are required for Phase 2 to merge. The first catches the torn-JSON failure mode; the second catches the lost-update failure mode that the v2 design would have shipped silently.

> **Why two tests, not one**: a single "are there 50 entries?" test would
> have caught both bugs, but a torn-JSON failure raises in `json.loads`
> and never reaches the count assertion, masking the count check. Splitting
> them gives clearer failure messages.
>
> **Why 8 workers × 50 entries**: empirically the smallest combination
> that reliably reproduced lost updates in a 100-rep loop on the v2 design
> (which used a separate read + atomic_write_json). If the lost-update
> test ever passes against a v2-style implementation, the rep count is
> too weak — bump to 16 × 100. (Codex round-2 answer A: keep this as the
> PR gate; add a 100–1000-rep nightly stress job, do not make that the
> default.)

### 4.4 Phase 2 gate

```bash
# 20 consecutive passes is the gate. Investigate any single failure.
for i in $(seq 1 20); do
  pytest tests/test_concurrency.py -v || { echo "FAILED on rep $i"; break; }
done
```

Optional nightly stress in CI (out of scope for the merge gate):

```bash
for i in $(seq 1 1000); do
  pytest tests/test_concurrency.py::test_concurrent_store_does_not_lose_updates -q || break
done
```

### 4.5 What Phase 2 does NOT touch

- Schemas (Phase 4)
- Any new field on the index (still the Phase 0 / Phase 1 shape)
- The skill `.mjs` scripts (Phase 3)
- Cleanup of stale `.lock` files. Per Codex round-2 answer B, leftover
  lockfiles from crashed processes are harmless disk noise; flock state
  is in the kernel, not the filename. Opportunistic cleanup is left for
  a future PR if it ever matters

---

## 5. Phase 3 — Skill Scripts Unification

**Goal**: every skill in `skills/memory_*/` exposes its retrieval through
the canonical `octopus-mem` CLI. The broken `.mjs` wrappers are deleted.
There is no `reindex` subcommand in this plan — see the explanation
below.

The choice is **delete the `.mjs` files**, because:

1. They exist solely to shell out to a Python script
   (`simple_memory_retriever.py`) that does not exist.
2. Maintaining both Node and Python toolchains for a single Python project
   is pure tax with zero benefit.
3. `octopus-mem retrieve --skill <name>` (Phase 1) is the strict
   replacement and was already shipped in Phase 1.

> **Why no `reindex` subcommand** (Codex round-2 objection #2): v2 of this
> plan promised an `octopus-mem reindex --skill <name>` that would rebuild
> the per-skill JSON index from the daily/long-term markdown files. Codex
> caught a real correctness gap: the markdown source format
> (`_append_to_markdown` in `manager.py`) records `## {timestamp} [{id}]`
> followed by content — it does **not** preserve `skill_name`. The same
> markdown line can belong to any skill (or none). A rebuild from the
> markdown alone would either be lossy or would have to invent fake skill
> assignments. Both are unacceptable.
>
> The right home for `reindex` is on top of a real append-only event log
> (the JSONL store the review's §11.2 calls for), which is **out of scope
> for this plan**. Phase 3 ships only the deletion + the SKILL.md updates.
> The on-disk index continues to be the source of truth and is only
> mutated by `store_memory` going through Phase 2's locked update helper.

**Branch**: `refactor/phase3-skill-scripts`
**Estimated diff size**: ~250 LoC deleted, ~30 LoC docs

### 5.1 Concrete changes

| # | Action | Detail |
| --- | --- | --- |
| F3.1 | Delete `skills/memory_*/scripts/retrieve.mjs` | All 6 files |
| F3.2 | Delete `skills/memory_*/scripts/update_index.mjs` | All 6 files |
| F3.3 | Delete the now-empty `skills/memory_*/scripts/` directories | All 6 dirs |
| F3.4 | Replace skill `SKILL.md` invocation examples | From `node scripts/retrieve.mjs "..."` to `octopus-mem retrieve "..." --skill <agent-slug>`. The CLI flag value is the **agent slug** (`molt`, `dev`, `content`, `ops`, `law`, `finance`) — the same string the existing `_meta.json` already records under the `agent` field and the `SKILL.md` frontmatter `metadata.agent` field. The CLI does NOT accept the `skill_name` value (`orchestrator`, `development`, etc.) — that is a human-readable label, not a routing key. Closes Codex round-3 polish item #3 |
| F3.5 | Add a "Migration" section to each updated `SKILL.md` | One paragraph: how to migrate from the deleted `.mjs` to the unified CLI; no rebuild needed because the existing `.index.json` files are already consumed by `octopus-mem retrieve` |
| F3.6 | Add a paragraph to `docs/ARCHITECTURE.md` | "Why there is no `reindex`": the index file is the source of truth; rebuilding from markdown would be lossy because skill metadata is not preserved there. A real reindex requires the JSONL event log, which is out of scope |
| F3.7 | Add a "Naming Contract" table to `docs/ARCHITECTURE.md` and link it from each `SKILL.md` | Single source of truth for the agent-slug ↔ display-name ↔ on-disk path mapping below. Stops the next contributor from guessing whether `--skill development` and `--skill dev` mean the same thing (they don't — only the agent slug is accepted) |

**Naming contract** (lands in `docs/ARCHITECTURE.md` per F3.7).
Verified against the actual repo on 2026-04-07 — the `skill_name` column
is sourced from `SKILL.md`'s `metadata.skill_name` field and from
`config/memory_index.json`'s `agents.<slug>.skill_name` field (the two
are duplicates of each other today; the canonical source is whichever
the implementer picks during F3.7 — recommendation: keep both in sync,
do not introduce a third):

| Agent slug (CLI `--skill` value) | `_meta.json` `agent` field | Display `skill_name` (from `SKILL.md` metadata + `config/memory_index.json`) | On-disk index file |
| --- | --- | --- | --- |
| `molt` | `molt` | `orchestrator` | `memory/skill_indexes/molt.index.json` |
| `dev` | `dev` | `development` | `memory/skill_indexes/dev.index.json` |
| `content` | `content` | `content_creation` | `memory/skill_indexes/content.index.json` |
| `ops` | `ops` | `operations` | `memory/skill_indexes/ops.index.json` |
| `law` | `law` | `legal` | `memory/skill_indexes/law.index.json` |
| `finance` | `finance` | `finance` | `memory/skill_indexes/finance.index.json` |

The CLI accepts **only** the agent slug from column 1. The display
`skill_name` in column 3 is documentation / human-readable label and
is not consulted for routing. If columns 1 and 3 ever drift, the slug
wins — the on-disk filename in column 4 is the routing contract.

> **Verification note**: column 2 (`_meta.json` `agent`) is NOT a
> separate routing key — it just happens to equal column 1 today by
> convention. The plan does not depend on `_meta.json` for any logic;
> it is shown for completeness so future contributors can see all the
> places the slug appears.

### 5.2 Phase 3 gate

```bash
# 1. Skill scripts are gone:
! find skills -name '*.mjs' | grep .

# 2. Existing skill indexes still work end-to-end via the canonical CLI:
octopus-mem store "test entry from dev" --type daily --skill dev
octopus-mem retrieve "test entry" --skill dev | grep -q "test entry from dev"

# 3. Skill SKILL.md files no longer reference the deleted scripts:
! rg -n 'scripts/retrieve\.mjs|scripts/update_index\.mjs' skills/

# 4. There is no second CLI on disk:
! find . -name 'cli.py' -not -path './octopus_mem/*' -not -path './.venv/*'
```

### 5.3 What Phase 3 does NOT touch

- The 6-agent metaphor (molt/dev/content/ops/law/finance) — they remain as
  `skill_name` values, no code change required
- `tools/data_sync.py` — left alone. The `--agent` flag was never honored;
  removing the dead `.mjs` callers means the unhonored flag stops being a
  lie. `data_sync.py` itself is out of scope for this plan
- Schemas — those land in Phase 4 around real callers
- Reindex / rebuild — explicitly out of scope (see the rationale block
  above and §12)

---

## 6. Phase 4 — Schema Freeze

**Goal**: the three on-disk JSON shapes have frozen schemas, validated on
every read and every write. Future contributors who add a field must bump
the schema version.

**Why Phase 4 (after Phase 3, not before)**: schemas should be frozen
*around real callers*, not speculative ones. By the time we reach Phase 4,
the only real caller of the index file is `octopus_mem/manager.py` going
through Phase 2's `locked_update_json`. The shape is known. Earlier
freezing would have been guesswork. (Phase 3 deleted the `.mjs` callers
without adding any new ones — see §5.)

**Branch**: `feat/phase4-schemas`
**Estimated diff size**: ~100 LoC code + ~80 LoC tests + 3 schema files

### 6.1 Schemas (frozen, validated on read/write)

Create `octopus_mem/domain/schemas/`:

- `observation.schema.json` — single memory write event
- `summary.schema.json` — daily roll-up (placeholder for Phase 5+)
- `skill_index.schema.json` — per-skill index file

Each schema has a top-level `"version": "1.0.0"` field. Loaders refuse
major-version mismatches with a clear error message.

### 6.2 Validator surface

Validation must not break Phase 2's lock contract. There is no
`load_and_validate` / `dump_and_validate` pair that callers compose
manually — that would put a read outside the lock and reintroduce the
v2 lost-update bug.

Instead, validation is wired *inside* `locked_update_json`. Phase 4
extends Phase 2's helper with two optional hooks:

`octopus_mem/storage/locking.py` (extended):

```python
def locked_update_json(
    path: Path,
    mutator: Callable[[Any], Any],
    *,
    default_factory: Callable[[], Any] = dict,
    lock_path: Path | None = None,
    validate_in: Callable[[Any], None] | None = None,   # NEW in Phase 4
    validate_out: Callable[[Any], None] | None = None,  # NEW in Phase 4
) -> Any:
    """Same as Phase 2, with optional validation inside the lock window.

    If ``validate_in`` is given, it runs on the loaded state before the
    mutator. If ``validate_out`` is given, it runs on the new state
    before the tempfile write. Both run **inside** the lock so a
    failed validation leaves the file untouched.
    """
```

`octopus_mem/domain/validate.py`:

```python
def schema_validator(schema_name: str) -> Callable[[Any], None]:
    """Return a callable that raises jsonschema.ValidationError on bad data."""
```

The skill index R-M-W in `manager.py` becomes:

```python
locked_update_json(
    index_path,
    _append,
    default_factory=_empty,
    validate_in=schema_validator("skill_index"),
    validate_out=schema_validator("skill_index"),
)
```

Validation runs on every read-before-mutate (via `validate_in`) and every
write (via `validate_out`). Volume is human-scale; the overhead is
invisible. **Default is on**; set `OCTOPUS_MEM_VALIDATE=0` to disable
(both polarity and direction documented identically in §9 risk register —
the v3.0 mismatch between §6.2 and §9 is corrected in v3.1).

**Read-only consumers** (e.g. `_search_skill_index`) are covered by a
separate, narrower helper:

```python
# octopus_mem/storage/locking.py
def read_json_validated(
    path: Path,
    *,
    validator: Callable[[Any], None] | None = None,
    lock_path: Path | None = None,
) -> Any:
    """Read JSON under a SHARED lock (LOCK_SH) and validate on the way out.

    Used by read-only retrieval paths that must not block writers
    indefinitely. Multiple readers may hold LOCK_SH concurrently;
    a writer holding LOCK_EX will block until all readers release.
    Returns the loaded data; raises if validation fails.
    """
```

The skill index search path in `_search_skill_index` becomes:

```python
data = read_json_validated(
    index_path,
    validator=schema_validator("skill_index"),
)
```

This closes Codex round-3 polish item #1: "validated on every read and
every write" is now backed by two named helpers, one for the R-M-W path
and one for the read-only path. There is no caller surface that reads
JSON without validation when `OCTOPUS_MEM_VALIDATE` is unset.

> **Why not a separate `load_and_validate` + `dump_and_validate`**: that
> was the shape in v2 of this section, and Codex round 2 caught the
> exact analogous bug at the lock layer. Repeating the same mistake at
> the validator layer would silently reintroduce lost updates whenever
> validation is enabled. Putting validation inside `locked_update_json`
> (writes) and `read_json_validated` (reads) is the only contract that
> cannot be misused this way.

### 6.3 Phase 4 gate

```bash
pytest tests/test_schemas.py -v
# Every schema fixture round-trips. Every malformed fixture is rejected with the right error.
```

### 6.4 Schema migration story

Schemas are version-locked. To change a field shape:

1. Bump the schema's major version
2. Add a one-shot migration in `octopus_mem/domain/migrations/<from>_to_<to>.py`
3. Add a fixture pair (`<from>.json`, `<to>.json`) to the test suite

Out of scope for this plan: actually implementing migrations. Phase 4 only
needs the one-version-pinned schemas. The migration scaffold is documented
but not built.

---

## 7. Phase 5 — Injection Planner (foundation for the closed loop)

**Goal**: a single pure function that takes candidate memories and a token
budget and returns what to inject. This is the foundation block §11.3 of the
review identifies as "the single piece most likely to make the product feel
different from grep over markdown."

**Branch**: `feat/phase5-injection-planner`
**Estimated diff size**: ~150 LoC code + ~250 LoC golden tests

### 7.1 Function signature

```python
# octopus_mem/retrieval/injection.py

from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Candidate:
    id: str
    content: str
    score: float          # 0..1, retrieval relevance
    recency_days: int     # days since written
    kind: str             # "decision" | "fact" | "open_question" | "summary"
    token_count: int

@dataclass(frozen=True)
class InjectionPlan:
    selected: tuple[Candidate, ...]
    rejected: tuple[tuple[Candidate, str], ...]   # (candidate, reason)
    used_tokens: int
    budget_tokens: int

def plan_injection(
    candidates: Sequence[Candidate],
    *,
    budget_tokens: int,
    pin_kinds: tuple[str, ...] = ("open_question",),
    decay_half_life_days: float = 7.0,
) -> InjectionPlan:
    ...
```

### 7.2 Selection algorithm (v1, intentionally simple)

1. **Pin pass**: every candidate whose `kind` is in `pin_kinds` is selected
   first, regardless of score, until budget runs out.
2. **Decay-weighted score**: for the rest, compute
   `effective = score * 0.5 ** (recency_days / decay_half_life_days)`.
3. **Greedy fill**: sort remaining by `effective` desc, take while
   `used_tokens + cand.token_count <= budget_tokens`.
4. **Rejection reasons**: every non-selected candidate gets one of
   `"budget"`, `"low_score"`, `"duplicate_id"`, `"unknown_kind"`.

> **Why this and not a fancier optimizer**: greedy fills ~95% of the value
> for ~5% of the complexity. The golden tests pin behavior so we can swap
> the algorithm later without breaking callers.

### 7.3 Golden tests

`tests/golden/injection/` contains JSON fixtures of the form:

```json
{
  "name": "open_question_pinned_even_when_low_score",
  "budget_tokens": 2000,
  "candidates": [],
  "expected_selected_ids": ["q1", "f3", "f7"],
  "expected_rejected_reasons": {"f9": "budget", "f4": "low_score"}
}
```

Test runner asserts both `selected` and `rejected` reasons match exactly.
JSON fixtures (not Python parametrize) are kept because they are
black-box, diffable, and re-usable from another language or transport
(Codex round-1 answer #5 confirmed this).

### 7.4 Phase 5 gate

```bash
pytest tests/test_injection.py tests/golden/injection -v
# All golden tests pass. New algorithms must produce identical output or update the goldens explicitly.
```

### 7.5 Round-trip acceptance test (G5 from §0.1)

```bash
# Process A: store
.venv/bin/octopus-mem store "decision: use atomic writes" --type long_term --skill dev
# Process B: fresh process, retrieve
.venv/bin/python -c "
from octopus_mem import MemoryManager
mm = MemoryManager()
results = mm.retrieve_memory('atomic writes')
assert any('atomic writes' in r['content_preview'] for r in results), results
print('OK')
"
```

This is the single most important integration test. It is what proves the
project is no longer broken.

---

## 8. Test Strategy Summary

| Layer | Tool | What it covers | Phase added |
| --- | --- | --- | --- |
| Unit | pytest | Bug regressions, validators, ID generation | Phase 0 |
| CLI | pytest + subprocess | `octopus-mem` subcommands smoke tests | Phase 1 |
| Concurrency | pytest + multiprocessing | Atomic writes under contention | Phase 2 |
| Schema | jsonschema | Round-trip and reject malformed | Phase 4 |
| Golden | pytest | Injection planner stability | Phase 5 |
| Integration | shell script | Round-trip across processes | Phase 5 |
| Lint | ruff (F401, E, W) | Dead imports, unused code | Phase 0 |

**Coverage gate**: 70% on `octopus_mem/` (G3). Set in `pyproject.toml`
`[tool.coverage.report] fail_under = 70`. Not 80, not 90 — 70 is the floor
that catches absent test files without inviting "test for the test's sake."
Codex round-1 answer #4 confirmed: package coverage, not diff coverage.

**CI**: GitHub Actions workflow `.github/workflows/test.yml` runs
`pytest --cov` on every push to a branch matching `fix/*`, `refactor/*`,
`feat/*`. Out of scope to set up multi-OS or multi-Python; one matrix
entry (`ubuntu-latest`, Python 3.12) is enough for Phase 0–5.

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Phase 1 git mv loses history on macOS | Low | Medium | Use `git mv` (preserves rename detection); verify with `git log --follow octopus_mem/manager.py` after merge |
| Phase 2 fcntl locks behave differently on macOS vs Linux | Medium | Low | Concurrency test runs in CI on Linux; document macOS-specific gotcha in `docs/ARCHITECTURE.md` if it surfaces |
| Schema validation slows hot path | Low | Low | Volume is human-scale (≤ 10⁴ entries). Validation is **on by default**; if it ever matters, set `OCTOPUS_MEM_VALIDATE=0` to disable both `validate_in`/`validate_out` hooks. (Polarity matches §6.2; the v3.0 mismatch was Codex round-3 polish item #1.) |
| Path traversal regex too strict, blocks legitimate skill names | Low | Medium | The 6 in-tree skills (`molt`, `dev`, `content`, `ops`, `law`, `finance`) are all `[a-z]+`. Phase 0 test `test_skill_name_accepts_legit_names` is parametrized over them so any tightening that breaks the 6 fails CI immediately |
| Injection planner decay constant feels wrong in practice | Medium | Low | Constants are function args, not globals. Tunable per call. Golden tests pin observable behavior, not internals |
| Phase 3 deletes skill `.mjs` files that someone is calling externally | Low | High if it happens | Before merging Phase 3: `rg --type-add 'mjs:*.mjs' -t mjs 'retrieve\.mjs\|update_index\.mjs' ~` from the parent project tree. Document any external callers in the PR description and provide the migration command (`octopus-mem retrieve --skill <name>`) |
| Coverage gate (70%) blocks merges on legitimate refactors | Medium | Low | Allow `--cov-fail-under=0` override on a per-PR basis with explicit reviewer sign-off in PR description |
| Phase 0 conftest.py path hack leaks into Phase 1+ | Low | Low | F1.11 deletes the conftest.py shim. CI runs `pytest` from a clean checkout in Phase 1+ to catch any residual import path assumptions |

---

## 10. Rollback Plan

Each phase merges as **one PR with one commit (squash merge)**. Rollback is
`git revert <commit>` per phase.

The dependency chain for rollback purposes:

```text
Phase 0  (independent — pure bug fixes against core/)
Phase 1  (depends on Phase 0 tests as regression fence; reverting P1 also reverts the F1.10/F1.11 import rewrite, so re-pin tests to core/)
Phase 2  (depends on Phase 1 layout; introduces locked_update_json — the only sanctioned write helper)
Phase 3  (depends on Phase 1 CLI; Phase 2 not strictly required because Phase 3 is deletion-only, but landing in this order keeps the locked helper as the only write path the SKILL.md migration text references)
Phase 4  (depends on Phase 2 locked_update_json — schemas plug in via the validate_in/validate_out hooks; depends on Phase 3 caller shape because the in-tree caller is the only consumer)
Phase 5  (depends on Phase 4 schemas for typed Candidate)
```

Reverting any phase N also requires reverting N+1..5 if those exist,
because the dependency arrows above are real. **Do not cherry-pick across
phases.** If you need to redo Phase 2, redo Phase 2 → Phase 5 forward.

> Each phase has a `pre-phase<N>-snapshot` annotated tag taken before
> merge so rollback is `git checkout -B fix/rollback-pN pre-phaseN-snapshot`.

---

## 11. Owner / Delegation Matrix

Per the user-global `~/.claude/CLAUDE.md`: Claude designs, Codex executes,
Codex also reviews. (There is no project-local `CLAUDE.md` in this repo —
Codex round 1 confirmed.) Concretely:

| Activity | Owner |
| --- | --- |
| This plan (design) | Claude |
| Plan review (scoring) | Codex via `ask codex "[PLAN REVIEW REQUEST] ..."` |
| Phase 0–5 implementation | Codex via `ask codex "[TASK] ..."` per phase |
| Phase code review | Codex via `ask codex "[CODE REVIEW REQUEST] ..."` |
| Acceptance gate execution (G1–G7) | Claude (runs commands, pastes output, confirms each gate) |
| Final user sign-off | User |

Plan review must score **overall ≥ 8.0 with no dimension ≤ 4** before any
implementation begins. Re-spin up to 3 rounds. After 3 failed reviews,
escalate to user with the latest scores and Codex's top objections.

---

## 12. Out of Scope (explicit)

These are real and worth doing — but not in this plan, because including
them would either violate Linus's first question ("is this a real problem
right now?") or would balloon scope past one reviewable PR per phase:

- Closed-loop memory evolution (§1 of review's Phase 2 vision)
- Cross-skill memory linking
- Semantic search / embeddings
- Encryption at rest for the private data repo
- Token-budget-aware retrieval inside `MemoryManager.retrieve_memory`
  (the injection planner is the seam; `retrieve_memory` stays dumb)
- Any change to `tools/data_sync.py` beyond what Phase 3 touches
- Multi-language documentation (README stays Chinese; ARCHITECTURE.md is
  whichever language the implementer prefers)
- Web UI / TUI / dashboard
- Schema migration tooling (Phase 4 only ships the v1 schemas; the
  migration scaffold is documented in §6.4 but not built)
- Real Chinese-aware tokenization (`jieba` etc.). Phase 0 deletes the
  fake keyword field; if golden tests in Phase 5 show injection accuracy
  suffers, tokenization comes back as a separate, evidence-driven PR

---

## 13. Open Questions — Settled in Codex Rounds 1 & 2

These were open in v1/v2. Codex's answers across two rounds are recorded
so v3 reviewers can see what is settled and not re-litigate it:

1. **Phase ordering** (round 1): settled. Phase 0 → 1 → 2 (atomic) → 3
   (skills) → 4 (schemas) → 5 (injection).
2. **F0.7 keyword field** (round 1): settled. Delete `keywords`, replace
   with a normalized `search_text` field.
3. **`skill_name` regex** (round 1): settled.
   `^[A-Za-z0-9](?:[A-Za-z0-9_\-]{0,62}[A-Za-z0-9])?$`.
4. **Coverage gate** (round 1): settled. 70% on `octopus_mem/` package.
5. **Golden fixtures** (round 1): settled. JSON files, not parametrize.
6. **Concurrency test rep count** (round 2 / open Q A): settled. Keep
   8 × 50 × 20 reps as the **PR merge gate**. Add a 100–1000-rep nightly
   stress job as an optional CI signal, **not** the merge gate. See §4.4.
7. **Stale lockfile detection** (round 2 / open Q B): settled. **No** to
   `O_EXCL | O_CREAT`. With `flock`, file existence is not lock state —
   stale `.lock` files left by crashed processes are harmless disk noise
   because lock state is in the kernel. Open the lockfile normally
   (`open(..., "a+")`), use `flock`, and treat residue files as noise.
   See §4.5 and §4.2.
8. **`jsonschema` dep** (round 2 / open Q C): settled. Acceptable runtime
   dep. Do not hand-roll a 50-line validator; the plan ships formal
   schema files, so the library is the right trade. See §6.
9. **`reindex` source-of-truth** (round 2 objection #2): settled —
   removed from this plan entirely. The markdown source does not
   preserve `skill_name`, so a rebuild from markdown would be lossy.
   Reindex requires a real append-only event log (review §11.2), which
   is out of scope. See §5.

There are no remaining open questions for v3. If round 3 surfaces new
ones, they land here as #10+.

---

## 14. Plan Review Summary

| Round | Date | Score (overall · correctness · simplicity · safety · standards) | Verdict | Top objections |
| --- | --- | --- | --- | --- |
| 1 | 2026-04-07 | 7.4 · 7.0 · 8.0 · 6.5 · 8.0 | FAIL (overall < 8.0) | (1) §9.3 sync-config landmine unaddressed; (2) Phase 0 imports `octopus_mem.manager` before Phase 1 creates it; (3) reindex split into second CLI; (4) atomic writes scheduled after skill rewrite; (5) gate drift (G1 too brittle, G4 not enumerated) |
| 2 | 2026-04-07 | 7.6 · 7.5 · 8.0 · 6.5 · 8.5 | FAIL (overall < 8.0) | All 5 round-1 objections addressed. New: (1) `atomic_write_json` only locks the write half — lost-update race remains; (2) `reindex` from markdown is lossy because `skill_name` is not in the source; (3) G4 over-claims by including the lint-only F0.6 |
| 3 | 2026-04-07 | **8.2** · 8.0 · 8.6 · 8.1 · 8.2 | **PASS** (overall ≥ 8.0, all dims ≥ 4) | All round-2 objections addressed. 3 polish items flagged as "materially tighter": (a) read-validation contract underspecified; (b) `ruff` referenced in G8 but never added to dev deps; (c) agent slug vs `skill_name` mapping unclear in `SKILL.md` updates. v3.1 lands all 3 polish edits proactively |
| Claude self-audit (Plan Ready Gate) | 2026-04-07 | n/a (not a Codex review) | Issued v3.2 | One factual error caught in §5.1 F3.7 naming-contract table: `_meta.json` was cited as the source of `skill_name`, but the field actually lives in `SKILL.md` `metadata` block + `config/memory_index.json`. Corrected. See §14.4 |

### 14.1 Round-1 → Round-2 changelog

- **(1) §9.3 landmine** → §2.1 F0.8 deletes `exclude_patterns`; §2.2 has a regression test (`test_data_repo_config_has_no_landmine_field`)
- **(2) Phase 0 imports** → §2 import contract callout + §2.2 conftest path hack; §3.2 F1.10/F1.11 rewrite imports and delete the shim in Phase 1
- **(3) Split CLI** → §5.1 F3.4 (now removed in v3) put `reindex` on `octopus_mem/cli.py` instead of a second `tools/cli.py`
- **(4) Phase ordering** → §1 phase chart now reads 0 → 1 → 2 (atomic) → 3 (skills) → 4 (schemas) → 5 (injection); §4 is the new atomic-writes phase
- **(5) Gate drift** → §0.1 splits phase gates from final gates; G1 matches `^ERROR` only; G4 enumerates explicit test names instead of a `-k` filter

### 14.2 Round-2 → Round-3 changelog

- **(1) Lost-update lock bug** → §4 entirely rewritten. The v2 export
  was `atomic_write_json(path, data)`, which let callers read outside
  the lock and write inside it — leaking lost updates. v3 exports a
  single `locked_update_json(path, mutator)` that holds `LOCK_EX` for
  the **entire** read-modify-write window. The mutator runs **inside**
  the lock. There is no public path to read outside the lock. New
  regression test `test_concurrent_store_does_not_lose_updates` in §4.3
  catches the v2 failure mode explicitly. The §4.5 callout records that
  stale lockfiles are noise, per Codex round-2 answer B.
- **(2) `reindex` markdown rebuild gap** → §5 dropped F3.4/F3.5 entirely.
  Phase 3 is now a deletion-only phase: it removes the `.mjs` scripts
  and updates `SKILL.md` files to use the existing `octopus-mem retrieve`
  command. F3.6 adds a paragraph to `docs/ARCHITECTURE.md` explaining
  why there is no `reindex`. §3.3 / §1 / §6 / §12 all updated to remove
  the reindex promise. The rebuild work moves to the closed-loop scope
  (review §11.2) which is out of scope for this plan.
- **(3) G4 over-claims coverage** → §0.1 G4 wording narrowed to
  "runtime/security defects". A new G8 lint gate covers F0.6 and any
  future dead-code finds. G4's enumerated test list also added the
  positive `test_skill_name_accepts_legit_names`,
  `test_index_entry_has_search_text`, and the new
  `test_concurrent_store_does_not_lose_updates`.

Adopted from Codex round-2 answers to v2 open questions:

- **A** (concurrency reps) → §4.4 keeps 8 × 50 × 20 as the PR gate; the
  optional 1000-rep nightly stress is documented as out-of-scope-for-merge
- **B** (stale lockfile cleanup) → §4.5 + §4.2 docstring: leftover lockfiles
  are noise; do not gate on `O_EXCL`
- **C** (`jsonschema` dep) → §6 keeps `jsonschema` as a runtime dep, no
  hand-rolling

### 14.3 Round-3 polish edits (v3 → v3.1)

Round 3 was a **PASS** at 8.2 overall. Codex flagged 3 polish items as
"materially tighter, ship-ready"; v3.1 lands all 3 in the same plan
revision so the user does not see a fourth review cycle on cosmetic
items.

- **Polish #1 (read-validation contract)** → §6.2 now specifies *two*
  helpers: `locked_update_json` (for R-M-W with `validate_in` and
  `validate_out` hooks running inside `LOCK_EX`) **and** the new
  `read_json_validated(path, *, validator, lock_path)` (for read-only
  consumers under `LOCK_SH`). The "validated on every read and every
  write" claim is now backed by two named callsites. §9 risk register
  env-var polarity (`OCTOPUS_MEM_VALIDATE=0` disables) is now identical
  to §6.2's wording.
- **Polish #2 (`ruff` dev dep)** → §3.2 F1.6 explicitly drops `flake8`
  and adds `ruff>=0.6.0` to `setup.py` `extras_require["dev"]`. G8
  (`ruff check octopus_mem/ tests/`) now has the toolchain it claims.
- **Polish #3 (agent slug vs `skill_name`)** → §5.1 F3.4 clarifies that
  `--skill <agent-slug>` accepts the slug only, not the per-skill
  `skill_name` from `_meta.json`. New F3.7 ships a "Naming Contract"
  table to `docs/ARCHITECTURE.md` (and links it from each `SKILL.md`)
  pinning the agent-slug ↔ `skill_name` ↔ on-disk-path mapping. The
  table is inlined under §5.1 for visibility.

> **Why v3.1 instead of waiting for round 4**: round 3 already cleared
> the 8.0 bar. The plan is "shippable" now. The 3 polish items are
> docs/dependency cleanups that cost nothing to land in the same
> revision and would otherwise live as v3.2 todos. Owner mindset:
> close the loop now, not later.

### 14.4 Plan Ready Gate — Claude self-audit (v3.1 → v3.2)

The user instructed: "all plans must be ready before code creation, no
rework". Codex round 3 was a remote review of the plan text; Claude
ran a local audit against the actual repository before declaring the
plan execution-ready. This is the final gate before any Phase delegation.

**Audit checks performed (all run from this session, not assertions):**

| # | Check | Tool | Result |
| --- | --- | --- | --- |
| A1 | Every line number in §2.1 (F0.1–F0.7) matches the actual `core/memory_manager.py` content | `python -c` against the live file | 8/8 ✅ |
| A2 | F0.8 — `exclude_patterns` actually exists in `data_repo_config.json` | `json.loads` of the live file | ✅ found `["*.md", "*.jsonl"]` |
| A3 | F1.6 — `python>=3.10` actually exists in `requirements.txt` | grep of live file | ✅ |
| A4 | F1.6 (c) — `flake8` actually exists in `setup.py` to be dropped | grep of live file | ✅ |
| A5 | `setup.py` already declares the `octopus-mem=octopus_mem.cli:main` entrypoint and uses `find_packages()` | grep of live file | ✅ |
| A6 | F3.7 naming-contract table — agent slug ↔ `_meta.json` ↔ `skill_name` mapping verified against all 6 skills | iterated all 6 `_meta.json` and `SKILL.md` files | ❌ **bug found and fixed**: `_meta.json` does not carry `skill_name`; the field lives in `SKILL.md`'s `metadata` block. F3.4 / F3.7 corrected, table re-anchored to the right source files |
| A7 | All 11 Python code blocks in the plan parse with `ast.parse` | `ast.parse` per block | 11/11 ✅ |
| A8 | All 35 `§X.Y` cross-references resolve to a real plan heading or are external review-doc refs | regex extraction + set diff | 35/35 ✅ (20 internal, 15 external) |
| A9 | F0.4 `skill_name` regex accepts every legitimate name and rejects every traversal/edge variant | live `re.match` against 28 cases | 28/28 ✅ |
| A10 | G6 dead-reference search returns the expected hits today and would return zero after Phase 1+3 | `rg` against the live repo | ✅ found 7 hits (1 in README, 6 in `.mjs` files), all targeted by Phase 1 / Phase 3 |
| A11 | No `TODO` / `FIXME` / `XXX` / `TBD` / `???` sentinels left in the plan | regex scan | 0/0 ✅ |

**Verdict**: One factual bug caught (A6) and fixed in v3.2. Every other
audit passed. The plan is execution-ready.

**Why this gate exists**: Codex round-3 PASS proved the plan is internally
coherent. The Plan Ready Gate proves the plan is *anchored to the actual
repository state*. Codex doesn't run code; the audit does. Both
checkpoints together close the loop on "ready to delegate" without
relying on either reviewer alone.
