# Launch Playbook — first-time OSS edition

A step-by-step plan for launching Claude_Meister v2.0 to the wider dev
community. Written for someone who has never shipped open-source before.

**How to use this document:** Work through phases in order. Each checkbox is
an atomic action — if you can't tick it off in one sitting, the step is
too vague and needs splitting. Don't skip phases. Don't reorder.

**Estimated total effort:** 15-20 hours over 2 weeks, then 4-6 hours/week
for the first month of post-launch maintenance.

**Tools you will install:** OBS Studio, ffmpeg, gh CLI, Typefully account,
GitHub social-preview generator. All free or trial-tier.

**Kill criterion (set NOW):** If by **2026-08-17** (90 days post v2.0
launch) the repo has fewer than **500 stars AND fewer than 50 weekly active
users**, pivot or sunset. Write the date in your calendar before you
continue.

---

## Phase 0 — Account & tool setup (2-3 hours, do once)

### 0.1 Accounts

- [ ] **Hacker News account** — register at https://news.ycombinator.com/login
      Username should be your real name or a handle you'll keep forever.
      HN doesn't gate by age but unestablished accounts are downweighted.
      **Pre-launch task:** comment thoughtfully on 3-5 unrelated HN posts
      this week. This earns you a few karma points and makes your Show HN
      not look like a throwaway.
- [ ] **Reddit account** — must have ≥50 comment karma to post in
      /r/programming. /r/ClaudeAI has lower bars. If new, comment on a few
      posts before launching.
- [ ] **X / Twitter** — bio should mention "building [thing]" so the link
      doesn't look like a spam drop.
- [ ] **dev.to** — register at https://dev.to/enter
- [ ] **Lobste.rs** — invite-only. Skip if you don't have one.
- [ ] **Typefully** — https://typefully.com — for atomic X thread posting.

### 0.2 Tools

- [ ] **OBS Studio** — https://obsproject.com/download (free, all OS)
- [ ] **ffmpeg** — for converting MP4 → GIF.
      - Windows: `winget install ffmpeg` or download from https://ffmpeg.org
      - macOS: `brew install ffmpeg`
      - Linux: `sudo apt install ffmpeg`
- [ ] **gh CLI** — https://cli.github.com/ (used to create the release)
      - Windows: `winget install GitHub.cli`
      - macOS: `brew install gh`
      - Linux: see install page
- [ ] **Authenticate gh:** `gh auth login` → GitHub.com → HTTPS → browser
- [ ] **Image editor for social preview** — Figma (free) or GIMP (free).

### 0.3 Verify

- [ ] `gh auth status` → shows "Logged in to github.com"
- [ ] `ffmpeg -version` → prints a version
- [ ] OBS opens, can record a test 5-second clip

**Skip Phase 0 only if** you have published to HN or shipped a public OSS
release in the past 6 months.

---

## Phase 1 — Make the demo (3-4 hours, do this FIRST)

> The single highest-leverage artifact of this entire launch. Every other
> step is 3-5x more effective with this video, and most are useless without
> it.

### 1.1 Storyboard (15 min)

Open `docs/launch/COPY_TEMPLATES.md` and read the X-thread tweet 1. That
sets the demo's narrative: "Your AI forgets. Meister fixes it. In any tool."

The 60-second script:

| Time | What viewer sees | Caption |
|---|---|---|
| 0–5s | Empty terminal in a real repo | "Your AI assistant forgets everything between sessions." |
| 5–15s | Run `python -m meister install-hooks` — backfill output prints | "One command. Reads your git history." |
| 15–25s | Close terminal. Cut to "Next day." card | "Next day." |
| 25–45s | Run `python -m meister recall "<topic>"` — three sessions appear, `meister show <id>` expands one | "Your memory follows the repo, not the tool." |
| 45–58s | Same `recall` works in Cursor via MCP (split screen if possible) | "Claude. Cursor. Codex. Aider. Same memory." |
| 58–60s | End card: github.com/Mintsolester/claude-meister | (URL only) |

### 1.2 Prepare the recording (30 min)

- [ ] Pick a clean demo repo with real, recognizable commits. **Do not** use
      your work repo (privacy). Suggestion: clone `claude-meister` itself —
      it has a real git history.
- [ ] Open it in your terminal. Verify `python -m meister --version` works
      (you may need to add `pip install -e .` first if it doesn't).
- [ ] Close ALL notifications. Turn off Slack/Discord. Set DND.
- [ ] Use a clean shell prompt — no `[user@host]` chatter. In bash:
      `PS1='\\$ '`. In zsh: `PROMPT='%% '`.
- [ ] Increase font size to 16-18pt. Small terminal text reads as amateur.
- [ ] Use a dark theme. Light themes wash out on YouTube/Twitter compression.

### 1.3 Record (45 min, expect 3-5 takes)

- [ ] OBS: new scene, "Display Capture" of just the terminal window.
      Resolution: 1920×1080. FPS: 30 (60 if your GPU handles it).
- [ ] Hit "Start Recording". Run through the script. Slow down — viewers
      pause naturally at the wrong moments.
- [ ] After recording, watch it. If you cringe at any point, re-record that
      segment. Cringe = real signal.

### 1.4 Edit (60 min)

You don't need fancy software. Free options:

- **Shotcut** (https://www.shotcut.org/) — free, cross-platform, simple cuts
- **DaVinci Resolve** (free tier) — heavier but better titling
- **CapCut Desktop** — easy captions

Editing checklist:

- [ ] Trim dead air to zero. Every second a viewer sees nothing happen
      costs you ~5% of the audience.
- [ ] Add captions (per the storyboard above) — 80% of viewers watch
      muted, especially on Twitter/LinkedIn.
- [ ] No background music. None. Dev demos with music feel salesy.
- [ ] End card: 2 seconds, just `github.com/Mintsolester/claude-meister`.

### 1.5 Export (15 min)

- [ ] Export MP4: H.264, 1080p, 30fps, ~6-10 Mbps. Should land 8-15 MB for
      60 seconds.
- [ ] Generate GIF for HN / GitHub README. ffmpeg one-liner:

  ```bash
  ffmpeg -i demo.mp4 -vf "fps=12,scale=1200:-1:flags=lanczos" -c:v gif demo.gif
  ```

  Target: GIF under 10 MB. If larger, drop fps to 10 or scale to 1000.

- [ ] Place files in repo as `docs/images/demo-v2.mp4` and `docs/images/demo-v2.gif`.
      Reference them from README.md and the release notes.

### 1.6 Sanity check

- [ ] Show the GIF to a non-technical friend. If they can't tell what the
      tool does in 30 seconds, the captions need rework.
- [ ] Show the MP4 to a developer friend. Ask: "Would you click install?"
      If no — find out which 5 seconds lost them and re-edit.

---

## Phase 2 — Repo hygiene (4-5 hours)

### 2.1 README restructure (90 min)

The current README is 35KB. The first impression test: can a stranger answer
"what does this do?" in <10 seconds? **If not, no campaign saves you.**

- [ ] First 30 lines of README must contain (in order):
  1. One-sentence pitch (already done in v2 hero section)
  2. Demo gif (embed via markdown image — `![demo](docs/images/demo-v2.gif)`)
  3. Install (`git clone`, `cd`, `python -m meister install-hooks` — 3 lines)
  4. First useful command (`python -m meister last`)
- [ ] Move everything from line 50 onward into `docs/v1-runtime.md`. Keep a
      "Full v1 reference" link in the README footer.
- [ ] Add a badge row near the title:
  ```markdown
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
  [![Stars](https://img.shields.io/github/stars/Mintsolester/claude-meister?style=social)](https://github.com/Mintsolester/claude-meister/stargazers)
  ```

### 2.2 GitHub repo settings (30 min)

Open https://github.com/Mintsolester/claude-meister/settings

- [ ] **Description** field: `Cross-tool conversation memory for AI coding
      agents. MCP + CLI. Layered retrieval.`
- [ ] **Website** field: link to a tweet of your demo (or your blog post
      once written).
- [ ] **Topics:** add — `claude`, `claude-code`, `cursor`, `mcp`,
      `ai-tools`, `memory`, `developer-tools`, `python`, `cli`
- [ ] Settings → General → **Features**: enable **Discussions** (low
      maintenance, captures "how do I..." that don't deserve an issue).
- [ ] Settings → General → **Social preview**: upload a 1280×640 image. Use
      this Figma template:
      https://www.figma.com/community/file/1218635915530632 (search "GitHub
      social preview"). Show the demo's key moment + the repo name.
- [ ] Settings → Pages: enable GitHub Pages from `master` → `/docs` folder
      (free static hosting for your docs).

### 2.3 Issue templates (30 min)

- [ ] Create `.github/ISSUE_TEMPLATE/bug.yml`:

  ```yaml
  name: Bug report
  description: Something broke
  body:
    - type: textarea
      id: what
      attributes:
        label: What happened?
        description: One paragraph. Include the exact command.
      validations:
        required: true
    - type: input
      id: os
      attributes:
        label: OS + Python version
        placeholder: "Windows 11, Python 3.12"
      validations:
        required: true
    - type: textarea
      id: log
      attributes:
        label: Output of `python -m meister doctor`
        render: shell
  ```

- [ ] Create `.github/ISSUE_TEMPLATE/feature.yml`:

  ```yaml
  name: Feature request
  description: Suggest a new capability
  body:
    - type: textarea
      id: problem
      attributes:
        label: What problem does this solve?
      validations:
        required: true
    - type: textarea
      id: solution
      attributes:
        label: What would the feature do? (be specific)
      validations:
        required: true
  ```

### 2.4 Open the 3 "good first issues" (15 min)

Open each as a GitHub issue and apply the `good-first-issue` label:

- [ ] **Issue 1: Cursor adapter** — copy body from
      `docs/launch/COPY_TEMPLATES.md` section 8
- [ ] **Issue 2: `meister export --markdown`** — same source
- [ ] **Issue 3: Allowlist instead of blocklist for noise filter** — same source

You can do this with the gh CLI:

```bash
gh issue create --title "Add Cursor adapter for capture" \
  --body-file docs/launch/issues/cursor-adapter.md \
  --label good-first-issue
```

(Or paste manually in the web UI.)

### 2.5 Tag the v2.0.0 release (15 min)

- [ ] Commit and push everything from Phase 2 first.
- [ ] Tag and release:

  ```bash
  cd A:/Claude_Meister
  git tag -a v2.0.0 -m "v2.0.0 — Memory follows the repo, not the tool"
  git push origin v2.0.0
  gh release create v2.0.0 \
    --title "v2.0.0 — Memory follows the repo, not the tool" \
    --notes-file docs/launch/RELEASE_v2.0.0.md \
    docs/images/demo-v2.mp4 docs/images/demo-v2.gif
  ```

- [ ] Verify the release page renders the gif. If not, embed it inline in
      the release body via the `![demo](...)` syntax pointing at the
      uploaded asset URL.

### 2.6 Final pre-launch check

- [ ] Open the repo in an **incognito window**. Time yourself: from URL to
      "I get what this does" — should be under 10 seconds. If not, fix.
- [ ] Run `python -m meister doctor` on a fresh clone in a Codespaces /
      Replit instance. Verify it works for someone who isn't you.
- [ ] Confirm `.repo_memory/` is gitignored. Run `git status` — if
      `.repo_memory/conversation.jsonl` appears, your gitignore is wrong.
- [ ] Search the repo for personal data — usernames, absolute paths, email:
      ```bash
      grep -ri "your-real-name\|/Users/your-name\|C:/Users/your-name" .
      ```
      Expect zero matches.

---

## Phase 3 — Soft launch (Day 5-7)

> One subreddit, one post. Catches the bugs HN won't forgive.

### 3.1 Post to /r/ClaudeAI

- [ ] **Time:** Sunday 6-8pm ET (peak weekday-prep traffic). On a weekday
      6-9pm ET also works.
- [ ] Use the title and body from `docs/launch/COPY_TEMPLATES.md` section 1.
- [ ] Embed the demo gif via Reddit's image upload (drag-and-drop), not as
      a link. In-feed images get 3-5x the engagement.
- [ ] Pin a top comment: "Author here, will respond to all questions today."

### 3.2 Iterate (Day 6-7)

- [ ] Triage every comment within 1 hour during the first 4 hours.
- [ ] Bug reports → open issue, label `from-reddit`, link in the comment.
- [ ] Fix the top 3 bugs by Monday. Push fixes to `master`. Update the
      Reddit thread with a "✅ fixed in commit XYZ" comment.
- [ ] Note what people *don't* understand. That's a README problem, not a
      product problem.

**If soft launch flops** (< 10 upvotes after 24 hours): pause. Do not proceed
to HN. Diagnose:
- README too vague?
- Demo gif too long / unclear?
- The "Why I built this" doesn't resonate?
- Wrong subreddit (try /r/LocalLLaMA instead)?

Fix and re-post in a different sub a week later. Do not hard-launch a
product the soft launch told you isn't ready.

---

## Phase 4 — Hard launch (Day 8: Tuesday)

### 4.1 The morning of (start at 7:30am ET)

- [ ] 7:30am — final smoke test: clone fresh, `install-hooks`, recall.
      Confirm everything works.
- [ ] 7:45am — open all browser tabs:
  - HN submit page: https://news.ycombinator.com/submit
  - Twitter compose
  - r/programming, r/commandline, r/LocalLLaMA tabs
  - GitHub repo (refresh-ready for engagement metrics)
- [ ] 7:55am — eat something, get coffee, be physically ready to type for 4
      hours.

### 4.2 Submit (8:00am ET sharp)

- [ ] **Submit to HN** using title + URL from `COPY_TEMPLATES.md` section 2.
      Leave the text field BLANK.
- [ ] **Immediately** (within 30 seconds) post the first comment from
      section 2 as the OP.
- [ ] Open your submission and refresh — confirm the comment posted.

### 4.3 Cross-channel push (8:05am – 8:30am)

- [ ] **Twitter:** post the thread from `COPY_TEMPLATES.md` section 3
      via Typefully (atomic post). Pin the thread to your profile.
- [ ] **r/programming:** post — title and body from section 1 of
      `COPY_TEMPLATES.md`, but check the sub's rules first; some require
      flair like `[Project]`. **Skip if** you don't have ≥50 link karma.
- [ ] **r/commandline:** same content, may need to angle as "CLI for AI
      memory inspection" in the title.
- [ ] **r/LocalLLaMA:** angle as "MCP server" — that community cares about
      local-first/no-cloud, lean into that.
- [ ] **Anthropic Discord** `#showcase` and **MCP Discord** `#showcase`
      channels — message from section 7.

### 4.4 Engagement window (8:30am – 12:30pm)

This 4-hour window decides the launch.

- [ ] Reply to **every HN comment within 30 minutes**. HN's ranking
      algorithm weighs OP engagement heavily.
- [ ] Reply to every Reddit comment within 1 hour.
- [ ] Quote-tweet ANY mention on X with a "thanks for sharing" + one
      concrete addition (link to the docs page they asked about).
- [ ] If a bug surfaces — fix and push **immediately**, then reply with
      "Fixed in [commit]. Thanks for the report."
- [ ] Pre-written responses are in `COPY_TEMPLATES.md` section 10. Use
      them. Don't ad-lib under pressure.

### 4.5 Don'ts (every single one matters)

- ❌ Don't manufacture upvotes. Alt accounts are detectable; HN shadowbans
     permanently.
- ❌ Don't ask friends to upvote. Same risk.
- ❌ Don't argue with critics. Acknowledge + clarify + thank.
- ❌ Don't promise features in launch comments. You'll be held to them.
- ❌ Don't apologize for the product. "Sorry it's basic" reads as low
     confidence.
- ❌ Don't reply with one-word answers. Even "thanks!" deserves a sentence
     of context.

### 4.6 End of day

- [ ] Around 6pm ET, tally: HN rank, star count, comment count, install
      count (proxy: clone count from GitHub Insights → Traffic).
- [ ] Write down ONE thing that surprised you. Save it for the
      retrospective.

---

## Phase 5 — Sustain (Days 9-30)

### Week 2

- [ ] **Mon:** Submit PRs to awesome-lists from `COPY_TEMPLATES.md` section 6.
- [ ] **Tue:** Send 10 cold DMs (section 4 template). Do this on Tuesday
      because mid-week DMs have the highest reply rate.
- [ ] **Wed:** Open 2-3 more "good first issues" if the first wave got
      claimed.
- [ ] **Thu:** Write and publish the blog post (section 5). Cross-post to
      dev.to and hashnode. Submit to HN as a **separate** post 3 days after
      publishing — only if Show HN didn't gain traction.
- [ ] **Fri:** Search HN and Reddit for any thread mentioning "claude code
      memory", "MCP memory", "ai coding context". Comment with technical
      value, sign off with link. Do NOT shill.

### Week 3

- [ ] Ship **Cursor adapter** as v2.1.0. Make a second 30-second demo
      showing the same memory in Claude Code AND Cursor (split-screen).
      Post this as a "v2.1 released" follow-up on X and r/ClaudeAI.
- [ ] Reply to every issue and PR within 48 hours. Even "thanks, I'll look
      this week" is enough — silence kills contributor energy fast.

### Week 4

- [ ] Write a **first-month retrospective** as a GitHub Discussion or blog
      post. Title: "30 days after launching Claude_Meister". Share real
      numbers: stars, installs (if tracked), issues opened/closed, what
      surprised you. Transparency builds compounding trust.
- [ ] **Decide on telemetry.** If you want to track weekly-active-users
      against the kill criterion, you need opt-in telemetry. Implement as a
      v2.2 feature: `meister --version` pings a counter endpoint
      (Cloudflare Worker, ~10 LOC). NEVER make it default-on.

---

## Phase 6 — The 90-day kill check (2026-08-17)

This is the hardest phase. On 2026-08-17, open this file and check:

- [ ] GitHub stars: ____ (target: 500+)
- [ ] Weekly active users: ____ (target: 50+)
- [ ] External contributors with merged PRs: ____ (target: 5+)
- [ ] Issues opened by non-author: ____ (target: 20+)

### Outcomes

**All four targets met** → continue. Plan v3 roadmap. Consider commercial
tier (encrypted cloud sync as the candidate).

**2-3 targets met** → product is real but small. Continue maintaining,
don't push more launch energy. Focus on making the existing users
delighted.

**0-1 targets met** → the market spoke. Options, in order of preference:

1. **Extract the layered-retrieval idea as a standalone library.** It's the
   real insight; ship it independently of the wider product.
2. **Donate to another project** that's gaining traction in the same space.
3. **Sunset cleanly:** archive the repo, leave the README with a "no longer
   maintained" header pointing at the closest alternative.

Whichever you pick, **write a retrospective post**. The skill of public
post-mortems is rare and durable. Future projects benefit from the same
honesty.

---

## Honest expectations

| Outcome | Probability | What it looks like |
|---|---|---|
| Bear | 60% | 50-300 stars, ~20 daily users, mostly your network. Sunset by month 4. |
| Base | 30% | 500-3000 stars, ~200 DAU, niche but real audience. Maintainable as a passion project. |
| Bull | 10% | HN front page + influencer pickup. 5k+ stars. Acquisition or paid-tier shot. |

The base case is good. Plan for it. Don't anchor on the bull case.

---

## When you get stuck

Three failure modes are common at each phase:

1. **Phase 1 (demo) too long** — under-recording, re-recording, perfectionism.
   **Fix:** ship a 6/10 video this week. You can replace it later. Doing it
   never is worse than doing it badly.

2. **Phase 2 (repo hygiene) too long** — endless README polishing.
   **Fix:** time-box to 4 hours. The README is never "done". It's good
   enough when a stranger can install it.

3. **Phase 4 (launch day) burnout** — 4 hours of replies is exhausting.
   **Fix:** schedule it on a day you control. Don't launch the day before
   travel.

---

## What to do right now

If you've read this whole document, do exactly this in the next 30 minutes:

1. Block 3 hours on your calendar tomorrow titled "Phase 1 — Demo recording".
2. Write the kill date (**2026-08-17**) in your calendar with a reminder
   that links to this file.
3. `git add docs/LAUNCH_PLAYBOOK.md && git commit -m "docs(launch): add
   first-time-OSS launch playbook"`
4. Send yourself an email titled "Why I'm launching Meister" with a 3-line
   answer. Read it on launch day if you're nervous.

Good luck.
