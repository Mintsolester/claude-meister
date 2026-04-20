# Claude_Meister Plugin

This plugin packages operational skills for the Claude_Meister repository.

It maps directly to workflows that already exist in this codebase:
- Install and update via `install.py`
- Verify health checks with `python install.py --verify`
- Tune behavior using `docs/configuration.md`
- Diagnose failures using `docs/troubleshooting.md`

## Included Skills

- `/install-claude-meister`
- `/verify-claude-meister`
- `/configure-claude-meister`
- `/troubleshoot-claude-meister`

## Repository Prerequisites

- Python 3.8+
- `mcp` and `fastmcp`
- Claude Code CLI

## Typical Flow

1. Clone the repository and open a terminal in the project root.
2. Run full install: `python install.py --full`
3. Verify installation: `python install.py --verify`
4. Inspect usage metrics: `python install.py --stats`
