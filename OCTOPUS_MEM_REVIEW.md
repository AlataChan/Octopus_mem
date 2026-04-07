# Octopus_mem Review

Date: 2026-04-06 (first pass by Codex)
Second pass: 2026-04-07 (Claude, evidence-driven audit — see §8–§13)

This document is a focused review of `Octopus_mem` from three angles:

1. What `Octopus_mem` should fix and optimize first
2. The 5 core designs worth borrowing from `claude-mem`
3. The parts of `claude-mem` that `Octopus_mem` should explicitly avoid copying

The sections numbered 1–7 are the original Codex pass (design-level opinions).
Sections 8–13 are a second-pass audit by Claude that actually ran the code,
pins issues to exact file paths and line numbers, and adds concrete patches.
If §1–§7 and §8–§13 disagree, §8–§13 supersedes — it is backed by repro.

## Executive Summary

`Octopus_mem` has the better long-term product direction if the goal is a lighter, more portable, more controllable memory substrate for multiple agents.

`claude-mem` has the better current implementation if the goal is a complete, already-working memory pipeline for Claude Code today.

The practical recommendation is:

- Keep building on `Octopus_mem`
- Do not copy `claude-mem` wholesale
- Borrow a small set of proven memory mechanisms from `claude-mem`
- First fix packaging, runtime correctness, schema stability, and retrieval flow before adding more features

## 1. Octopus_mem: What Needs Fixing and Optimizing

### P0: Correctness and Packaging

These should be fixed before any major feature work.

1. Packaging and entrypoint mismatch
   - `setup.py` exposes `octopus-mem=octopus_mem.cli:main`, but the public repo structure does not clearly show a proper `octopus_mem/` package layout.
   - This creates immediate install and usability risk.

2. `requirements.txt` is not production-clean
   - `python>=3.10` appears inside requirements, which is not the right place for interpreter constraints.
   - Runtime dependencies, optional semantic dependencies, and dev dependencies should be separated.

3. README and repository contents are not fully aligned
   - README references items such as `examples/basic_usage.py`, but the public repo view does not clearly show those paths.
   - The documented architecture is ahead of the actual implementation.

4. Runtime bug risk in core code
   - `memory_manager.py` uses date/time logic and should be audited for missing imports and basic path/test coverage before being treated as a stable foundation.

5. Mixed-language operational surface
   - Core logic is Python, but skill wrappers and update scripts currently involve Node `.mjs` scripts.
   - This increases maintenance cost early, before the product surface is stable.

### P1: Architecture Gaps

These are the next blockers after correctness.

1. The memory pipeline is not yet a closed loop
   - `Octopus_mem` has good storage ideas, but the repo still reads more like a storage/indexing framework than a full memory system.
   - A real memory system needs a closed loop:
   - capture
   - normalize
   - summarize/compress
   - index
   - retrieve
   - inject back into the next interaction

2. Data model is not frozen enough
   - The repo has the right concepts: `daily`, `long_term`, `skill_indexes`.
   - But it still needs stable schemas for:
   - daily memory documents
   - long-term memory notes
   - skill index records
   - retrieval result objects
   - memory importance / recency metadata

3. Retrieval strategy is conceptually good but not operationally precise enough
   - The README mentions layered retrieval and time decay.
   - What is still missing is a strict retrieval contract:
   - what returns IDs only
   - what returns snippets
   - what returns full details
   - what gets injected automatically
   - what stays on-demand

4. No strong evidence of black-box tests for memory behavior
   - Memory systems fail less from syntax bugs than from behavior drift.
   - You need fixture-based tests for:
   - storing notes
   - updating indexes
   - daily-to-long-term promotion
   - retrieval ranking
   - context injection selection

5. Private data sync design needs hardening
   - The dual-repo model is attractive, but it becomes fragile if sync semantics are not explicit.
   - Data ownership, merge policy, conflict policy, and ignored file patterns should be validated against actual storage formats.

### P2: Optimization and Product Quality

These matter after the core loop is real.

1. Add token-budget awareness
   - A memory system without token economics usually turns into context bloat.
   - Retrieval should measure not just relevance, but prompt cost.

2. Add explicit recency and importance scoring
   - Time decay is mentioned, but should become a formal ranking layer.
   - Suggested ranking dimensions:
   - recency
   - skill match
   - semantic relevance
   - importance
   - user-pinned or manually promoted status

3. Add observability
   - For every retrieval, record:
   - selected memories
   - rejected memories
   - score breakdown
   - estimated token cost
   - source layer

4. Add migration-safe adapters
   - Keep `md/jsonl` as source-of-truth when possible.
   - Treat SQLite and vector indexes as rebuildable derived artifacts.

5. Benchmark before optimizing internals
   - Define success with metrics:
   - cold start time
   - retrieval latency
   - peak memory
   - index rebuild time
   - injected token count per session

## 2. Recommended Target Architecture for Octopus_mem

The current direction is sound, but the architecture should be tightened into explicit layers.

### Recommended module split

- `octopus_mem/domain/`
  - memory record types
  - ranking models
  - retention rules
  - schemas
- `octopus_mem/storage/`
  - markdown store
  - jsonl event store
  - sqlite derived index
- `octopus_mem/indexing/`
  - skill index builder
  - daily index builder
  - long-term link builder
  - optional vector index adapter
- `octopus_mem/retrieval/`
  - ids-first retrieval
  - timeline retrieval
  - detail hydration
  - injection candidate selector
- `octopus_mem/pipeline/`
  - capture
  - compaction
  - promotion
  - cleanup
- `octopus_mem/cli/`
  - ingest
  - retrieve
  - reindex
  - inject
  - inspect

### Recommended source-of-truth policy

- Source-of-truth:
  - markdown
  - jsonl
- Derived and rebuildable:
  - sqlite
  - embeddings
  - caches

That gives you a lighter and safer system than a database-centric design.

## 3. The 5 Core Designs Octopus_mem Should Borrow from claude-mem

These are the best parts of `claude-mem` from a memory-systems perspective.

### 1. Dual-layer memory compression: observation plus summary

Why it is strong:

- `claude-mem` does not only store end-of-session summaries.
- It captures structured observations during work, then emits a higher-level summary later.
- This gives both local detail and session-level abstraction.

What `Octopus_mem` should adopt:

- Keep two memory layers:
  - event/observation layer
  - session/summary layer
- Do not rely on only one daily note or one long-term note to represent everything.

How to adapt it:

- In `Octopus_mem`, the observation layer can stay lightweight:
  - append-only JSONL events
  - compact structured records
- The summary layer can remain markdown or JSON.

### 2. Progressive disclosure retrieval

Why it is strong:

- `claude-mem` uses a clear staged pattern:
  - search index
  - timeline/context
  - full details
- This is one of its best design decisions because it controls token cost.

What `Octopus_mem` should adopt:

- Make retrieval explicitly staged:
  - `search`: IDs and compact snippets only
  - `timeline`: neighborhood and chronology
  - `hydrate`: full note/event content

Why this matters:

- It prevents over-injection.
- It scales much better than "retrieve full documents first".

### 3. Session-start context injection with a hard budget

Why it is strong:

- `claude-mem` is built around the idea that memory is useful only if it gets back into the next session at the right time and in the right size.

What `Octopus_mem` should adopt:

- Add a dedicated injection planner that chooses:
  - what to inject automatically
  - what to leave as retrievable only
  - what to suppress because it is too expensive or too low-signal

The key lesson:

- Retrieval is not the same thing as injection.
- Automatic injection should be stricter than manual retrieval.

### 4. Mode-aware memory policy

Why it is strong:

- `claude-mem` has a mode system that changes observation types, concepts, and prompts based on the workflow.
- That is more powerful than using one universal schema for all tasks.

What `Octopus_mem` should adopt:

- Introduce policy profiles per agent or per skill family.
- Examples:
  - dev mode
  - ops mode
  - legal mode
  - research mode

Each mode should control:

- allowed memory types
- priority rules
- retention rules
- injection rules
- ranking weights

### 5. Metadata filtering plus optional semantic ranking

Why it is strong:

- `claude-mem` does not treat semantic search as the only retrieval mechanism.
- It keeps structured filtering available through SQLite and then optionally layers vector ranking on top.

What `Octopus_mem` should adopt:

- Preserve a strict order:
  - metadata filters first
  - semantic reranking second
  - full hydration last

Why this is important:

- It keeps the system lightweight by default.
- It makes search explainable.
- It allows semantic search to remain optional.

## 4. What Octopus_mem Should Explicitly Avoid Learning from claude-mem

This part is as important as the borrowing list.

### 1. Do not inherit the Claude Code lock-in

`claude-mem` is deeply shaped by Claude Code hooks, worker lifecycles, and plugin mechanics.

Why to avoid it:

- It makes the system powerful in one environment, but harder to reuse elsewhere.
- `Octopus_mem` should stay agent-agnostic and transport-agnostic.

Recommended rule:

- Design memory capture and injection as portable interfaces first.
- Build environment-specific adapters second.

### 2. Do not copy the always-on heavy worker model too early

`claude-mem` has background worker, routing layer, UI, SSE, plugin hooks, provider switching, and multiple operational surfaces.

Why to avoid it:

- That operational complexity is justified only after the memory core is already mature.
- For `Octopus_mem`, it would be premature weight.

Recommended rule:

- Prefer a simple CLI/service boundary first.
- Add a daemon only when proven necessary by latency or concurrency demands.

### 3. Do not make LLM compression the only path for memory creation

`claude-mem` leans heavily on model-mediated observation generation.

Why to avoid over-copying this:

- It increases latency and cost.
- It introduces nondeterminism into the core write path.
- It makes testing harder.

Recommended rule:

- Keep deterministic capture first.
- Use LLM compaction as a second-stage enrichment step, not the only source of truth.

### 4. Do not overbuild the product surface too early

`claude-mem` includes viewer UI, MCP server, HTTP API, background services, search layers, mode systems, and provider integrations.

Why to avoid it:

- `Octopus_mem` should not become a framework zoo before the storage and retrieval semantics are stable.

Recommended rule:

- Delay UI, dashboards, live streams, and broad integrations until the CLI and schemas are stable.

### 5. Do not copy AGPL-bound implementation ideas directly

This is both legal and practical.

- `claude-mem` is AGPL-3.0.
- `Octopus_mem` is presented as MIT.

Recommended rule:

- Borrow ideas, not code.
- Re-express designs in your own architecture and your own implementation language.
- Keep design notes that distinguish:
  - "inspired by"
  - "implemented independently"

## 5. Concrete Next Steps for Octopus_mem

### Phase 1: Stabilize the foundation

- Fix package layout
- Fix CLI entrypoints
- Clean up dependency model
- Align README with actual repo contents
- Add tests for core storage and retrieval
- Eliminate mixed-language wrappers where possible

### Phase 2: Build the closed memory loop

- Add append-only observation event format
- Add deterministic session summary format
- Add explicit index build pipeline
- Add injection candidate selector
- Add staged retrieval commands

### Phase 3: Add quality and scale features

- Add ranking weights
- Add token-budget calculations
- Add optional semantic reranking
- Add promotion from daily to long-term memory
- Add rebuild tools for derived indexes

### Phase 4: Add integrations carefully

- Add agent adapters
- Add sync hardening
- Add inspection tools
- Add optional service mode
- Add UI last, not first

## 6. Recommended Decision

The best path is:

- Continue with `Octopus_mem`
- Treat it as the strategic base
- Refactor it into a clean Python memory core
- Borrow only the strongest memory mechanics from `claude-mem`
- Avoid inheriting `claude-mem`'s environment lock-in and operational heaviness

If this is executed well, `Octopus_mem` can end up with:

- a better license posture
- a lighter runtime
- a more portable architecture
- a cleaner source-of-truth model
- a more sustainable memory platform for multiple agents

## 7. Bottom Line

`claude-mem` is the better reference implementation.

`Octopus_mem` is the better long-term bet, if you are willing to do the engineering work to harden it.

That means the right move is not to abandon `Octopus_mem`.

The right move is to make `Octopus_mem` more disciplined:

- stronger package structure
- stricter schemas
- staged retrieval
- explicit injection policy
- deterministic core pipeline
- optional semantic enhancement

That combination gives you most of the value of `claude-mem` without inheriting its weight.

---

## Part II — Second-Pass Audit (Claude, 2026-04-07)

The first pass (Codex) was a design-level review. This second pass actually
ran the code, walked the repo, and verified the claims. Everything below is
backed by a file path, a line number, or a shell command that reproduces it.

## 8. Verified Runtime Bugs

These are not "risk" items — they are confirmed defects. Reproductions were
run against the current `main` (commit `68ca28c`) on Python 3.13.

### 8.1 `retrieve_memory` crashes with NameError (P0)

- File: [core/memory_manager.py:254](core/memory_manager.py#L254)
- Root cause: `timedelta` is used inside `_search_daily_memories`, but
  [core/memory_manager.py:11](core/memory_manager.py#L11) only imports
  `datetime` from `datetime`. `timedelta` is never imported.
- Blast radius: any call path that reaches `_search_daily_memories` crashes.
  Since `retrieve_memory` falls through to daily search whenever the skill
  index returns fewer than `limit` hits (which is the common case on a fresh
  install), the public retrieval API is effectively broken.
- Reproduction:

  ```bash
  python3 -c "
  import sys; sys.path.insert(0, 'core')
  from memory_manager import MemoryManager
  import tempfile
  with tempfile.TemporaryDirectory() as d:
      MemoryManager(base_path=d).retrieve_memory('hello world')
  "
  # => NameError: name 'timedelta' is not defined
  ```

- Fix: `from datetime import datetime, timedelta`.
- Why this matters for the review verdict: the first pass called this
  "runtime bug risk" and asked for an audit. There was no risk — the code
  was already broken. Any demo, test, or Skill invocation that calls
  `retrieve_memory` without a pre-populated skill index raises on the first
  query. This is the single most important fix before anything else.

### 8.2 `_search_long_term_memories` silently ignores most of `MEMORY.md` (P0)

- File: [core/memory_manager.py:291](core/memory_manager.py#L291)
- Root cause: `for para in paragraphs[:10]` — only the first 10 paragraphs
  of `memory/long_term/MEMORY.md` are ever scanned, regardless of query.
- Blast radius: long-term memory is append-only
  ([core/memory_manager.py:98-104](core/memory_manager.py#L98-L104)),
  so everything written after the 10th block becomes unreachable by
  retrieval. The system looks like it works and then silently stops
  finding anything you added yesterday.
- Fix: remove the `[:10]` cap and move to a streaming scan, or (better)
  build a real inverted index at write time.

### 8.3 Long-term memory IDs are non-deterministic (P1)

- File: [core/memory_manager.py:294](core/memory_manager.py#L294)
- Root cause: `hash(para) % 10000`. Python's built-in `hash()` is
  randomized per process (PYTHONHASHSEED). The same paragraph gets a
  different ID on every run.
- Reproduction:

  ```bash
  python3 -c "print(hash('same-text'))"
  python3 -c "print(hash('same-text'))"
  # => two different integers
  ```

- Blast radius: retrieval results cannot be cached, deduplicated, or
  referenced stably across sessions. Any downstream system that pins a
  memory by ID will break after the next Python process starts.
- Fix: reuse `_generate_memory_id` (which already uses `hashlib.md5`) so
  every layer shares one deterministic ID scheme.

### 8.4 Skill index writes race and corrupt JSON (P1)

- File: [core/memory_manager.py:106-145](core/memory_manager.py#L106-L145)
- Root cause: `_update_skill_index` does read → mutate → overwrite on the
  skill index JSON with no file lock, no atomic rename, and no tmp file.
  Two concurrent `store_memory` calls with the same `skill_name` will
  either lose an entry or leave the JSON file partially written.
- Fix: write to `*.index.json.tmp`, `os.replace()` into place, and hold
  a `fcntl.flock` during the read-modify-write. Or, better, treat the
  JSON index as a derived artifact rebuilt from a JSONL event log — the
  direction §2 already recommends.

### 8.5 `sqlite3` is imported but never used

- File: [core/memory_manager.py:10](core/memory_manager.py#L10)
- Low severity, but symptomatic: the README and §1 both claim SQLite is
  part of the architecture. The actual code never opens a database.
  Either remove the import or land the SQLite derived index. Right now
  the import is a promise the module does not keep.

### 8.6 Keyword extraction is structurally broken for Chinese input

- File: [core/memory_manager.py:147-161](core/memory_manager.py#L147-L161)
- Root cause: `content.lower().split()` tokenizes by whitespace, but the
  seeded example content and the `common_words` stopword list are both
  Chinese — and Chinese text has no inter-word spaces. The result is
  that `_extract_keywords` returns either the whole sentence as one
  token (filtered out by `isalpha()` in mixed content) or nothing at all.
  Meanwhile English content gets a Chinese stopword filter that is a
  no-op for it.
- This is not a stylistic nit; it means the "keyword" column in every
  skill index is essentially random or empty, and the skill-index search
  path in [core/memory_manager.py:210-245](core/memory_manager.py#L210-L245)
  falls back to matching on `content_preview` alone.
- Fix: either drop the keyword field entirely and match on content, or
  plug in `jieba` for Chinese and leave English to whitespace tokenizing.
  Do not ship the current hybrid.

## 9. Security Findings

### 9.1 Path traversal via `skill_name` (Moderate)

- File: [core/memory_manager.py:108-109](core/memory_manager.py#L108-L109)
- Root cause: `skill_name` is concatenated directly into the index path
  with `os.path.join(..., f"{skill_name}.index.json")`. There is no
  allow-list, no `os.path.normpath` check, no containment assertion.
- Reproduction (confirmed):

  ```bash
  python3 -c "
  import sys, tempfile, os
  sys.path.insert(0, 'core')
  from memory_manager import MemoryManager
  with tempfile.TemporaryDirectory() as d:
      os.makedirs(os.path.join(d, 'memory', 'evil'))
      mm = MemoryManager(base_path=d)
      mm.store_memory('payload', memory_type='daily', skill_name='../evil/owned')
      for root, _, files in os.walk(d):
          for f in files:
              if 'owned' in f: print('escaped:', os.path.relpath(os.path.join(root, f), d))
  "
  # => escaped: memory/evil/owned.index.json
  ```

- Primitive: arbitrary file *write* with JSON content, scoped to parent
  directories that already exist. Not an RCE on its own, but it lets any
  caller that controls `skill_name` (e.g. an LLM-planned tool call, a
  web API, or a chat message routed through a skill resolver) stomp on
  config files, hook scripts, or other skill indexes.
- Fix: validate `skill_name` against `^[A-Za-z0-9_\-]+$` and reject
  anything else. Then `assert os.path.commonpath([resolved, skill_dir]) == skill_dir`
  as a defense-in-depth check.

### 9.2 Non-validated `memory_type` silently routes to long-term

- File: [core/memory_manager.py:76-82](core/memory_manager.py#L76-L82)
- `if memory_type == "daily": ... else: write to MEMORY.md`. Any typo
  or adversarial value (`"Daily"`, `"tmp"`, `"../evil"`) lands in the
  single long-term file. Combined with 8.2 (only first 10 paragraphs
  scanned), this means misrouted writes become invisible.
- Fix: whitelist `{"daily", "long_term"}` and raise `ValueError` on
  anything else.

### 9.3 `data_sync.py` exclude patterns delete the data they should sync

- File: [data_repo_config.json:18](data_repo_config.json#L18)
- `"exclude_patterns": ["*.md", "*.jsonl"]` — the storage formats the
  README declares as the source of truth are *excluded* from sync. If
  any code path ever consults this list, the data repo will never get
  memory content. Today nothing reads the field, but shipping a config
  that contradicts the product claim is a landmine.
- Fix: flip to `include_patterns` or delete the field until there is
  actual sync filter code to consume it.

## 10. Contract Mismatches (the root cause of §1)

The first pass noted "README ahead of implementation." The deeper problem
is that four artifacts each describe a *different* system:

| Artifact | What it says the layout is |
| --- | --- |
| [README.md](README.md) | `core/memory_manager.py`, `core/index_engine.py`, `core/retrieval_engine.py`, `examples/basic_usage.py`, `skills/memory_indexer/`, `skills/memory_retriever/`, `skills/memory_evolver/` |
| [setup.py:52](setup.py#L52) | Console entrypoint `octopus-mem=octopus_mem.cli:main` — implies an `octopus_mem/` package |
| [core/memory_manager.py:31-42](core/memory_manager.py#L31-L42) | `_init_directories` hard-codes yet another layout: `memory/`, `storage/config/`, `storage/logs/`, `storage/data/`, `skills/memory_indexer/`, `skills/memory_retriever/`, `skills/memory_evolver/`, `core/` |
| Actual repo | `core/memory_manager.py` only; `skills/memory_{molt,dev,content,ops,law,finance}/`; `indexes/` (empty); `memory/` (empty); no `octopus_mem/` package; no `examples/` |

Concrete consequences:

- **`pip install -e .` produces a broken entrypoint.** `find_packages()`
  finds nothing named `octopus_mem`, so `octopus-mem` on the shell will
  fail with `ModuleNotFoundError: No module named 'octopus_mem'`.
- **Skills reference a script that does not exist.**
  [skills/memory_dev/scripts/retrieve.mjs:16](skills/memory_dev/scripts/retrieve.mjs#L16)
  shells out to `../../simple_memory_retriever.py`. That file is not in
  the repo. Every skill retrieve script is a dead link.
- **Skills call `data_sync.py --agent dev` but `data_sync.py` has no
  CLI at all.** [tools/data_sync.py](tools/data_sync.py) does not use
  `argparse`; `if __name__ == "__main__"` just calls `run_full_setup()`.
  The `--agent` flag is silently ignored by `subprocess`, and the
  update path does nothing the user thinks it is doing.
- **`requirements.txt` contains `python>=3.10`.**
  [requirements.txt:4](requirements.txt#L4) — not a valid pip requirement.
  `pip install -r requirements.txt` will fail (or, on some pip versions,
  warn and skip). `python_requires` belongs in `setup.py`, which already
  has it correctly set.
- **`_init_directories` creates directories that contradict the active
  layout.** On first use of `MemoryManager`, it creates empty
  `skills/memory_indexer/`, `skills/memory_retriever/`,
  `skills/memory_evolver/`, and a `storage/` tree that nothing else
  writes to. Every run leaves phantom dirs next to the real skills.
- **`data_sync.py` force-migrates `memory/` and `indexes/` into
  `.data_temp/` on first setup** ([tools/data_sync.py:92-106](tools/data_sync.py#L92-L106)),
  but `_init_directories` just re-creates them empty on the next
  `MemoryManager(...)` call. The two modules fight over the same
  directories.

The fix here is not "align the README" — it is to pick one layout,
delete the other three, and enforce it with tests. A good sentinel:
`pytest` must be able to import `octopus_mem` by name.

## 11. Additional Patterns to Borrow From claude-mem (beyond the 5 in §3)

The Codex pass named five. Four more are worth calling out:

### 11.1 Treat observations as typed records, not free text

`claude-mem` classifies observations into a small enum (decision, fact,
open-question, etc.) at write time. That lets retrieval filter by type
before any text matching and makes the injection planner's job much
easier (e.g. "always inject open questions from the last session").

Adopt as: add a required `kind` field to the observation JSONL schema.
Keep the enum tiny (5–7 values). Reject unknown values.

### 11.2 One append-only log per session, one summary per session

`claude-mem` keeps per-session trace files. Debugging memory drift is
enormously easier when you can replay a single session's events in
order. `Octopus_mem` currently has only `memory_operations.jsonl`
([core/memory_manager.py:174](core/memory_manager.py#L174)), which
is a global firehose with no session boundary.

Adopt as: `storage/sessions/{session_id}.jsonl` (events) +
`memory/daily/{date}/{session_id}.md` (summary). Global log becomes
derived.

### 11.3 Injection is a distinct subsystem with its own tests

`claude-mem` separates "what the index knows" from "what gets pasted
into the next prompt." The injection planner is testable in isolation
with a fixed token budget.

Adopt as: a pure function
`plan_injection(candidates, budget_tokens) -> selected, rejected, reason`.
Black-box test it against golden fixtures. This is the single piece
most likely to make the product feel different from "grep over markdown."

### 11.4 A small MCP surface is a good retrieval contract

The first pass said "avoid MCP server overhead." Agreed on the server,
but the MCP *schema* is a good forcing function — it makes you decide
what `search`, `timeline`, and `get_observations` actually return, and
those types are portable across agents. Write the tool schemas first,
even if the initial transport is just a CLI.

## 12. Concrete Fix Plan (ordered, minimum viable)

This is what I would do before any new feature, in this order. Each
step has an acceptance signal so you can tell when it is done.

| # | Change | File(s) | Done when |
| --- | --- | --- | --- |
| 1 | Import `timedelta`; add pytest that calls `retrieve_memory('x')` on an empty store | [core/memory_manager.py:11](core/memory_manager.py#L11), `tests/test_memory_manager.py` | Test passes |
| 2 | Validate `skill_name` (`^[A-Za-z0-9_\-]+$`) and `memory_type` (`{"daily","long_term"}`); add parametrized tests for traversal attempts | [core/memory_manager.py:47-91](core/memory_manager.py#L47-L91) | Traversal reproduction raises `ValueError` |
| 3 | Replace `hash(para)` with `_generate_memory_id(para)`; assert IDs are stable across two interpreter runs | [core/memory_manager.py:294](core/memory_manager.py#L294) | Subprocess test passes |
| 4 | Remove `paragraphs[:10]` cap; stream-scan the whole file | [core/memory_manager.py:291](core/memory_manager.py#L291) | New test: writing 20 long-term notes and querying for the 19th returns it |
| 5 | Move the entrypoint. Create `octopus_mem/__init__.py`, `octopus_mem/cli.py`, `octopus_mem/manager.py` (move `memory_manager.py` into the package). Delete the stray `_init_directories` dirs. | `octopus_mem/`, `core/`, `setup.py` | `pip install -e . && octopus-mem --help` works |
| 6 | Fix `requirements.txt`: remove `python>=3.10`; split runtime vs dev deps | [requirements.txt](requirements.txt), [setup.py:38-49](setup.py#L38-L49) | `pip install -r requirements.txt` succeeds clean |
| 7 | Decide: either implement `simple_memory_retriever.py` and a real `--agent` flag on `data_sync.py`, or delete the `.mjs` wrappers and replace with a single Python CLI | `skills/memory_*/scripts/*.mjs`, `tools/data_sync.py` | Running one skill end-to-end returns real results |
| 8 | Atomic index writes: write to `.tmp`, `os.replace`, `fcntl.flock` during R-M-W; add a concurrent-write test using `multiprocessing` | [core/memory_manager.py:106-145](core/memory_manager.py#L106-L145) | Concurrent test never produces a JSON parse error |
| 9 | Freeze the schemas declared in §1.P1: `observation.schema.json`, `summary.schema.json`, `skill_index.schema.json`. Validate on read/write with `jsonschema` | `octopus_mem/domain/schemas/` | All existing tests still pass after the round-trip validator |
| 10 | Add a tiny `plan_injection` function with golden tests, as described in §11.3 | `octopus_mem/retrieval/injection.py` | Golden test: given fixture + 2k token budget, selection is stable |

Steps 1–4 are strictly bug fixes and should land in a single PR.
Steps 5–7 unify the runtime story and are blocking for any external
user. Steps 8–10 build the closed loop §1 asked for, in the minimum
order that still produces a working system at every commit.

## 13. Acceptance Gate (how to know you are done with Phase 1)

Borrowed from the project's own `CLAUDE.md` discipline: a gate, not
a feature list.

1. `pip install -e .` from a clean venv succeeds with zero warnings.
2. `octopus-mem --help` prints a usage string.
3. `pytest` runs and passes with coverage ≥ 70% on `octopus_mem/`.
4. `pytest -k "traversal or concurrent or nameerror"` passes —
   every bug in §8 and §9 has a regression test.
5. Running `octopus-mem store '...' --skill dev --type daily` then
   `octopus-mem retrieve '...'` returns the same record, in both
   the same process *and* a fresh process.
6. `rg -n "simple_memory_retriever|index_engine\.py|retrieval_engine\.py|examples/basic_usage"` returns zero hits — every dead reference has been either implemented or deleted.
7. A single `docs/ARCHITECTURE.md` describes *one* layout and matches
   what `find octopus_mem memory indexes skills -type d` prints.

Only after all seven pass does Phase 2 (the closed memory loop from §1)
become worth starting. Until then, any new feature lands on top of a
broken retrieval path and a fractured layout, and the compounding cost
will outrun the compounding value.

## 14. Bottom Line, Restated

The first pass was right about the strategy: keep `Octopus_mem`,
borrow ideas from `claude-mem`, avoid the lock-in. Nothing in the
second pass changes that verdict.

What the second pass changes is the order of operations. Before any
of the architecture work in §2 or the borrowing work in §3 is
worthwhile, this repo needs a single unbroken path from
`pip install` → `store` → `retrieve` → `retrieve again from a new
process`. Today that path is broken in at least five independent
places, and every one of them is a ~5-line fix.

Fix the five. Then §1–§7 becomes actionable, not aspirational.
