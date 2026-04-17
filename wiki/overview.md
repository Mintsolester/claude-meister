---
title: Overview
type: overview
created: 2026-04-09
updated: 2026-04-09
sources: []
tags: [overview, meta]
---

# Overview

This wiki is a structured knowledge base covering the **Anthropic/Claude ecosystem**, built from 307 raw documentation pages.

## The Ecosystem at a Glance

**Anthropic** builds Claude, a family of large language models. The ecosystem has five major components:

### 1. [[claude-models|Claude Models]]
Three current tiers: **Opus 4.6** (most intelligent, $5/$25 MTok), **Sonnet 4.6** (fast + smart, $3/$15 MTok), **Haiku 4.5** (fastest, $1/$5 MTok). All support text+image input, up to 1M token context. Key innovation: [[adaptive-thinking|adaptive thinking]] where Claude dynamically decides reasoning depth.

### 2. [[claude-api|Claude API]]
REST API at `api.anthropic.com`. Core endpoint: Messages API. Also: Batches (50% discount), Files, Token Counting, Models, Skills (beta). Available via Anthropic direct, AWS Bedrock, Google Vertex AI, Microsoft Foundry.

### 3. [[claude-code|Claude Code]]
Agentic coding tool that reads codebases, edits files, runs commands. Available as CLI, VS Code/JetBrains extensions, desktop app, web app. Works through an agentic loop: gather context → take action → verify results. Extensible via CLAUDE.md, skills, hooks, subagents, MCP, plugins.

### 4. [[agent-sdk|Agent SDK]]
Build production agents with Claude Code's tools as a library. Python and TypeScript. Same agentic loop and tools, programmable.

### 5. [[mcp|Model Context Protocol]]
Open standard for connecting AI to external systems. Client-server architecture with tools, resources, and prompts as primitives. Supported across Claude, ChatGPT, VS Code, Cursor, and many others.

## Key Cross-Cutting Concepts

- [[context-windows|Context Windows]] — The fundamental constraint. 1M tokens available, but quality degrades as context fills.
- [[adaptive-thinking|Adaptive Thinking]] — Claude decides when/how much to reason. Effort parameter controls depth.
- [[tool-use|Tool Use]] — Client-side (you execute) and server-side (Anthropic executes) tools.
- [[prompt-engineering|Prompt Engineering]] — Be clear, use examples, structure with XML, give roles, verify.
- [[pricing-and-costs|Pricing]] — Token-based. Batch (50% off), caching (90% off reads), fast mode (6x).
- [[agentic-patterns|Agentic Patterns]] — Explore→Plan→Execute, subagent delegation, fan-out, verification.

## Current State
- **307 raw sources** cataloged in the index
- **5 entity pages** covering the major products/components
- **6 concept pages** covering key ideas and patterns
- **~20 core files deeply read**, remaining files cataloged by topic for future deep-dive

## Open Questions
- How do the various SDK languages compare in feature parity?
- What are the specific MCP server implementations most valuable for common workflows?
- How does computer use (beta) perform in practice vs. traditional tool use?
- What are the real-world cost profiles for different agent architectures?
