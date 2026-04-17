---
title: Claude Models
type: entity
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Models overview]]", "[[raw/Choosing the right model]]", "[[raw/What's new in Claude 4.6]]", "[[raw/Pricing]]", "[[raw/Context windows]]"]
tags: [models, claude, anthropic, pricing]
---

# Claude Models

Claude is a family of large language models developed by [[anthropic|Anthropic]]. All current models support text+image input, text output, multilingual capabilities, and vision.

## Current Model Lineup (as of April 2026)

### Claude Opus 4.6
- **ID:** `claude-opus-4-6`
- **Role:** Most intelligent broadly available model. Best for coding, enterprise agents, professional work.
- **Context:** 1M tokens input, 128k tokens max output (300k via Batch API with beta header)
- **Pricing:** $5/MTok input, $25/MTok output
- **Knowledge cutoff:** May 2025 (reliable), Aug 2025 (training data)
- **Key features:** [[adaptive-thinking|Adaptive thinking]], [[extended-thinking|extended thinking]], [[fast-mode|fast mode]] (2.5x speed at $30/$150 MTok)
- **Breaking changes:** Prefill (last-assistant-turn) NOT supported. Returns 400 error.

### Claude Sonnet 4.6
- **ID:** `claude-sonnet-4-6`
- **Role:** Best combination of speed and intelligence. Built for coding, agents, enterprise workflows.
- **Context:** 1M tokens input, 64k tokens max output (300k via Batch API)
- **Pricing:** $3/MTok input, $15/MTok output
- **Knowledge cutoff:** Aug 2025 (reliable), Jan 2026 (training data)
- **Key features:** [[adaptive-thinking|Adaptive thinking]], effort parameter, [[context-awareness|context awareness]]
- **Recommendation:** Set effort to `medium` for most use cases to balance speed/cost/quality.

### Claude Haiku 4.5
- **ID:** `claude-haiku-4-5-20251001` (alias: `claude-haiku-4-5`)
- **Role:** Fastest model with near-frontier intelligence. Best for real-time, high-volume, cost-sensitive tasks.
- **Context:** 200k tokens input, 64k tokens max output
- **Pricing:** $1/MTok input, $5/MTok output
- **Knowledge cutoff:** Feb 2025
- **Key features:** Extended thinking, [[context-awareness|context awareness]]

### Claude Mythos Preview
- Research preview for defensive cybersecurity (Project Glasswing). Invitation-only.
- 1M token context window.

## Model Selection Guide

| When you need... | Use... |
|---|---|
| Maximum intelligence, complex reasoning, long-horizon agents | Opus 4.6 |
| Fast turnaround + strong intelligence at scale | Sonnet 4.6 |
| Real-time speed, high volume, cost efficiency | Haiku 4.5 |

**Two approaches to model selection:**
1. **Start cheap, upgrade if needed:** Begin with Haiku 4.5, upgrade only for capability gaps
2. **Start smart, optimize later:** Begin with Opus 4.6, then consider downgrading for cost

## Platform Availability

| Platform | Provider |
|---|---|
| Claude API (direct) | Anthropic |
| Amazon Bedrock | AWS |
| Vertex AI | Google Cloud |
| Azure AI / Microsoft Foundry | Microsoft |

Third-party platforms may have feature delays. Starting with Sonnet 4.5+, AWS offers global vs regional endpoints; GCP offers global, multi-region, and regional. Regional endpoints have a 10% premium.

## What's New in Claude 4.6

- **[[adaptive-thinking|Adaptive thinking]]** is the recommended thinking mode (`thinking: {type: "adaptive"}`)
- **Effort parameter** is GA: `low`, `medium`, `high`, `max`
- **[[fast-mode|Fast mode]]** (beta): 2.5x speed for Opus at 6x price
- **[[compaction|Compaction API]]** (beta): server-side context summarization for infinite conversations
- **Code execution free with web tools** when using `web_search_20260209` or `web_fetch_20260209`
- **Fine-grained tool streaming** now GA
- **128k max output** for Opus 4.6
- **Prefill removed** on Opus 4.6 (use structured outputs or system prompts instead)
- **`output_format` deprecated** in favor of `output_config.format`
- **`budget_tokens` deprecated** in favor of adaptive thinking + effort

## Batch Processing Discounts

50% discount on all models via the Batch API:
- Opus 4.6: $2.50/$12.50 MTok
- Sonnet 4.6: $1.50/$7.50 MTok
- Haiku 4.5: $0.50/$2.50 MTok

## See Also
- [[claude-api|Claude API]]
- [[pricing-and-costs|Pricing & Costs]]
- [[adaptive-thinking|Adaptive Thinking]]
- [[context-windows|Context Windows]]
