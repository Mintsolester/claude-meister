"""Meister — platform-independent conversation memory for AI coding tools.

Captures the turns you have with Claude Code / Cursor / Codex / Aider into a
repo-local `.repo_memory/conversation.jsonl` and surfaces them back via a CLI
and an MCP server. Layered retrieval (L0 -> L1 -> L2) keeps recall cheap.
"""

__version__ = "0.1.0"
