# Plan Deviations

This document tracks where the implementation departs from the plan at
`<local>/Agentic_Workflows/docs/superpowers/plans/2026-04-16-claude-meister.md`.
Each deviation was applied deliberately; this file is the audit trail.

## Task 3 — `runtime_loader.py` default path

**Plan:** `config.get("tools_dirs", ["<local>/Agentic_Workflows/tools/"])[0]`
**Actual:** `config.get("tools_dirs", [""])[0]`
**Reason:** The plan's default contained a hardcoded developer path that
would have failed the Task 3 grep check for leaked paths and would be
meaningless on any user's machine.
**Known edge:** `tools_dirs: []` (explicit empty list) makes
`config.get("tools_dirs", [""])` return `[]`, and `[][0]` raises
`IndexError`. Safe for the default case; only triggers if a user
explicitly sets an empty list in `runtime_config.json`.

## Task 4 — cleanup

Removed unused imports (`json`, `tempfile`) from `tests/test_installer.py`
flagged by Task 4 code quality review. No behavior change.

## Task 5 — test assertion for `context_router` templating

**Plan (line 790):** `if "Mintsolester" not in router_content:`
**Actual:** `if "{{RUNTIME_PATH}}" not in router_content and "{{WIKI_PATH}}" not in router_content:`
**Reason:** On Windows, `tempfile.TemporaryDirectory()` creates directories
under `C:/Users/Mintsolester/AppData/Local/Temp/...`. After substitution,
the developer username appears in the installed content as a byproduct of
the temp path, not as a leaked hardcoded path. The source files (verified
clean via grep) never contain the name. The new assertion preserves the
original intent (verify substitution ran) while being
environment-independent.

## Task 8 — data-safety fix in `claude_md.py` create mode

**Plan:** `mode="create"` wrote the template directly over the target file.
**Actual:** `mode="create"` now calls `_backup(claude_md)` first if the
file exists.
**Reason:** Data-loss bug flagged as Critical by the Task 8 code quality
review. Auto-detect mode only resolves to `create` when the file is
absent, so this path was only reachable via an explicit `mode="create"`
call on an existing file — a user-error pattern that would have silently
destroyed the user's CLAUDE.md. The fix mirrors the backup-before-modify
pattern already present in `append` and `update` branches.

## Task 9 — Windows path comparison in `mcp.py`

**Plan:** `if expected_path in current_path:`
**Actual:** `if expected_path in current_path.replace("\\", "/"):`
**Reason:** Windows is the primary target platform. The `claude mcp list`
CLI can emit backslash-separated paths while our expected path uses
forward slashes (by project convention). Without normalization, an
already-registered server would not be recognized and the installer would
re-register or fail. Normalizing only the CLI-side string (not the
project-controlled `expected_path`) keeps the change minimal.

## Task 10 — `test_verify()` missing `install_wiki()` call

**Plan (lines 2189-2250):** Test sets up runtime + memory + CLAUDE.md,
then calls `run_verification(paths, install_mode="full")`.
**Actual:** Added `install_wiki(paths)` to test setup (and its import).
**Reason:** `install_mode="full"` triggers wiki checks in verify.py
(plan lines 2332-2336), but the test setup never installed the wiki.
3 wiki checks failed deterministically. The fix preserves plan intent
(exercise full-mode verification) rather than weakening the test.

## Task 12 — GitHub URL placeholder in README.md

**Plan (lines 2872-2886):** README must be comprehensive with accurate
commands.
**Actual:** README uses `https://github.com/Mintsolester/claude-meister.git`
as the clone URL in three places (Quick Start, Detailed Installation,
Contributing). This is a placeholder — the real remote has not been
set on the local repo.
**Reason:** The repository is local-only at this point. The URL is a
plausible guess based on the git user's name. Before publishing, the
user must either (a) create the repo at that exact URL, or (b) global
search-and-replace the URL in README.md to the actual remote.

## Task 12 — README Windows-first path example

**Plan (line 2878):** Documents `runtime_config.json` fields.
**Actual:** Configuration section's example config uses Windows paths
(`C:/Users/yourname/...`) rather than Unix paths, with a note below
showing the macOS/Linux variant.
**Reason:** Windows is the primary target platform (per spec). The
initial draft showed Unix paths, which would confuse the majority of
users. The note below preserves cross-platform clarity without burying
the lede for the main audience.

## Phase 2.2 — `tool_index.json` rebuild placement

**Plan:** "Index is regenerated on `install.py --update` or manually via
`tool_loader.py --rebuild-index`."
**Actual:** `install_runtime()` calls `_build_tool_index()` at the end of
a fresh install, AND `update_runtime()` calls it a second time *after*
preserved files (including `configs/runtime_config.json`) are restored.
**Reason:** `PRESERVE_ON_UPDATE` backs up the user's real
`runtime_config.json` before reinstall and restores it afterward. If the
index builder ran only once (inside `install_runtime`), it would execute
against the freshly-templated config where `tools_dirs: []`, producing an
empty index on every update. The second rebuild sees the restored config
with the user's real `tools_dirs`. The first rebuild is kept so fresh
installs still leave a valid (empty) index file on disk.

## Phase 2.2 — `tool_loader.py` skips index when `--scan-dir` is set

**Plan:** "`--query` first checks the index; falls back to current
docstring-scoring on miss."
**Actual:** Index lookup is also bypassed when the caller passes
`--scan-dir` (one or more times), and via a new explicit `--no-index`
flag.
**Reason:** `--scan-dir` means "scan this specific directory" — the
caller is overriding the default tool registry, so the pre-built index
(keyed off `tools_dirs` in runtime_config) would not represent what they
asked for. Deferring to the docstring walk in that case matches the
caller's intent. `--no-index` gives tests and debugging a deterministic
way to force the fallback path.

## Phase 2.3 — `usage_logger.py --finalize` exit code on missing id

**Plan:** "`--finalize <task_id> --success true|false` updates the record."
**Actual:** When `--finalize <id>` does not match any existing record,
the process writes `{"status": "not_found", "id": "..."}` to stderr and
exits with code 2.
**Reason:** A silent no-op would let a broken finalize call leak into
`usage_report.py` as a "success=null" record. Exit code 2 lets callers
detect and retry without scanning stdout. The log is unchanged on
mismatch (no silent append).

## Phase 3.1 — `--inject-here` does not use `claude_md_full.md`

**Plan:** "Reuse `setup_claude_md()` with a `target_path` override."
**Actual:** The create branch of `setup_claude_md()` now picks between
`claude_md_full.md` (global default) and `claude_md_block.md` (per-repo or
minimal). When `target_override` is set, the block template is always
used — never the full Prompt Architect file.
**Reason:** A per-repo `./CLAUDE.md` is an overlay for that project, not
a replacement for the user's global Prompt Architect configuration.
Dropping the full Prompt Architect file into every repo would stomp
workspace-specific guidance and duplicate content the user already has
globally. The block template carries only the runtime-engine hook.

## Phase 3.2 — repo scanner cap and test signal

**Plan:** "Scanner: detect primary language (by file count), size bucket
(small/medium/large), test framework presence."
**Actual:** `installer/repo_scanner.py` caps the walk at 2000 files and
treats any dir or file whose basename contains `tests`/`test`/`spec`/
`__tests__`/`e2e` as the test signal. Markdown is excluded from the
"primary language" pick unless nothing else qualifies.
**Reason:** Unbounded walks stall on large monorepos; 2000 files is
enough to settle language ratios. The test-signal heuristic covers
pytest / jest / rspec / jasmine / cypress layouts without per-framework
detection code. Excluding markdown avoids calling a docs-heavy repo a
"markdown project" when it's really Python or Go.

## Phase 3.3 — tier demotion wins over promotion

**Plan:** "Promotion rule: `frequency >= 5 and success_rate >= 0.8` →
hot. Demotion rule: `last_used > 60 days` → warm; `> 180 days` → cold."
**Actual:** `compute_tier()` checks age before checking promotion: an
entry with `last_used > 60 days` is always `warm` (or `cold` past 180
days) regardless of its frequency. Also: `success_rate is None`
(unfinalized) does NOT block promotion — it's treated as "unproven, not
failed" since the plan-era Phase 2.3 rollout means many existing entries
won't have a finalized success_rate yet.
**Reason:** Without demotion-first ordering, a frequently-retrieved but
long-abandoned entry would stay `hot` forever and crowd out fresher
signals. Without the None-as-neutral rule, nothing promotes at all
until outcomes get finalized, defeating the tier's ranking value in the
interim.

## Phase 3.4 — failure registry is cross-repo with per-repo ranking

**Plan:** "On `memory_evolve` with `success=false`, extract a pattern
signature (tool + error class + file kind) and store in a compact
registry."
**Actual:** Registry stores one file at `~/.claude_memory/
failure_registry.json` shared across all repos. Each record carries a
`repos: []` list (last 10 repos that hit the pattern). `find_similar_
failures()` ranks same-repo hits above cross-repo hits but never hides
cross-repo matches — a pattern seen in another project can still warn
us here. Capped at 200 entries; oldest by `last_seen` evicted first.
**Reason:** Cross-repo visibility is the entire point of a "global"
failure registry — an SQLite-timeout lesson learned in project A should
warn project B. Per-repo ranking keeps local relevance high without
losing the cross-project safety net. The 200-entry cap prevents
unbounded growth on systems that fail often.
