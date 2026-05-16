# Changelog

All notable changes to Claude_Meister are documented here. This project
follows [Semantic Versioning](https://semver.org/).

## v2.0.0 — 2026-05-17

The "memory follows the repo, not the tool" release. v2.0 introduces a
human-facing CLI (`meister`) over the existing memory store and seeds it from
git history so first-run is never empty.

### Added
- **`meister` CLI** — platform-independent surface over the conversation memory
  store. Commands: `init`, `last`, `recall`, `show`, `status`, `install-hooks`,
  `backfill`, `doctor`. Same memory works from Claude Code, Cursor, Codex,
  Aider, or your shell.
- **Capture hooks** (`UserPromptSubmit` + `PostToolUse` + `Stop`) that append a
  turn record to repo-local `.repo_memory/conversation.jsonl`. Fail-open: any
  exception is swallowed, hooks never block tool execution.
- **Layered retrieval** — L0 one-line session titles → L1 expanded session
  detail → L2 raw event stream. Recall cost stays bounded as history grows.
- **Git-history backfill** — `install-hooks` (and standalone `meister backfill`)
  synthesizes one session per recent non-merge commit so first-run is never
  empty. Idempotent on re-run.
- **Noise filter** — capture skips Claude Code's internal scratch paths
  (`AppData/Temp/claude`, `~/.claude/projects/`, `/tmp/claude`).
- `docs/MEISTER_CLI.md` — full CLI reference and event schema.

### Changed
- README hero section now leads with the cross-tool wedge, positioning Meister
  as a memory layer that follows the repo, not the tool.
- `.gitignore` now excludes `.repo_memory/` — the live conversation log
  contains user prompts and must not ship with any repo.

### Security
- Capture hooks apply a regex scrubber on `api_key|token|secret|password`
  patterns before writing summaries to disk. This is not a comprehensive
  secret scanner. If your repo handles credentials, gitignore `.repo_memory/`
  or run a real scanner before committing.

## v1.4.0 — 2026-04-19

### Added
- **`tokens_saved` runtime metric** — `usage_logger.py` now records
  `components_loaded`, `tokens_loaded`, `tokens_saved`, and
  `baseline_tokens` on every task. Savings are computed against a naive
  baseline of 5879 tokens — what loading every runtime component on
  every task would cost. `usage_report.py` surfaces total saved, per-task
  average, savings rate, and per-mode breakdown. `runtime_loader.py`
  embeds `--components-loaded` into the post-task command so the metric
  populates automatically. Older log records are backfilled on the fly
  from `components_loaded` + `memory_tokens` so historical data still
  contributes.

### Fixed (Pre-Ship Hardening Sweep)
- **`runtime_loader.py`** — `tools_dirs: []` no longer raises `IndexError`;
  advisor-script path now uses `Path` joining instead of fragile string
  concatenation.
- **`memory_controller.py`** — Honors both `path` and `file_path` keys in
  the index (schema mismatch was making every entry fall through to its
  truncated `content` field). Added a `relative_to(memory_root)` boundary
  check that turns this into a sandboxed reader instead of an
  arbitrary-file-read primitive when the index is tampered with.
- **`repo_detector.py`** — New `sanitize_repo_name()` collapses unsafe
  chars, rejects `.` / `..` / empty, and caps length. Wired into both
  `detect_repo_name()` and `ensure_repo_dirs()` so a malicious repo name
  can no longer escape `~/.claude_memory/repos/`.
- **`memory/server/main.py`** — `import memory_store` no longer collides
  with the `@mcp.tool() def memory_store(...)` definition. Aliased to
  `memory_store_mod` so the tool can actually call `store_entry()` at
  runtime instead of raising `AttributeError`.
- **`cleanup.py`** — `freed_bytes` is no longer always 0. File sizes are
  captured *before* `unlink()` and stored on each removed record, then
  summed at the end.
- **`docs/wiki-pipeline-guide.md`** — Three references to the wrong
  config path (`~/.claude_meister/runtime_config.json`) corrected to
  `~/.claude_runtime/configs/runtime_config.json`.

## v1.3.0 — 2026-04-18

### Added
- **`install.py --inject-here`** — Inject the runtime block into a per-repo
  `./CLAUDE.md` instead of your global one. Useful for project-specific
  customization without touching the global config.
- **Smart block selection via `installer/repo_scanner.py`** — Profiles the
  current repo (primary language, size bucket, test presence) in a bounded
  single-pass walk. Small repos without tests get the new
  `claude_md_block_minimal.md`; everything else gets the full block.
- **Memory tiering** — Every memory entry carries a `tier` field
  (`hot` / `warm` / `cold`). Promotion: `frequency >= 5` and
  `success_rate >= 0.8` (None treated as neutral). Demotion beats
  promotion — an entry unused for 60+ days demotes to `warm`, 180+ days
  to `cold`. `memory_retrieve` boosts hot entries, penalizes cold, and
  only surfaces cold entries when the query strongly matches.
- **Cross-repo failure registry** — `memory/server/failure_registry.py`.
  Every unsuccessful outcome logged via `memory_evolve` now registers a
  compact signature (failure type + distilled error tokens). On future
  `memory_retrieve` calls, matching past failures surface in a new
  `avoid:` section of the result so we don't repeat the same mistake
  across projects. Stored at `~/.claude_memory/failure_registry.json`,
  capped at 200 entries.
- **`memory_status` tier distribution** — Health dashboard now reports
  hot/warm/cold/untiered counts per repo and overall.

## v1.2.0 — 2026-04-18

### Added
- **Query intent pre-classifier** — `memory/server/intent_classifier.py`.
  Keyword buckets route queries into `code`, `architecture`, `debug`,
  `decision`, or `general`. Entries carrying a matching intent get a
  1.15x score boost during retrieval. No LLM calls — fully local.
- **Tool capability index** — `runtime/controllers/build_tool_index.py`
  generates `tool_index.json` from every directory listed in
  `tools_dirs`. `tool_loader.py --query` now consults the index first
  (deterministic, capability-weighted scoring) and falls back to the
  original docstring walk on a miss, on `--scan-dir` override, or on
  explicit `--no-index`. New `--rebuild-index` flag regenerates on
  demand; `install.py --update` also rebuilds automatically.
- **Runtime feedback loop** — `usage_logger.py` records now carry `id`,
  `success` (tri-state: true/false/null), and `outcome_note` fields.
  New `--finalize <id> --success true|false` flow updates an earlier
  record's outcome. `--stats` now reports `success_rate_by_mode`.

### Changed
- `memory_retriever.py` lazily backfills `intent` on first access for
  legacy entries missing the field.

## v1.1.0 — 2026-04-18

### Added
- **Memory deduplication via `content_hash`** — `memory_store`
  normalizes content (lowercase, whitespace-collapsed) and hashes it with
  SHA-256. Subsequent stores of the same content in the same repo/type
  bump `frequency` and `last_used` on the existing entry instead of
  creating duplicates. Outcomes are exempt (each failure is its own
  event).
- **Input validation** — `store_entry()` fast-fails on empty content,
  non-list tags, invalid types, or missing repo. Malformed calls no
  longer leak garbage entries into the index.
- **Observability aggregation** — `runtime/controllers/usage_report.py`
  reads `runtime_usage.json` and emits a text-table (or `--json`)
  summary: tasks per mode, average tokens, top tools, memory hit rate,
  rolling windows via `--days N`.

### Fixed
- **`install.py --update` now refreshes the CLAUDE.md runtime block**
  when markers are present. Previously, `--update` refreshed runtime,
  memory, and wiki files but left the injected block stale.

## v1.0.0 — 2026-04-16

Initial distributable release.

### Included
- **Runtime engine** at `~/.claude_runtime/` — LIGHT / STANDARD / DEEP
  mode routing, context router, token budgeting, tool loader, usage
  logger.
- **Global memory** at `~/.claude_memory/` — MCP server with store,
  retrieve, evolve, debate, cleanup, status tools. Scored entries with
  recency, frequency, and success weighting.
- **Wiki** at `~/.claude_wiki/` — tiered knowledge base with
  `_hot.md` + `index.md` + per-topic files.
- **CLAUDE.md injection** — runtime block with
  `<!-- RUNTIME:START --> / <!-- RUNTIME:END -->` markers that
  `install.py --update` refreshes in place; timestamped backups on
  every write.
- **Installer** — `install.py` with `--full`, `--runtime-only`,
  `--memory-only`, `--wiki-only`, `--update`, `--uninstall`, `--verify`,
  `--stats` modes. Windows-first path handling with macOS/Linux parity.
