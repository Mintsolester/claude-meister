# Contributing to Claude_Meister

First time contributing to OSS? Great — this project is friendly to first
PRs. The shortest path is below.

## TL;DR

1. **Fork** the repo on GitHub.
2. **Clone your fork** locally and create a branch: `git checkout -b fix/short-name`.
3. **Make the change.** Keep it focused — one logical change per PR.
4. **Test it locally:** `python -m meister doctor`, plus any commands relevant to your change.
5. **Commit:** `git commit -m "fix(scope): one-line summary"` (Conventional Commits).
6. **Push to your fork** and open a PR against `master`.
7. **Respond to review feedback** within ~3 days; we'll merge or close politely if it goes stale.

## Project layout

```
meister/              The v2 CLI + capture hooks (Python, no deps)
memory/server/        The v1 MCP server (FastMCP-based)
runtime/              The v1 intelligence runtime (mode routing, token budget)
installer/            install.py support modules
templates/            CLAUDE.md blocks and config templates
docs/                 Reference docs (MEISTER_CLI.md, LAUNCH_PLAYBOOK.md, etc.)
plugins/              Plugin distribution
tests/                Test suite
```

## Good first issues

Look for the `good-first-issue` label on the [issues
page](https://github.com/Mintsolester/claude-meister/issues). If there are
none open, here are durable starter areas:

- **Add a Cursor adapter** — normalize Cursor's chat transcript format to our
  event schema. See `docs/MEISTER_CLI.md` for the schema.
- **Add a `meister export --markdown` command** — render a session as
  human-readable markdown.
- **Improve the noise filter** — replace the substring blocklist in
  `meister/capture.py` with a positive allowlist (only capture paths inside
  the repo root).
- **Add a `.repo_memory/ignore` glob file** — user-controlled exclusions.
- **Test on macOS / Linux** — Windows is the dev box; we want bug reports
  from other platforms.

## Style

- Python 3.10+. No black/ruff config yet — match the style of the surrounding
  file. Type hints encouraged but not required.
- One change per PR. If you found three bugs, send three PRs.
- Tests welcome but not blocking. The MVP runs without a test suite.
- Comments only when WHY is non-obvious. The code should explain WHAT.

## Commit message format

Conventional Commits, lowercase scope:

```
feat(meister): add recall --since flag
fix(capture): handle missing tool_input on Bash
docs(readme): clarify install-hooks requires Python on PATH
```

Types we use: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

## What gets merged fast

- Bug fixes with a clear repro
- Documentation improvements
- Cross-platform fixes (especially macOS/Linux)
- New adapters for Cursor / Codex / Aider

## What needs discussion first

Open an issue before sending a PR for:

- New CLI commands (we want to keep the surface small)
- Schema changes to `conversation.jsonl` (back-compat matters once we have
  any users)
- New runtime dependencies (we ship zero today and want to keep it that way
  for the MVP)

## Security

If you find a security issue (path traversal in the capture hook, secret
leak in the noise filter, etc.) please **do not open a public issue**. Email
the repo owner via their GitHub profile or open a [private security
advisory](https://github.com/Mintsolester/claude-meister/security/advisories/new).

## Code of Conduct

Be kind, be specific, assume good faith. We follow the [Contributor
Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Disagreements are fine; disrespect is not. Maintainers reserve the right to
moderate comments and close threads that aren't productive.

## License

By contributing you agree your contribution is licensed under the project's
MIT license.
