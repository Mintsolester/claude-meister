# Launch copy — paste-ready templates

Every post you need to make is below. Replace `[DEMO_GIF]` and `[DEMO_VIDEO]`
placeholders with your actual links. Do not improvise — these are tuned for
each platform's culture.

---

## 1. Reddit `/r/ClaudeAI` (soft launch, Sunday 6-8pm ET)

**Title** (140 char limit, no clickbait, no emoji):

```
Built a memory layer for Claude Code that auto-seeds from git history — feedback wanted before wider launch
```

**Body:**

```
Claude Code forgets between sessions. CLAUDE.md helps but it's static. I built `meister` — a repo-local conversation memory that captures every turn and, on first install, backfills 50 sessions from your git log so you never see an empty state.

Why I think this is different: it's MCP + CLI, so the same memory works in Cursor and Codex too. Repo-local plaintext JSONL — no cloud, no embeddings to install. ~1k LOC.

[DEMO_GIF]

Repo: https://github.com/Mintsolester/claude-meister

Honest asks:
1. Does the first-run feel magical or empty for you?
2. What's missing for it to replace your current memory hack?
3. Roast my README structure.
```

**Rules:** Don't crosspost the same day. Respond to every top-level comment
within 1 hour. If a mod flags it, fix and re-submit politely; don't argue.

---

## 2. Hacker News Show HN (hard launch, Tuesday 8:00am ET)

**Title** (80 char limit, must start with "Show HN:"):

```
Show HN: Meister – Cross-tool conversation memory for AI coding agents
```

**URL field:** `https://github.com/Mintsolester/claude-meister`

**Text field:** *leave blank* — HN convention is to put the explanation in
the first comment, not the submission body.

**First comment** (post yourself, immediately after submission):

```
Hi HN, author here.

I built this because Claude Code, Cursor, and Codex all forget between sessions, and each ships its own incompatible memory format. Meister captures turns into a repo-local `.repo_memory/conversation.jsonl` and serves them back via MCP + CLI, so your memory follows the repo, not the tool.

Three things I think are non-obvious:

1. Layered retrieval (L0 -> L1 -> L2). Default recall returns one-line session titles, not full content. Memory cost stays bounded as history grows. Most memory tools return everything every time.

2. Git-history backfill. Brand-new install reads your last 50 commits and synthesizes sessions from them, so `meister last` is never empty on day one.

3. Fails open. Capture hooks swallow every exception, exit 0. They cannot block your tool calls. Plaintext JSONL on disk — `cat`, `gitignore`, `rm -rf` are all valid ways to inspect/remove.

Limitations I'll mention before you find them:
- Tested heavily with Claude Code, lightly with Cursor (MCP path), not yet with Codex/Aider.
- TF-IDF only — no embeddings. Adequate for the layered design; not a Mem0 replacement.
- Windows is the dev box; macOS/Linux should work but I want bug reports.

What I want from this thread: bug reports, "this won't scale because ___", and your honest answer on whether the layered-recall idea is novel or whether I missed prior art.
```

**Rules:**
- One submission only. If it doesn't gain traction in 2 hours, you can't repost the same URL.
- Reply to every comment within 30 minutes during the first 4 hours. HN's ranking algorithm rewards OP engagement.
- Never argue. Acknowledge, clarify, fix, thank.

---

## 3. X / Twitter thread (launch day, within 2 hours of HN post)

**Tweet 1** (with attached MP4):

```
Your AI assistant forgets everything between sessions.

I built `meister` — a memory layer that captures every turn into your repo and works across Claude Code, Cursor, Codex, and Aider.

Demo (60s, no sound):

[DEMO_VIDEO]

🧵
```

**Tweet 2:**

```
The wedge:

Anthropic's memory is Claude-only.
Cursor's memory is Cursor-only.

Meister's `.repo_memory/conversation.jsonl` is the *repo's* memory. Open it. Read it. Commit it. Gitignore it. Whatever you want.

Your memory follows the repo, not the tool.
```

**Tweet 3:**

```
The trick: layered retrieval.

Most memory tools dump everything at every call. Meister returns one-line session titles first (~50 tokens), expanded detail on drill-down (~300 tokens), raw event stream only on demand.

Recall cost stays bounded as history grows.
```

**Tweet 4:**

```
First-run is never empty.

`meister install-hooks` auto-seeds your memory from the last 50 git commits, so day-one `meister last` already shows you what you've been working on.

It feels like the tool already knew.
```

**Tweet 5:**

```
Open source, MIT, ~1k LOC, zero external dependencies.

Repo: https://github.com/Mintsolester/claude-meister

Honest feedback wanted. Especially: does this solve a real pain for you, or did I build a thing nobody needs?
```

**Posting:** Use [Typefully](https://typefully.com) (free) to schedule the
thread atomically — manually pasting tweets one at a time loses ~30% engagement
per tweet because they're not chained.

Tag @AnthropicAI, @cursor_ai, @sama, @karpathy — only if you've earned the
right (don't @-spam strangers). Tagging is optional.

---

## 4. Cold DM to dev YouTubers / influencers

**Targets** (10 best, ranked by likely fit):

1. Theo Browne (@t3dotgg) — covers AI coding tools weekly
2. Fireship — broad reach, may cover if novel angle
3. ThePrimeagen — only if the demo is *very* tight
4. Cody.dev (the YouTuber, not Sourcegraph)
5. Mckay Wrigley (@mckaywrigley) — builds AI tools
6. Jason Liu (@jxnlco) — RAG / memory specialist
7. Continue.dev's team — may RT or feature in their newsletter
8. Aider's @paulgauthier — author of Aider, would care about cross-tool angle
9. Cline / Cursor community managers
10. @swyx — known to RT good dev tools

**Template** (one-shot, no follow-up if no reply):

```
Hi [name],

Big fan of [specific recent thing they made — must be real, not generic].

Built a thing that might fit your audience: a memory layer for AI coding tools that works across Claude Code, Cursor, and Codex (not just one). Auto-captures every turn into a repo-local JSONL, layered retrieval keeps recall cheap.

60-second demo: [DEMO_VIDEO]
Repo: https://github.com/Mintsolester/claude-meister

No ask — just thought you might find the cross-tool angle interesting. If you'd ever cover something like this, happy to answer questions.

— [your name]
```

**Rules:**
- Personalize the first line. Generic openers get ignored.
- ONE message. No follow-up. Not even one.
- Don't pitch a sponsorship or paid placement.
- Expect 0-1 responses out of 10. The one response is worth 10k users.

---

## 5. Blog post — *"Why memory recall costs more than you think"*

Cross-post to dev.to, hashnode.com, lobste.rs (if you have an invite), and
your own blog. **Different from the HN/Reddit pitch** — this sells the *idea*
(layered recall), not the product.

**Title:**

```
Why memory recall costs more than you think — and how layered retrieval fixes it
```

**Outline** (write ~1000-1500 words):

1. **The problem** (200 words) — AI coding agents are gaining memory, but
   every retrieval pulls full content. Show a hypothetical: 100 past sessions
   × 500 tokens = 50k tokens per recall query. That's $0.15 per `recall` call
   on Claude Sonnet. Not sustainable.

2. **The mental model** (300 words) — borrow the
   directory-listing-then-`cat` flow that devs already use on the shell.
   Why don't we do the same with memory? Define L0 (titles), L1 (expansion),
   L2 (raw). Diagram.

3. **The implementation** (400 words) — show how Meister does it. Code
   snippet from `retrieve.py` showing the `recall()` → `expand_session()` →
   `raw_events()` chain. Walk through a real query example.

4. **The trade-off** (200 words) — what you give up: you need TWO calls
   instead of one to drill in. Argue this is *the same* trade-off you
   already accept with `ls` then `cat`.

5. **Try it** (100 words) — install link, GitHub, "I'd love feedback."

**Distribution:**
- dev.to with tags `#ai`, `#opensource`, `#productivity`, `#tools`
- hashnode with same tags
- Cross-post to your own blog (Substack / personal site) with canonical URL
  set to the original
- Submit to lobste.rs *only* if you have an invite — submitting your own
  blog without one is poor etiquette
- Submit to HN ~3-5 days *after* the Show HN, only if Show HN flopped

---

## 6. Awesome-list PR

**Lists to submit to** (one PR each, separate days):

| List | URL | What they look for |
|---|---|---|
| awesome-claude-code | github.com/hesreallyhim/awesome-claude-code | Tools/plugins for Claude Code |
| awesome-mcp-servers | github.com/punkpeye/awesome-mcp-servers | MCP servers |
| awesome-ai-coding | github.com/sourcegraph/awesome-code-ai | AI coding tools, broad |
| awesome-cli-apps | github.com/agarrharr/awesome-cli-apps | If you have a strong CLI |

**PR template:**

```markdown
Adds meister — cross-tool conversation memory for AI coding agents.

- Repo: https://github.com/Mintsolester/claude-meister
- One-line: Captures every turn into a repo-local JSONL, layered retrieval
  keeps recall cheap, works across Claude Code / Cursor / Codex via MCP.
- License: MIT
- Active: yes, v2.0.0 just released

Following the list's contribution guidelines: alphabetical order, no
self-promotion in description, link only to the repo (not to a marketing
page).
```

---

## 7. Discord / Slack community posts

Channels to post in (one message each, in the right channel only):

- **Anthropic Discord** (`#showcase` or equivalent)
- **MCP Discord** (`#showcase`)
- **Cursor Discord** (`#community-creations` if it exists)
- **r/LocalLLaMA Discord**

**Template:**

```
Hey folks — built a cross-tool memory layer for AI coding agents and would
love feedback. It captures every turn into a repo-local JSONL and surfaces
it back via MCP + CLI, so the same memory works in Claude Code, Cursor,
Codex, etc.

The non-obvious part: layered retrieval (titles -> detail -> raw) keeps
recall cheap as history grows. Brand new install backfills from git so it's
useful on day one.

Repo: https://github.com/Mintsolester/claude-meister

Open to PRs and roasts.
```

**Rules:** Post once per server. Never DM members unless they ask you to.

---

## 8. "Good first issue" templates

Open these as GitHub issues *before* launch so contributors have a way in.

### Issue 1: Cursor adapter for capture

```markdown
**Title:** Add Cursor adapter for capture path

Cursor stores chats in `~/.cursor/chats/<session_id>.json`. To bring write
parity with Claude Code we need an adapter that:

1. Watches the Cursor chats directory
2. Normalizes each chat turn into our event schema (see `docs/MEISTER_CLI.md`)
3. Appends to the correct repo's `.repo_memory/conversation.jsonl`

This is a contained ~150 LOC change in `meister/adapters/cursor.py` (new
file). The schema is documented; you don't need to touch the rest of the
codebase.

Good first issue: yes
Estimated effort: 4-8 hours
```

### Issue 2: `meister export --markdown`

```markdown
**Title:** Add `meister export --session <id> --markdown` command

Render one session as a human-readable markdown document — useful for sharing
a session log or pasting into a PR description.

Output sketch:

```
# Session <id> (2026-05-17)

## Prompt
> fix the dedup bug

## Actions
- Edit `db/repository.py` (lines 55-119)
- Bash: `pytest tests/test_db.py`

## Outcome
tests pass, dedup behavior verified
```

Add this as a new subcommand in `meister/cli.py`.

Good first issue: yes
Estimated effort: 2-4 hours
```

### Issue 3: Replace noise-filter blocklist with allowlist

```markdown
**Title:** Replace `_INTERNAL_PATH_NOISE` blocklist with positive allowlist

`meister/capture.py` currently uses a substring blocklist to skip Claude
Code's internal scratch directories. This is fragile — every new Claude
Code release could add a new internal path we'd need to discover.

Replace with: only capture file paths inside the repo root (or
sub-directories of it). Anything outside the repo is dropped.

Touchpoints: `meister/capture.py:_is_internal_noise`,
`meister/store.py:find_repo_root`.

Good first issue: yes (small, well-bounded change)
Estimated effort: 1-2 hours
```

---

## 9. README hero update (run this BEFORE launch)

Verify the README hero section (top 50 lines) answers, in order:

1. What is this? (one sentence)
2. Demo gif (autoplay)
3. Install (one command)
4. First useful command (one command)

If any answer takes more than 10 seconds to find, you've already lost the
visitor. Test by opening the repo in an incognito window.

---

## 10. Post-launch responses — pre-written

**"How is this different from Mem0?"**

```
Mem0 is a general-purpose memory layer for LLM apps with embeddings + vector
DB. Meister is purpose-built for coding agents: repo-local plaintext JSONL,
no embeddings, layered retrieval. Different design space. Mem0 is better if
you want one memory across many apps; Meister is better if you want memory
that belongs to the codebase.
```

**"How is this different from CLAUDE.md?"**

```
CLAUDE.md is static — you write it once, Claude reads it on every session.
Meister captures dynamic state: which files you touched yesterday, what
prompts led to what changes, which decisions you made. Complementary, not
competing. Keep your static facts in CLAUDE.md; let Meister handle the
ephemeral.
```

**"What about privacy / my prompts going somewhere?"**

```
Nothing leaves your machine. The log is plaintext JSONL at
`<your-repo>/.repo_memory/conversation.jsonl`. `cat` it, `rm` it, `gitignore`
it. The default .gitignore in v2.0 already excludes it from commits.
```

**"Will Anthropic just ship this natively?"**

```
Probably — for Claude Code. They will never ship it for Cursor or Codex.
That's the wedge. If you only use Claude Code, Anthropic's native memory
will eventually replace this. If you switch between tools, Meister is the
only thing that keeps your memory continuous.
```
