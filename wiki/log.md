---
title: Wiki Log
type: log
created: 2026-04-09
updated: 2026-04-09
---

# Wiki Log

Chronological record of all wiki operations.

## [2026-04-09] reorganize | Wiki Initialization
Set up the LLM Wiki structure. Created: CLAUDE.md (schema), wiki/index.md, wiki/log.md, wiki/overview.md. Established directory conventions: sources/, entities/, concepts/, comparisons/, guides/, queries/. ~307 raw Anthropic/Claude docs available for ingestion in raw/.

## [2026-04-09] ingest | Bulk Ingestion of 307 Raw Sources
**Tier 1 foundation files deeply read (~20 files):** Intro to Claude, Get started with Claude, Models overview, Choosing the right model, What's new in Claude 4.6, Context windows, Claude Code overview, How Claude Code works, Best Practices for Claude Code, Features overview, API Overview, What is MCP, Architecture overview, Agent SDK overview, Prompt engineering overview, Prompting best practices, Common workflows, Pricing, Using the Messages API, Tool use with Claude.

**All 307 raw files cataloged** in the index by topic category: Claude Models & Core, Claude Code, API & Messages, Tools & Capabilities, Agent SDK & Skills, MCP, Prompt Engineering & Security, Enterprise & Admin, Admin API Endpoints, SDKs & Platforms, Models API, Tutorials.

**Wiki pages created:**
- Entities: [[claude-models]], [[claude-code]], [[claude-api]], [[agent-sdk]], [[mcp]]
- Concepts: [[prompt-engineering]], [[tool-use]], [[context-windows]], [[adaptive-thinking]], [[pricing-and-costs]], [[agentic-patterns]]
- Updated: [[overview]], [[index]]

**Key insights from ingestion:**
- Claude 4.6 represents a major shift: adaptive thinking replaces budget_tokens, prefill removed on Opus, effort parameter is GA
- Context management is the fundamental constraint across all products
- The ecosystem is deeply interconnected: Claude Code uses the API, which uses tools, which can connect via MCP
- Pricing is competitive: Opus 4.6 at $5/$25 is 3x cheaper than Opus 4.1 at $15/$75

## [2026-04-09] reorganize | Retrieval Protocol Optimization
Replaced flat 4-step retrieval with tiered 5-step protocol to reduce token cost per query. Changes:
- **CLAUDE.md** — New retrieval protocol: _hot.md → index.md (lean) → domain sub-index → grep fallback → 5-page limit
- **index.md** — Slimmed from ~350 lines to ~60 lines. Removed raw source catalog. Added "Recently Active" section and domain sub-index pointer table.
- **Created 8 domain sub-indexes:** _index-models (18), _index-claude-code (52), _index-api (32), _index-tools (36), _index-agent-sdk (36), _index-mcp (26), _index-prompting (10), _index-enterprise (49)
- **_hot.md** — Already existed from prior step. Now formally Step 1 in protocol.
