---
title: Claude API
type: entity
created: 2026-04-09
updated: 2026-04-09
sources: ["[[raw/API Overview]]", "[[raw/Using the Messages API]]", "[[raw/Features overview]]", "[[raw/Pricing]]", "[[raw/Tool use with Claude]]"]
tags: [api, messages, rest, anthropic]
---

# Claude API

RESTful API at `https://api.anthropic.com` providing programmatic access to [[claude-models|Claude models]]. Primary endpoint: `POST /v1/messages`.

## Available APIs

### Generally Available
- **Messages API** (`POST /v1/messages`) — core conversational endpoint
- **Message Batches API** (`POST /v1/messages/batches`) — async processing, 50% cost discount
- **Token Counting API** (`POST /v1/messages/count_tokens`) — pre-send token estimation
- **Models API** (`GET /v1/models`) — list available models and capabilities

### Beta
- **Files API** (`POST /v1/files`) — upload/manage files across calls
- **Skills API** (`POST /v1/skills`) — create/manage custom agent skills
- **Compaction** — server-side context summarization

## Authentication

Required headers:
- `x-api-key`: your API key
- `anthropic-version`: `2023-06-01`
- `content-type`: `application/json`

SDKs handle headers automatically.

## Request Limits

| Endpoint | Max Size |
|---|---|
| Messages, Token Counting | 32 MB |
| Batch API | 256 MB |
| Files API | 500 MB |

## Messages API Patterns

### Basic Request
```python
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}],
)
```

### Multi-turn Conversations
API is stateless — always send full conversation history. Use synthetic `assistant` messages for context.

### Prefill (deprecated on 4.6)
Pre-filling assistant responses is NOT supported on Opus 4.6 / Sonnet 4.6. Use [[structured-outputs|structured outputs]] or system prompts instead.

### Vision
Supports `image/jpeg`, `image/png`, `image/gif`, `image/webp` via base64, URL, or Files API reference. Up to 600 images/PDF pages per request (100 for 200k context models).

## Key Features

| Feature | Status | Description |
|---|---|---|
| [[adaptive-thinking]] | GA | Claude decides when/how much to think |
| [[extended-thinking]] | GA | Step-by-step reasoning before answering |
| [[prompt-caching]] | GA | Reuse processed prompt portions (5m or 1hr) |
| [[structured-outputs]] | GA | Guaranteed JSON schema conformance |
| [[tool-use]] | GA | Client-side and server-side tool execution |
| [[compaction]] | Beta | Server-side context summarization |
| [[context-editing]] | Beta | Tool result clearing, thinking block clearing |
| [[citations]] | GA | Source-grounded responses |
| [[data-residency]] | GA | US-only inference routing (1.1x premium) |
| [[batch-processing]] | GA | Async, 50% discount |
| [[files-api]] | Beta | Persistent file uploads |

## Client SDKs

Official SDKs with automatic auth, type safety, retries, streaming:
- **Python** (`anthropic`)
- **TypeScript** (`@anthropic-ai/sdk`)
- **Java**, **Go**, **Ruby**, **PHP**, **C**

## Third-Party Platforms
- **Amazon Bedrock** — AWS billing/IAM, may have feature delays
- **Google Vertex AI** — GCP integration
- **Microsoft Foundry** — Azure integration

## See Also
- [[claude-models|Claude Models]]
- [[tool-use|Tool Use]]
- [[pricing-and-costs|Pricing & Costs]]
- [[prompt-caching|Prompt Caching]]
