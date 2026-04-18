# Ship Guide

Steps to push this repo to GitHub and make it public. Do these in order.

## 1. Pre-flight (verify locally)

```bash
cd <repo>
python install.py --verify          # all 24 checks pass
python tests/test_installer.py      # 8 groups pass
python tests/test_memory_server.py  # 7 groups pass
python tests/test_usage_report.py   # 5 groups pass
python tests/test_runtime.py        # 171 pass / 2 known CLAUDE.md size fails (non-blocking)
git status                          # working tree clean
```

## 2. Confirm the remote

```bash
git remote -v
# Expect: origin  https://github.com/Mintsolester/claude-meister.git
```

If the remote is missing or wrong:
```bash
git remote add origin https://github.com/Mintsolester/claude-meister.git
# or
git remote set-url origin https://github.com/Mintsolester/claude-meister.git
```

## 3. Create the GitHub repo (one-time)

If the repo at https://github.com/Mintsolester/claude-meister doesn't exist yet:

- Go to https://github.com/new
- Owner: `Mintsolester`
- Repository name: `claude-meister`
- Visibility: **Public**
- **Do not** initialize with README, .gitignore, or license — you already have all three
- Click **Create repository**

If it already exists but is private: Settings → General → scroll to "Danger Zone" → **Change visibility** → Public.

## 4. Push code and tags

```bash
git push -u origin master
git push origin --tags
```

`master` is the long-lived branch on this repo; the five tags (`v1.0.0` through `v1.4.0`) carry the release history.

## 5. Cut the v1.4.0 GitHub Release

- Open https://github.com/Mintsolester/claude-meister/releases/new
- **Choose a tag:** `v1.4.0` (already pushed)
- **Release title:** `v1.4.0 — Pre-ship hardening + tokens_saved metric`
- **Description:** copy the `## v1.4.0` section verbatim from `CHANGELOG.md`
- Leave "Set as the latest release" checked
- **Publish release**

## 6. Polish the repo page

- Add a **Description** (top of repo page, gear icon next to "About"):
  > Claude Code runtime + global memory + wiki + injector. Cuts per-task token use ~99% in LIGHT mode vs naive load.
- Add **Topics**: `claude-code`, `claude`, `anthropic`, `mcp`, `agent-runtime`, `memory`, `python`
- Add **Website** field (optional): link to a demo or your X profile
- Pin the repo to your GitHub profile

## 7. Announce

Lead with the install one-liner from `README.md`. Suggested channels:

- **r/ClaudeAI** on Reddit — focused, active, friendly to power-user tooling
- **Anthropic Discord** → `#community-projects` channel
- **X / Twitter** — tag `@AnthropicAI`, use `#ClaudeCode`
- **Hacker News** — `Show HN:` if you want broader (less Claude-specific) reach

Suggested 1-line pitch:

> Claude_Meister is a runtime + global memory layer for Claude Code that has saved my last 14 tasks an average of 5,843 tokens each (99.4% vs naive load). MIT-licensed, Windows + macOS + Linux.

## 8. After release

- Watch the **Issues** tab — first reports usually surface install-path edge cases
- Add regression tests for any bug reports before fixing them
- Cut a `v1.4.1` patch if a critical bug appears in the first 48 hours

That's it. Total time: ~15 minutes once the repo exists.
