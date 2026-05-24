# Verify Meister works on your own machine

Run this protocol once before you tell anyone else about the project. It
proves the whole loop end-to-end: **capture → store → recall → injection
back into Claude's context.**

It takes 15-20 minutes and you'll either come out of it with proof the
thing works, or a precise list of what's broken.

## Part 1 — Programmatic checks (3 minutes)

These run in-process. If any FAIL, fix before proceeding.

```bash
# First time only — install meister so the `meister` command is on PATH:
git clone https://github.com/Mintsolester/claude-meister
cd claude-meister && pip install -e .

# Then in YOUR repo (not the claude-meister repo):
cd <your-repo>
meister install-hooks      # wires capture + SessionStart inject + statusLine
meister test               # 4/4 PASS check
```

Expected output:

```
meister self-test
------------------------------------------------------------
Repo root:  /path/to/your-repo
Memory dir: /path/to/your-repo/.repo_memory

  [PASS] memory dir exists & writable  /path/to/your-repo/.repo_memory
  [PASS] capture roundtrip  wrote 2 events, read back 2
  [PASS] recall returns marker  top-3 contains test_a1b2c3d4...
  [PASS] hooks wired  UserPromptSubmit + PostToolUse + Stop present
  [PASS] SessionStart inject wired  Claude will see meister context on session start
  [PASS] statusLine wired  footer shows live capture state
  [INFO] token math: full log = ~2840 tokens, L0 recall = ~310 tokens (89% saved on default recall)
------------------------------------------------------------
Result: 4/4 programmatic checks passed.
```

If any FAIL: re-run `python -m meister install-hooks`, then `meister test`
again. Don't proceed until all four PASS.

## Part 2 — Confirm live capture is happening (2 minutes)

This proves the hooks fire during a real session.

1. Open Claude Code in your repo.
2. **Look at the footer.** You should see something like:
   ```
   meister: 23 sessions · 184 events · 87.4KB · last 2s ago
   ```
   If you see `meister: ready (no captures yet)` — capture isn't wired.
   Quit, run `install-hooks` again, restart Claude Code.
3. Ask Claude to do one trivial thing: *"List the files in this directory."*
4. After the response, the footer should show events incremented by 1+ and
   `last 0s ago`. If the timestamp doesn't update, the PostToolUse hook
   isn't firing.

## Part 3 — Confirm Claude actually USES the captured memory (10 minutes)

> **This is the test that matters.** Capture without recall is useless.
> This proves the loop is closed.

### 3a — Plant a distinctive marker (3 minutes)

In your current Claude Code session, do something memorable and unique.
The more specific, the better:

> *"Read the file `db/schema.sql` and tell me what tables are defined.
> Then save a one-line note to yourself: I'm investigating dedup behavior
> in the personas table."*

This produces multiple events in the JSONL (a Read tool call + a prompt
response with a distinctive phrase: "investigating dedup behavior").

Verify the marker landed:

```bash
python -m meister recall "dedup behavior"
```

Expected: the current session shows up in the top-3 results.
**If not, capture isn't capturing assistant text — capture is event-level
only by design, so use a phrase from your PROMPT, not the response. Retry
with a distinctive prompt phrase like "investigating zarflemb personas".**

### 3b — Close the session completely (1 minute)

- Exit Claude Code (`/exit` or close the terminal).
- Wait at least 30 seconds. This eliminates any session-state caching.
- Reopen Claude Code in the **same repo**.

### 3c — Test cold recall (5 minutes)

In the fresh session, ask **without giving Claude any hint about meister:**

> *"What was I working on most recently in this repo?"*

You should observe one of three outcomes:

| Outcome | What it means |
|---|---|
| **Claude correctly summarizes your dedup investigation** | The SessionStart hook is injecting meister context. **The loop is closed.** |
| Claude says "I don't have memory of previous sessions" | SessionStart inject failed. Check: `python -m meister test` should show `[PASS] SessionStart inject wired`. |
| Claude gives a generic guess based on file structure | Inject ran but the context was too vague. Increase MAX_SESSIONS in `meister/session_inject.py` from 5 to 10. |

Now ask:

> *"Use the meister CLI to find the session where I was investigating dedup
> behavior, then show its details."*

This tests whether Claude can use meister as a tool when asked. Claude
should run `python -m meister recall "dedup behavior"` (or similar) and
report the result. If it doesn't know about meister, add a hint to
`CLAUDE.md`:

```markdown
## Memory

This repo uses `meister` for cross-session memory. To recall what was
worked on previously, run `python -m meister recall "<topic>"` or
`python -m meister last`.
```

### 3d — The honest read

After 3c, you'll know exactly what works:

- **Both prompts worked:** the system is functional end-to-end. Ship it.
- **Only the explicit prompt worked:** capture and recall work, but
  passive injection doesn't. Either the SessionStart hook didn't fire, or
  the context was too short. Debug the hook by adding `print(ctx,
  file=sys.stderr)` to `session_inject.py` and re-running.
- **Neither worked:** the loop is broken. Most likely the hooks are
  wired but `.repo_memory/` is empty in the test repo. Run `meister
  status` to confirm session count.

## Part 4 — Quantify the value (5 minutes)

Now you have real data to put real numbers on the README claims.

```bash
python -m meister status
```

Note the event count and log size.

Then compute the recall cost yourself:

```bash
# How big would naive "dump the log to Claude" be?
wc -c .repo_memory/conversation.jsonl
# Divide by 4 for a rough token count.

# How big is a layered L0 recall?
python -m meister last -n 10 | wc -c
# Divide by 4.
```

Realistic numbers from a one-week-old repo with active use:

| Approach | Tokens per recall |
|---|---|
| Naive (dump full JSONL) | 5,000-15,000 |
| Meister L0 (last 10 sessions) | 200-400 |
| Meister L1 (one session drill-down) | 300-600 |

**This is your real headline number for marketing.** Put it in the README.
"Recall costs ~300 tokens instead of ~8,000 — measured on a real repo
with 50 sessions captured" beats every adjective.

## Part 5 — When to consider it verified

You can confidently launch when **all** of these are true:

- [ ] `meister test` shows 4/4 PASS
- [ ] Status line updates after every tool call in Claude Code
- [ ] Part 3c — Claude correctly summarizes recent work in a fresh session
      (the cold-recall test)
- [ ] You have concrete tokens-per-recall numbers from YOUR repo to put in
      the README, not made-up ones

If any of these are false, the marketing claims are unproven. Fix first,
launch second. The launch playbook can wait; a broken first impression
cannot be undone.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Status line shows nothing | Python not on PATH | Verify `which python` matches what's in `~/.claude/settings.json` |
| Status line shows "ready (no captures yet)" but you've used Claude Code | Hooks point at wrong Python | Re-run `install-hooks` in the env where Claude finds Python |
| `meister test` PASSes but Claude still doesn't remember | SessionStart hook not firing | Open `/hooks` in Claude Code once, or restart the session |
| Claude knows about meister but never uses it on its own | No CLAUDE.md hint | Add the `## Memory` block from Part 3c to CLAUDE.md |
| Capture works in repo A but not repo B | `find_repo_root` couldn't locate B | Make sure repo B is a git repo (`git init` if not) |
