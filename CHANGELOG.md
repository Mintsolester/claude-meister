# Changelog

All notable changes to Claude_Meister are documented here. This project
follows [Semantic Versioning](https://semver.org/).

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
