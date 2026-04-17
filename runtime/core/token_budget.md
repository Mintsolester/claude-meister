# Token Budget Guidelines

These are advisory guidelines. You cannot count tokens precisely mid-conversation, but you can estimate: ~1.3 tokens per word, or use the `estimate_tokens()` function in memory tools.

## Budget by Mode

| Mode | Extra Context Files Loaded | Memory Budget | Response Target |
|------|---------------------------|--------------|-----------------|
| LIGHT | 0 (no runtime files) | 0 tokens | < 250 words (~325 tokens) |
| STANDARD | 1-2 runtime files | 500 tokens max | Proportional to task |
| DEEP | Context router + relevant refs | 500 tokens max | No artificial limit |

## Hard Rules (Enforceable)

These are not advisory — they are actual limits enforced by tools or design:

1. **Memory retrieval:** Never exceed 500 tokens. Pass `--max-tokens 500` to memory_controller.py. The MCP memory_retrieve tool also enforces this cap internally.

2. **Wiki reads:** Maximum 5 pages per query. Start with `_hot.md`, stop as soon as you have your answer.

3. **File reads:** Use `offset` and `limit` parameters on files over 200 lines. Never read a full 5000-line file.

4. **No re-reads:** If a file is already in conversation context from a previous Read, do not read it again.

5. **Batch tool calls:** Make independent tool calls in parallel. Don't serialize calls that have no dependencies.

## Behavioral Guidelines (Advisory)

1. **LIGHT mode responses** should be under 250 words. A typo fix needs one sentence, not three paragraphs.

2. **STANDARD mode** should load only the runtime files that context_router.md directed. Don't read mode_selector.md AND token_budget.md AND skill_router.md for every moderate task — only what's relevant.

3. **DEEP mode** has no response length limit, but should still be concise. Thorough does not mean verbose. Explain what matters, skip what doesn't.

4. **Memory storage:** Entries must be compressed to max 200 tokens. Strip filler words. Store decisions and patterns, not raw logs.
