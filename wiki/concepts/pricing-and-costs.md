---
title: Pricing & Costs
type: concept
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/Pricing]]", "[[raw/Pricing 1]]", "[[raw/Manage costs effectively]]"]
tags: [pricing, costs, tokens, billing]
---

# Pricing & Costs

All prices USD. 1 token ≈ 4 characters or 0.75 words in English.

## Model Pricing (per million tokens)

| Model | Input | Output | Batch Input | Batch Output |
|---|---|---|---|---|
| **Opus 4.6** | $5 | $25 | $2.50 | $12.50 |
| **Opus 4.5** | $5 | $25 | $2.50 | $12.50 |
| **Opus 4.1/4** | $15 | $75 | $7.50 | $37.50 |
| **Sonnet 4.6** | $3 | $15 | $1.50 | $7.50 |
| **Sonnet 4.5/4** | $3 | $15 | $1.50 | $7.50 |
| **Haiku 4.5** | $1 | $5 | $0.50 | $2.50 |
| **Haiku 3.5** | $0.80 | $4 | $0.40 | $2 |

## Prompt Caching Multipliers

| Operation | Multiplier | Duration |
|---|---|---|
| 5-min cache write | 1.25x input | 5 minutes |
| 1-hour cache write | 2x input | 1 hour |
| Cache read (hit) | 0.1x input | Same as write |

Pays off after 1 read (5-min) or 2 reads (1-hour).

## Special Pricing

- **Fast mode** (Opus 4.6): $30/$150 MTok (6x standard). Not available with Batch API.
- **Data residency** (US-only): 1.1x multiplier on Opus 4.6+
- **Regional/multi-region endpoints** (AWS/GCP): 10% premium over global
- **Long context** (1M tokens): Standard pricing, no premium

## Tool Pricing

| Tool | Cost |
|---|---|
| Web Search | $10/1000 searches + tokens |
| Web Fetch | Free (tokens only) |
| Code Execution | Free with web tools; $0.05/hr after 1,550 free hrs/month |
| Bash | +245 input tokens |
| Text Editor | +700 input tokens |
| Computer Use | +735 tokens + screenshots |
| Tool use system prompt | ~346 tokens (auto/none) |

## Cost Optimization

1. **Use appropriate models:** Haiku for simple tasks, Sonnet for most, Opus for complex
2. **Prompt caching:** Reuse repeated context
3. **Batch API:** 50% discount for async processing
4. **Monitor usage:** Track token consumption
5. **Effort parameter:** Lower effort = fewer thinking tokens
6. **Subagents in Claude Code:** Isolate research to avoid context bloat

## Agent Example

10,000 support tickets with Opus 4.6 (~3,700 tokens/conversation): **~$37 total**

## See Also
- [[claude-models|Claude Models]]
- [[prompt-caching|Prompt Caching]]
- [[context-windows|Context Windows]]
