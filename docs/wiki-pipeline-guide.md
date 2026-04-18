# Wiki Pipeline Guide

A step-by-step playbook for building a domain-specific knowledge wiki that Claude reads on-demand — no repeated summarization, no burned context, zero API cost for retrieval.

---

## Table of Contents

1. [What This Pipeline Does](#chapter-1-what-this-pipeline-does)
2. [Prerequisites](#chapter-2-prerequisites)
3. [Gathering Raw Sources](#chapter-3-gathering-raw-sources)
4. [Setting Up the Vault Structure](#chapter-4-setting-up-the-vault-structure)
5. [The Synthesis Process](#chapter-5-the-synthesis-process)
6. [Building Sub-Indexes for Efficient Retrieval](#chapter-6-building-sub-indexes-for-efficient-retrieval)
7. [Setting Up \_hot.md (Working Memory)](#chapter-7-setting-up-_hotmd-working-memory)
8. [The Tiered Retrieval Protocol](#chapter-8-the-tiered-retrieval-protocol)
9. [Maintaining and Evolving the Wiki](#chapter-9-maintaining-and-evolving-the-wiki)
10. [Example — Building a Wiki for React](#chapter-10-example--building-a-wiki-for-react)

---

## Chapter 1: What This Pipeline Does

### The Problem

Claude's training has a knowledge cutoff. Official documentation changes constantly — APIs get updated, new hooks are added, deprecations happen, pricing shifts. Every time you start a conversation, Claude either gives you stale information or you waste hundreds of tokens copy-pasting documentation into the chat just to ask a question about it.

Even worse: if you paste docs in every conversation, you're paying for the same tokens over and over. Large language models are expensive at scale. And if you're running Claude inside an automated workflow or agentic system, there's no convenient way to paste docs in at all.

### The Solution

A structured local wiki that Claude reads on-demand using Claude_Meister's runtime context router.

Instead of pasting docs, you build a knowledge base once — a set of interlinked Markdown files organized by topic, with a smart retrieval layer on top. When Claude needs to know something about your domain, it follows a five-step read sequence: starting with a tiny "working memory" file (under 500 tokens), then escalating to deeper pages only if needed.

The result: Claude gets accurate, up-to-date, domain-specific knowledge at a fraction of the token cost of pasting raw docs.

### What You Will End Up With

After completing this guide you will have:

- A `your-wiki/` directory with 20-50 interlinked Markdown pages
- A master `index.md` and a `_hot.md` working-memory file
- Domain-specific sub-indexes for fast lookup
- The `wiki_path` field set in `runtime_config.json` so Claude_Meister's context router finds and reads the wiki automatically
- A repeatable pipeline for adding new sources and keeping pages current

The whole thing costs zero API calls to read — it's just local files.

---

## Chapter 2: Prerequisites

Before you start, make sure you have the following in place.

### Required

**Claude Code with Claude_Meister installed**
If Claude_Meister isn't installed yet, follow the steps in the project README. Once it's installed, you'll have a `runtime_config.json` file at `C:/Users/yourname/.claude_runtime/configs/runtime_config.json`. That config is where you'll point Claude at your wiki at the end of this guide.

**A domain to build the wiki for**
This can be anything:
- A framework you use every day (React, FastAPI, Tailwind)
- A third-party API (Stripe, Twilio, OpenAI)
- Your company's internal documentation
- A product you're building (your own API, feature set)

**Markdown editor**
Any text editor works — VS Code, Notepad++, even Windows Notepad. Obsidian is recommended but not required.

**~2–4 hours for the initial build**
The first time through takes 2–4 hours depending on how many raw sources you have. Ongoing updates are 15–30 minutes per session.

### Recommended (Optional)

**Obsidian** (free, [obsidian.md](https://obsidian.md))
Obsidian renders wikilinks (`[[Page Name]]`), shows a graph of connected pages, and has a Web Clipper plugin for capturing docs directly. None of this is required — it just makes the process easier to visualize.

**MarkDownload browser extension** ([Chrome](https://chrome.google.com/webstore/detail/markdownload-markdown-web/pcmpcfapbekmbjjkdalcgopdkipoggdi) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/markdownload/))
Converts any webpage to clean Markdown with one click. Useful for capturing docs pages.

### Expected Output for This Chapter

You should be able to answer yes to these questions before moving on:
- [ ] Claude Code is installed and Claude_Meister is configured
- [ ] I have a domain in mind
- [ ] I have a markdown editor open and ready

---

## Chapter 3: Gathering Raw Sources

Before you can synthesize anything, you need the raw material. This chapter walks you through finding, capturing, and storing source documents for your domain.

### What to Gather

Good source material for a wiki includes:

| Source type | Examples | Priority |
|-------------|----------|----------|
| Official docs | docs.react.dev, FastAPI docs, Stripe API reference | High |
| Getting-started guides | "Introduction", "Overview", "Quickstart" pages | High |
| API reference | Full method/function/endpoint listings | Medium |
| Official blog posts | Release announcements, migration guides | Medium |
| Changelogs / release notes | CHANGELOG.md, GitHub releases | Medium |
| Community tutorials | well-regarded guides from respected sources | Low |
| README files | GitHub repo READMEs for related packages | Low |

**Quality over quantity.** 50 well-chosen documents beat 500 random ones. Prioritize official, authoritative sources. Avoid SEO-padded blog posts that just restate the docs.

### How to Capture Sources

**Method 1: Manual copy-paste (simplest, always works)**

1. Open the documentation page in your browser.
2. Select all text (Ctrl+A, then Ctrl+C).
3. Paste into a new Markdown file in your text editor.
4. Save the file with the page title as the filename (see naming convention below).

Expected output: a `.md` file containing the raw text of the page, including headings, code blocks, and lists.

If you see formatting break badly (e.g., tables become garbled), use Method 2 instead.

**Method 2: MarkDownload browser extension (recommended)**

1. Install the MarkDownload extension for your browser.
2. Navigate to the documentation page.
3. Click the MarkDownload icon in your browser toolbar.
4. Click "Download" in the popup. The file saves to your Downloads folder.
5. Move it to your `raw/` directory.

Expected output: a clean `.md` file where headings, code blocks, and tables are properly formatted.

If you see the extension fail on JavaScript-heavy pages (common with some API reference sites), fall back to Method 1.

**Method 3: CLI download (for large doc sets)**

If you need to capture an entire documentation site at once, use `wget`:

```bash
wget --mirror --convert-links --no-parent --page-requisites \
     -e robots=off -P ./raw-html \
     https://docs.example.com/
```

Then convert the HTML files to Markdown using a tool like `pandoc`:

```bash
# Install pandoc from https://pandoc.org/installing.html
# Then, for each HTML file:
pandoc raw-html/docs.example.com/page.html -o raw/Page-Name.md
```

Expected output: a `raw/` directory containing `.md` files for each page.

If you see broken internal links or garbled code blocks, the HTML→Markdown conversion was imperfect. Open the worst offenders and clean them up by hand.

**Method 4: Obsidian Web Clipper (if you use Obsidian)**

1. Install the Web Clipper plugin from Obsidian's community plugins list.
2. Configure it to save clipped pages into your wiki's `raw/` folder.
3. Browse to any documentation page and click the clip icon.

Expected output: a `.md` file saved directly into your vault's `raw/` folder with clean formatting.

### Naming Convention

Name every raw file after its page title, using title case and hyphens for spaces:

```
Getting-Started.md
API-Overview.md
Hooks-Reference.md
Migration-Guide-v17-to-v18.md
useEffect-Explained.md
```

Keep names short but descriptive. Avoid names like `page1.md` or `docs-export-2024-11-01.md` — when you're scanning 50 files in three months, you'll thank yourself for the clear names.

### Storage

Create a `raw/` directory inside your wiki folder and put all captured files there:

```
my-wiki/
└── raw/
    ├── Getting-Started.md
    ├── API-Overview.md
    ├── Hooks-Reference.md
    └── ...
```

These files are your unprocessed inputs. Do not edit them — if the source docs change, you re-capture and replace the raw file. The synthesized wiki pages (which you'll create in Chapter 5) are where the real work lives.

### Quality Check Before Moving On

Before you proceed to the next chapter, verify:
- [ ] You have at least 10 raw source files
- [ ] All files are named descriptively
- [ ] Files are stored in a `raw/` directory
- [ ] The most important overview/introduction pages are included

---

## Chapter 4: Setting Up the Vault Structure

Now create the directory structure that will hold your synthesized wiki pages.

### The Directory Layout

Navigate to wherever you store your projects (e.g., `C:/Users/yourname/wikis/`) and create a new folder for your wiki:

```
my-react-wiki/              ← root of your wiki
├── _hot.md                 ← working memory (first thing Claude reads)
├── index.md                ← master index of all pages
├── overview.md             ← domain overview / "what is this?"
├── log.md                  ← operation log (every synthesis run logged here)
├── raw/                    ← your raw captured source files
│   ├── Getting-Started.md
│   └── ...
├── entities/               ← products, services, components, APIs
│   ├── useState.md
│   ├── useEffect.md
│   └── React-Router.md
├── concepts/               ← ideas, patterns, techniques
│   ├── Component-Lifecycle.md
│   ├── State-Management.md
│   └── Rendering-Behavior.md
├── comparisons/            ← X vs Y analyses
│   ├── useState-vs-useReducer.md
│   └── Class-vs-Functional-Components.md
├── guides/                 ← how-to walkthroughs
│   ├── Setting-Up-Create-React-App.md
│   └── Migrating-to-React-18.md
├── queries/                ← saved research questions and answers
│   └── Why-does-useEffect-run-twice.md
└── sources/                ← summarized source files (one per raw file)
    ├── Getting-Started-summary.md
    └── Hooks-Reference-summary.md
```

**What each directory is for:**

| Directory | What goes here | Example pages |
|-----------|----------------|---------------|
| `entities/` | Discrete things: hooks, components, APIs, services | `useState.md`, `Suspense.md` |
| `concepts/` | Cross-cutting ideas, patterns, mental models | `State-Management.md`, `Reconciliation.md` |
| `comparisons/` | Side-by-side analyses | `useState-vs-useReducer.md` |
| `guides/` | Step-by-step walkthroughs | `Setting-Up-CRA.md` |
| `queries/` | Specific questions you've researched | `Why-does-StrictMode-double-invoke.md` |
| `sources/` | One-page summaries of raw source files | `Hooks-Reference-summary.md` |

### Create the Structure

On Windows, open a terminal (Git Bash, PowerShell, or Command Prompt) and run:

```bash
cd C:/Users/yourname/wikis
mkdir my-react-wiki
cd my-react-wiki
mkdir entities concepts comparisons guides queries sources raw
touch _hot.md index.md overview.md log.md
```

Expected output: a `my-react-wiki/` directory with all subdirectories created and four empty files at the root.

If you see "touch is not recognized" in Command Prompt, use PowerShell or Git Bash instead, or create the files manually in File Explorer.

### The YAML Frontmatter Schema

Every synthesized page in your wiki (everything except `_hot.md`, `index.md`, `log.md`, and raw files) should start with this YAML frontmatter block:

```yaml
---
title: Page Title
type: entity | concept | comparison | guide | query | source | index | overview
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/file-that-informed-this.md, raw/another-source.md]
tags: [relevant, tags, for, this, page]
---
```

**Field explanations:**

- `title` — Human-readable title. Matches the filename without the `.md`.
- `type` — One of the seven values above. This tells Claude what kind of page it's reading.
- `created` / `updated` — ISO dates. Use today's date for `created`. Update `updated` whenever you edit the page.
- `sources` — List of raw files this page was synthesized from. Critical for traceability — when a source doc is updated, you can quickly find which wiki pages need updating.
- `tags` — Free-form tags for cross-referencing. Keep them lowercase and consistent.

**Example frontmatter for a React hook page:**

```yaml
---
title: useEffect
type: entity
created: 2026-04-17
updated: 2026-04-17
sources: [raw/Hooks-Reference.md, raw/useEffect-Explained.md]
tags: [hook, side-effects, lifecycle, cleanup]
---
```

### Create Placeholder Files

Create skeleton files now so the structure is ready when you start synthesizing:

```bash
# Create overview.md skeleton
cat > overview.md << 'EOF'
---
title: Overview
type: overview
created: 2026-04-17
updated: 2026-04-17
sources: []
tags: [overview]
---

# [Domain] — Overview

(Fill this in during synthesis)
EOF
```

For now, leave `index.md` and `_hot.md` empty — you'll fill these in during synthesis.

---

## Chapter 5: The Synthesis Process

This is the core of the pipeline. You'll use Claude to read your raw sources and produce structured wiki pages. This chapter gives you the exact prompts to use at each step.

**Important:** Run each step as a separate Claude conversation or session. Do not try to do the entire synthesis in one conversation — context limits will cause Claude to lose track of earlier files.

---

### Step 1: Triage

**What you're doing:** Getting a bird's-eye view of all your raw sources before doing any deep work.

**Open a new Claude conversation and paste this prompt:**

```
I'm building a knowledge wiki for [your domain, e.g., "React"].

I have N raw documentation files in a directory. I'm going to share them with you one by one (or paste their contents). Your job is to:

1. Read each file.
2. Add it to a running catalog with these columns:
   - Filename
   - Topic domain (e.g., "hooks", "routing", "state management", "performance")
   - One-line summary of what the file covers
   - Priority (High / Medium / Low) — High means foundational; Low means supplementary

When I've shared all files, produce the final catalog as a Markdown table.

Ready? Here's the first file: [paste contents of raw/Getting-Started.md]
```

**Then paste each raw file's contents in sequence.** After the last file, say: "That's all the files. Please produce the final catalog."

**Expected output:** A Markdown table like this:

```
| Filename | Domain | Summary | Priority |
|----------|--------|---------|----------|
| Getting-Started.md | basics | Intro to React, JSX, first component | High |
| Hooks-Reference.md | hooks | Reference for all built-in hooks | High |
| React-Router-v6.md | routing | React Router v6 API and patterns | Medium |
| ...
```

If you see Claude produce an incomplete table (missing files), ask: "You cataloged N files but I shared M. Please add the missing ones: [list filenames]."

**Save this catalog** to a file called `raw/catalog.md` in your wiki directory. You'll reference it in the next steps.

---

### Step 2: Deep Read

**What you're doing:** Thoroughly reading the highest-priority files to build a mental model of the domain before writing any pages.

This step is about Claude building understanding — you don't produce any wiki pages yet.

**Open a new Claude conversation and paste this prompt:**

```
I'm synthesizing a knowledge wiki for [your domain]. I have a catalog of raw source files (attached below). I want you to do a deep read of the HIGH priority files.

For each high-priority file I share with you:
1. Read it carefully.
2. Note the key concepts, entities, and patterns it introduces.
3. Note any important warnings, gotchas, or deprecations.
4. Identify other pages it references or cross-links to.

Do NOT produce any wiki pages yet — just build your understanding. When you've read all high-priority files, give me a summary of:
- The 10-15 most important entities in this domain
- The 5-10 most important cross-cutting concepts
- Any topics where the documentation seems contradictory or incomplete

Here's the catalog:
[paste contents of raw/catalog.md]

Starting with the first high-priority file:
[paste contents of your first high-priority raw file]
```

**Continue pasting high-priority files.** After the last one, say: "That's all the high-priority files. Please give me the entity/concept summary."

**Expected output:** A structured summary listing ~10–15 entities and ~5–10 concepts. This will guide what pages you create in Steps 3 and 4.

Save this summary to `raw/synthesis-plan.md`.

---

### Step 3: Create Entity Pages

**What you're doing:** Writing one detailed wiki page per major entity (component, hook, API endpoint, service, etc.).

Work through the entity list from Step 2, one entity at a time. For each entity:

**Open a new Claude conversation and paste this prompt:**

```
I'm writing wiki pages for a [your domain] knowledge base. I need you to write a wiki page for: [Entity Name]

Use this exact format:

---
title: [Entity Name]
type: entity
created: [today's date]
updated: [today's date]
sources: [list the raw files you'll draw from]
tags: [relevant tags]
---

# [Entity Name]

## What It Is
(1-2 sentence definition)

## How It Works
(Core mechanics. How does it actually function? Include a minimal code example if relevant.)

## Key Features / Properties
(Bullet list of the most important things to know)

## Common Patterns
(2-3 common ways this entity is used in practice. Code examples where helpful.)

## Gotchas and Warnings
(Things that bite people. Deprecations. Common mistakes.)

## Related Pages
(Use [[wikilinks]] to link to related entities and concepts: [[State Management]], [[Component Lifecycle]])

## Sources
(Brief note on which raw files were consulted)

Here are the raw files to draw from:

[File 1 — paste contents of the most relevant raw file]

[File 2 — paste contents if needed]

Write the page now.
```

**Expected output:** A complete `.md` file ready to save to your `entities/` directory.

Copy the output and save it as `entities/[Entity-Name].md`.

Repeat for each entity in your synthesis plan.

If you see Claude produce a page that's too shallow (generic statements, no real detail), add to the prompt: "This is too general. Please re-read the source files and add specific technical detail, exact method signatures, and real code examples from the documentation."

---

### Step 4: Create Concept Pages

**What you're doing:** Writing pages for cross-cutting ideas that aren't a single entity but appear across many.

Use the same prompt format as Step 3, but change `type: entity` to `type: concept` and adapt the structure:

```
I'm writing wiki pages for a [your domain] knowledge base. I need you to write a wiki page for the CONCEPT: [Concept Name]

Use this format:

---
title: [Concept Name]
type: concept
created: [today's date]
updated: [today's date]
sources: [list sources]
tags: [relevant tags]
---

# [Concept Name]

## What This Concept Is
(1-2 sentence definition — what is this idea?)

## Why It Matters
(Why does understanding this make you a better [domain] developer?)

## How It Manifests
(Where does this concept show up in practice? Examples from the domain.)

## Key Principles
(Bullet list of the rules or patterns that govern this concept)

## Common Misconceptions
(Things people get wrong about this concept)

## Related Entities
([[wikilinks]] to the entities that implement or illustrate this concept)

## Further Reading
(Which raw source files go deepest on this?)

Here are the source files:
[paste relevant raw files]
```

Save each output to `concepts/[Concept-Name].md`.

---

### Step 5: Build the Master Index

**What you're doing:** Creating `index.md`, which lists every page in the wiki organized by type.

After all entity and concept pages are written, open a new Claude conversation:

```
I've finished synthesizing a [your domain] knowledge wiki. I need you to write the master index.md file.

Here is the list of all pages I've created:

Entities:
- entities/useState.md
- entities/useEffect.md
- entities/useContext.md
[... list every entity page you created]

Concepts:
- concepts/Component-Lifecycle.md
- concepts/State-Management.md
[... list every concept page you created]

Comparisons:
[... list any comparison pages]

Guides:
[... list any guide pages]

Write index.md in this format:

---
title: Index
type: index
created: [today's date]
updated: [today's date]
sources: []
tags: [index]
---

# [Domain] Wiki — Index

## Entities
| Page | Description |
|------|-------------|
| [[useState]] | [one-line description] |
...

## Concepts
| Page | Description |
|------|-------------|
| [[Component Lifecycle]] | [one-line description] |
...

## Comparisons
...

## Guides
...

Keep descriptions to one line each. Use [[wikilinks]] for all page names.

For descriptions, use this brief summary from the synthesis:
[paste the entity/concept summary you saved to raw/synthesis-plan.md]
```

**Expected output:** A complete `index.md` file with a table for each section.

Save to `index.md` at the root of your wiki.

---

## Chapter 6: Building Sub-Indexes for Efficient Retrieval

### Why Sub-Indexes Matter

The master `index.md` is intentionally lightweight — it's meant to be scanned quickly. But if your wiki has 50+ pages across 8 domains, even scanning the index gets slow.

Sub-indexes solve this by grouping all sources for a specific topic area into one lookup file. When Claude is looking for information about "React hooks", it can go straight to `_index-hooks.md` and find all relevant pages in one read instead of scanning the entire master index.

### Naming Convention

Sub-index files use the prefix `_index-` so they sort to the top of any directory listing:

```
_index-hooks.md
_index-routing.md
_index-state-management.md
_index-performance.md
```

### How to Create Sub-Indexes

Use your triage catalog from Chapter 5 (the table you saved to `raw/catalog.md`). Open a new Claude conversation:

```
I have a catalog of raw source files for my [your domain] wiki (attached below). I also have synthesized wiki pages organized in entities/, concepts/, guides/, and comparisons/ directories.

Please:
1. Group all sources by domain (using the "Domain" column from the catalog).
2. For any domain with 5 or more sources, create a sub-index file.

Each sub-index file should be named `_index-{domain}.md` (lowercase, hyphens for spaces) and follow this format:

---
title: Sub-Index — {Domain}
type: index
created: [today's date]
updated: [today's date]
sources: []
tags: [index, {domain}]
---

# {Domain} — Sub-Index

## Wiki Pages
(Links to synthesized pages in this domain)
| Page | Type | Description |
|------|------|-------------|
| [[Entity Name]] | entity | one-line description |

## Raw Sources
(Links to raw files that cover this domain)
| File | Summary |
|------|---------|
| raw/Hooks-Reference.md | Complete reference for all built-in hooks |

Here is my catalog:
[paste contents of raw/catalog.md]

Here are my synthesized pages:
[list all pages by directory]
```

**Expected output:** One `_index-{domain}.md` file per domain with 5+ sources.

Save each file to the root of your wiki directory (alongside `index.md`).

If you see Claude create sub-indexes for domains with only 1-2 sources, add: "Only create sub-indexes for domains with 5 or more sources. Smaller domains can just appear in the master index."

---

## Chapter 7: Setting Up \_hot.md (Working Memory)

### What \_hot.md Is

`_hot.md` is the first file Claude reads every time it accesses your wiki. It's a compact "working memory" — a quick-reference cache of the most important and most recently changed facts.

Think of it as the sticky note you put on top of a thick binder. Anyone who picks up the binder reads the sticky note first and immediately knows the current state of things.

### The 500-Token Cap

**Keep `_hot.md` under 500 tokens at all times.** This is a hard limit.

The reason: Claude reads `_hot.md` before deciding whether to go deeper into the wiki. If `_hot.md` is large, it costs tokens on every query, even ones that don't need the wiki at all. Keeping it under 500 tokens means it's fast, cheap, and always gets read.

Use `wc -w _hot.md` to check word count (multiply by ~1.3 for a rough token estimate). 380 words ≈ 500 tokens.

### What Goes In \_hot.md

```markdown
# React Wiki — Working Memory

**Last updated:** 2026-04-17
**Wiki coverage:** React 18.x, React Router v6, Redux Toolkit

## Active Context
- Currently building: migration guide from class to functional components
- Last synthesis run: 2026-04-15 (added 8 new hooks pages)

## Key Facts
- React 18 introduced concurrent features: Suspense, startTransition, useDeferredValue
- useEffect runs after every render by default; add dependency array to control when
- React.StrictMode intentionally double-invokes effects in development — not a bug
- Key prop on list items prevents reconciliation issues

## Recent Changes
- 2026-04-15: Added useTransition.md, useDeferredValue.md, useId.md
- 2026-04-10: Updated State-Management.md to cover Zustand alongside Redux

## Gaps / Known Unknowns
- Server Components not yet covered (raw sources not captured yet)
- No page on testing (React Testing Library)

## Quick Navigation
- All hooks: [[_index-hooks]]
- State management comparison: [[useState-vs-useReducer]]
- Master index: [[index]]
```

**Sections to include:**

| Section | What it contains | Max length |
|---------|-----------------|------------|
| Active Context | What you're currently working on | 2-3 lines |
| Key Facts | The most important facts about this domain | 4-6 bullets |
| Recent Changes | Last 3-5 wiki updates with dates | 3-5 lines |
| Gaps | Topics not yet covered | 2-3 lines |
| Quick Navigation | Direct links to most-used pages | 3-5 links |

### When to Update \_hot.md

Update `_hot.md` after every significant wiki operation:
- After a synthesis run (adding new pages)
- After updating a page with new information
- When you learn about a breaking change in the domain
- When you discover a gap in coverage

The update itself takes under 5 minutes — just edit the relevant section and bump the "Last updated" date.

---

## Chapter 8: The Tiered Retrieval Protocol

### How the Runtime Uses Your Wiki

Claude_Meister's context router implements a five-step escalating read sequence when it needs domain knowledge. Each step costs a small number of tokens but can satisfy the query without going further:

**Step 1: Read `_hot.md` (~100 tokens)**
The context router reads `_hot.md` first. If the question can be answered from working memory alone, the sequence stops here.

**Step 2: Read `index.md` (~200 tokens)**
If `_hot.md` doesn't answer the question, the router reads the master index to identify which domain and page is relevant.

**Step 3: Read domain sub-index (~150 tokens)**
If the master index points to a domain with a sub-index, the router reads that sub-index to narrow down to specific pages or raw files.

**Step 4: Read 1-2 wiki pages (~500-800 tokens)**
The router reads the specific entity or concept pages identified in Steps 2-3.

**Step 5: Hard cap**
The router never reads more than 5 pages per query. If 5 pages don't answer the question, Claude reports what it found and asks for clarification rather than reading further.

**Total cost per query:** 100–1,250 tokens depending on how deep the sequence goes. Compare this to pasting raw docs into the conversation (often 2,000–10,000 tokens for a single doc).

### Configuring wiki\_path

To point Claude_Meister's context router at your wiki, set the `wiki_path` field in your runtime config.

Open `C:/Users/yourname/.claude_runtime/configs/runtime_config.json`. See `docs/configuration.md` for a full reference of all configuration fields. The relevant section looks like this:

```json
{
  "wiki_path": "C:/Users/yourname/wikis/my-react-wiki",
  "wiki_enabled": true,
  "wiki_hot_file": "_hot.md",
  "wiki_index_file": "index.md",
  "wiki_max_pages_per_query": 5
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `wiki_path` | string | Absolute path to your wiki's root directory |
| `wiki_enabled` | boolean | Set to `true` to enable wiki retrieval |
| `wiki_hot_file` | string | Filename of your working memory file (default: `_hot.md`) |
| `wiki_index_file` | string | Filename of your master index (default: `index.md`) |
| `wiki_max_pages_per_query` | integer | Hard cap on pages read per query (default: 5) |

**Set `wiki_path` to the absolute path of your wiki directory.** Use forward slashes even on Windows (JSON requires it):

```json
"wiki_path": "C:/Users/yourname/wikis/my-react-wiki"
```

Not:
```json
"wiki_path": "C:\\Users\\yourname\\wikis\\my-react-wiki"
```

### Testing That Retrieval Works

After setting `wiki_path`, test the connection by starting a new Claude Code session and asking a question you know your wiki can answer:

```
(In a new Claude Code conversation)
Can you check my React wiki and tell me how useEffect works?
```

**Expected behavior:** Claude reads `_hot.md`, then `index.md`, then navigates to `entities/useEffect.md` and answers from that page. The answer should include details from your synthesized wiki page, not generic Claude knowledge.

**If you see Claude answer from its training data instead of your wiki:** Check that `wiki_enabled` is set to `true` and that `wiki_path` is correct. Open the path in File Explorer to confirm it exists.

**If you see an error like "wiki_path not found":** The path has a typo or uses backslashes. Correct it and restart Claude Code.

**If you see Claude read too many pages (more than 5):** Decrease `wiki_max_pages_per_query` to 3 and see if that resolves the issue.

---

## Chapter 9: Maintaining and Evolving the Wiki

A wiki that isn't maintained becomes a liability — stale docs are worse than no docs because they give false confidence. This chapter covers how to keep your wiki current without letting it become a second job.

### When to Add New Sources

Add new raw sources and synthesize new pages when:
- A new major version of the domain is released (React 19, etc.)
- A significant new API or feature is announced
- You encounter a question during a project that your wiki couldn't answer
- The official docs add a section that wasn't there before

**Trigger:** If you ask Claude a domain question and it says "I don't have that in your wiki," that's a signal to add a source.

### When to Update Existing Pages

Update existing wiki pages when:
- An API you documented changes its signature
- A pattern you documented is now deprecated
- You discover your synthesized page was incomplete or wrong
- Better documentation exists for the same topic

**Signal:** If Claude gives you outdated information from a wiki page, that page needs updating.

### Using log.md

`log.md` is your audit trail. Every time you run a synthesis session, add an entry:

```markdown
## 2026-04-17 — Added Concurrent Features pages

**Session type:** Synthesis (new pages)
**Raw files processed:** Suspense.md, startTransition.md, useDeferredValue.md
**Pages created:**
- entities/Suspense.md
- entities/useTransition.md
- entities/useDeferredValue.md
- concepts/Concurrent-Rendering.md
**Index updated:** Yes
**_hot.md updated:** Yes
**Notes:** React 18 concurrent docs are scattered across 4 different pages — synthesized into one concept page for clarity.
```

This log tells you exactly what was covered and when. When React 19 drops and you need to find pages about concurrent features to update, `log.md` tells you exactly which pages were synthesized from which sources.

### The Update Cycle

Every time you add or update content, follow this sequence:

```
1. Add raw source → raw/New-Feature-Docs.md
2. Synthesize → Update or create the relevant wiki page(s)
3. Update sub-index → Add/update entry in the relevant _index-{domain}.md
4. Update master index → Add/update entry in index.md
5. Update _hot.md → Add to "Recent Changes", update "Key Facts" if significant
6. Add entry to log.md
```

Steps 3-6 take about 15 minutes once the synthesis is done.

### Preventing Bloat

The wiki should never feel unwieldy. Rules to keep it lean:

- **One page per entity.** If a hook has two pages, merge them.
- **Sources summarize raw files; wiki pages synthesize.** Don't put raw content in wiki pages.
- **Delete pages that become obsolete.** Remove the entry from index.md and the relevant sub-index. Log the deletion in log.md.
- **Audit quarterly.** Once every 3 months, scan the index and ask: "Is this still accurate? Is this still relevant?" Delete ruthlessly.
- **`_hot.md` stays under 500 tokens.** If it grows past that, cut the least recent items.

---

## Chapter 10: Example — Building a Wiki for React

This chapter walks through the entire pipeline end-to-end for React. Follow along to see exactly what each step produces, then adapt the same approach for your own domain.

### The Domain

**React** — the JavaScript library for building user interfaces, maintained by Meta. Primary official source: [react.dev](https://react.dev).

We'll build a focused wiki covering React 18.x: hooks, component patterns, state management, and the new concurrent features. We'll deliberately exclude React Native, Next.js, and testing — those are big enough to be their own wikis.

---

### Step 1: Identify Sources

Here are the exact URLs to capture for a solid React wiki:

**High Priority (capture these first):**

| URL | What to name the file |
|-----|----------------------|
| https://react.dev/learn | Getting-Started.md |
| https://react.dev/reference/react | Hooks-API-Reference.md |
| https://react.dev/learn/thinking-in-react | Thinking-in-React.md |
| https://react.dev/learn/managing-state | Managing-State.md |
| https://react.dev/learn/synchronizing-with-effects | Synchronizing-with-Effects.md |
| https://react.dev/reference/react/hooks | Built-in-Hooks.md |
| https://react.dev/blog/2022/03/29/react-v18 | React-18-Release.md |
| https://react.dev/blog/2023/03/16/introducing-react-dev | React-Dev-Launch.md |

**Medium Priority:**

| URL | What to name the file |
|-----|----------------------|
| https://react.dev/learn/passing-data-deeply-with-context | Context-API.md |
| https://react.dev/learn/scaling-up-with-reducer-and-context | Reducer-and-Context.md |
| https://react.dev/reference/react/useReducer | useReducer.md |
| https://react.dev/reference/react/useCallback | useCallback.md |
| https://react.dev/reference/react/useMemo | useMemo.md |
| https://react.dev/learn/you-might-not-need-an-effect | You-Might-Not-Need-an-Effect.md |
| https://react.dev/reference/react/Suspense | Suspense.md |
| https://react.dev/reference/react/startTransition | startTransition.md |

Use MarkDownload to capture each page, or copy-paste into markdown files. Save all to `raw/`.

---

### Step 2: The Triage Catalog

After running the Triage prompt from Chapter 5 on these files, you'd get a catalog like this:

```markdown
| Filename | Domain | Summary | Priority |
|---|---|---|---|
| Getting-Started.md | basics | Intro to React: components, JSX, props, state | High |
| Hooks-API-Reference.md | hooks | Overview of all built-in hooks with brief descriptions | High |
| Thinking-in-React.md | concepts | How to think in components; state identification process | High |
| Managing-State.md | state | Principles for organizing and lifting state | High |
| Synchronizing-with-Effects.md | hooks | Deep dive on useEffect, cleanup, dependency array | High |
| Built-in-Hooks.md | hooks | Full reference for useState, useEffect, useContext, etc. | High |
| React-18-Release.md | history | What's new in React 18: concurrent mode, Suspense, transitions | Medium |
| Context-API.md | state | createContext, useContext, Provider patterns | Medium |
| Reducer-and-Context.md | state | Combining useReducer with Context for scalable state | Medium |
| useReducer.md | hooks | useReducer API, when to use vs useState | Medium |
| useCallback.md | hooks | useCallback for memoizing functions | Medium |
| useMemo.md | hooks | useMemo for expensive computations | Medium |
| You-Might-Not-Need-an-Effect.md | concepts | Anti-patterns: when not to use useEffect | High |
| Suspense.md | concurrent | Suspense component for async loading states | Medium |
| startTransition.md | concurrent | startTransition and useTransition for non-urgent updates | Medium |
| React-Dev-Launch.md | history | Overview of the new react.dev documentation site | Low |
```

Domains: `basics` (1 file), `hooks` (6 files), `concepts` (2 files), `state` (3 files), `concurrent` (2 files), `history` (2 files).

Sub-indexes to create: `_index-hooks.md` (6 files) and `_index-state.md` (3 files). Remaining domains go only in the master index.

---

### Step 3: The Vault Structure Applied to React

After synthesis, your React wiki looks like this:

```
my-react-wiki/
├── _hot.md
├── index.md
├── overview.md
├── log.md
├── _index-hooks.md
├── _index-state.md
├── raw/
│   ├── catalog.md
│   ├── synthesis-plan.md
│   ├── Getting-Started.md
│   └── ... (16 raw files)
├── entities/
│   ├── useState.md
│   ├── useEffect.md
│   ├── useContext.md
│   ├── useReducer.md
│   ├── useCallback.md
│   ├── useMemo.md
│   ├── useRef.md
│   ├── Suspense.md
│   └── React-Context.md
├── concepts/
│   ├── Component-Lifecycle.md
│   ├── State-Management-Patterns.md
│   ├── Rendering-Behavior.md
│   ├── When-Not-to-Use-Effects.md
│   └── Concurrent-Rendering.md
├── comparisons/
│   ├── useState-vs-useReducer.md
│   └── useCallback-vs-useMemo.md
├── guides/
│   ├── Thinking-in-React.md
│   └── Lifting-State-Up.md
└── sources/
    └── (summaries of raw files)
```

---

### Step 4: The Exact Prompts Adapted for React

**React Triage Prompt:**

```
I'm building a knowledge wiki for React 18.x (the JavaScript UI library).

I have raw documentation files from react.dev and the React blog. I'm going to share them one by one. For each file, categorize it using these domains: basics, hooks, state, concepts, concurrent, history, performance.

Add each to a catalog:
| Filename | Domain | Summary | Priority |

When I've shared all files, output the final table and identify which domains have 5+ files (candidates for sub-indexes).

First file:
[paste Getting-Started.md]
```

**React Entity Synthesis Prompt (for `useEffect`):**

```
I'm writing wiki pages for a React 18.x knowledge base. Write a wiki page for: useEffect

Use this format:

---
title: useEffect
type: entity
created: 2026-04-17
updated: 2026-04-17
sources: [raw/Synchronizing-with-Effects.md, raw/Built-in-Hooks.md, raw/You-Might-Not-Need-an-Effect.md]
tags: [hook, side-effects, lifecycle, cleanup, dependency-array]
---

# useEffect

## What It Is
(1-2 sentence definition of useEffect)

## Syntax
(The function signature and parameters)

## How It Works
(How React schedules and runs effects. When does it run? When does cleanup run?)

## Dependency Array Behavior
(What happens with no array, empty array, array with values)

## Common Patterns
(Data fetching, subscriptions, DOM manipulation — 3 mini examples)

## Gotchas and Warnings
(Double-invocation in StrictMode, stale closures, infinite loop patterns)

## When NOT to Use useEffect
(Summarize the "You Might Not Need an Effect" guidance)

## Related Pages
([[useState]], [[useCallback]], [[Component Lifecycle]], [[When-Not-to-Use-Effects]])

Here are the source files:
[paste Synchronizing-with-Effects.md]
[paste You-Might-Not-Need-an-Effect.md]
```

**React Index Prompt:**

```
I've synthesized a React 18.x knowledge wiki. Write the master index.md.

Here are all my pages:

Entities: useState, useEffect, useContext, useReducer, useCallback, useMemo, useRef, Suspense, React-Context
Concepts: Component-Lifecycle, State-Management-Patterns, Rendering-Behavior, When-Not-to-Use-Effects, Concurrent-Rendering
Comparisons: useState-vs-useReducer, useCallback-vs-useMemo
Guides: Thinking-in-React, Lifting-State-Up

Format as:

---
title: Index
type: index
created: 2026-04-17
updated: 2026-04-17
sources: []
tags: [index]
---

# React 18.x Wiki — Index

## Entities (Hooks & Components)
| Page | Description |
...

## Concepts
| Page | Description |
...

Use [[wikilinks]]. One-line descriptions only. Keep it under 300 lines.
```

---

### Step 5: What the Final \_hot.md Looks Like

```markdown
# React Wiki — Working Memory

**Last updated:** 2026-04-17
**Coverage:** React 18.x (hooks, state, concurrent features). Excludes: React Native, Next.js, testing.

## Key Facts
- React 18: introduced concurrent mode, Suspense for data, startTransition, useDeferredValue, useId
- useEffect: runs after paint; cleanup runs before re-run and on unmount
- StrictMode double-invokes effects in dev — intentional, not a bug
- useReducer preferred over useState when state logic is complex or involves multiple sub-values
- useMemo/useCallback: premature optimization — only add when you measure a problem

## Recent Changes
- 2026-04-17: Initial synthesis — 9 entity pages, 5 concept pages, 2 comparison pages

## Gaps
- React Server Components not covered
- React Testing Library not covered
- React DevTools not covered

## Quick Navigation
- All hooks: [[_index-hooks]]
- State patterns: [[_index-state]]
- Master index: [[index]]
```

Token count: ~280 words ≈ ~365 tokens. Well within the 500-token cap.

---

### Step 6: Configure wiki\_path for the React Wiki

Open `C:/Users/yourname/.claude_runtime/configs/runtime_config.json` and add:

```json
{
  "wiki_path": "C:/Users/yourname/wikis/my-react-wiki",
  "wiki_enabled": true,
  "wiki_hot_file": "_hot.md",
  "wiki_index_file": "index.md",
  "wiki_max_pages_per_query": 5
}
```

See `docs/configuration.md` for full field reference and advanced options.

### Step 7: Test the React Wiki

Start a new Claude Code session and run this test:

```
Check my React wiki and answer: What is the difference between useCallback and useMemo?
```

**Expected retrieval path:**
1. Read `_hot.md` — mentions useMemo and useCallback are in the wiki
2. Read `index.md` — sees `comparisons/useCallback-vs-useMemo.md`
3. Read `comparisons/useCallback-vs-useMemo.md` — answers the question

**Expected answer quality:** Claude should give a detailed, accurate answer using your synthesized comparison page — including the exact gotchas and patterns you included during synthesis, not just a generic answer from its training data.

This is the pipeline working as intended.

---

## Quick Reference

### The Complete Synthesis Checklist

```
Phase 1: Gather
[ ] Identify 10-30 high-quality raw sources
[ ] Capture each as a .md file using MarkDownload or manual copy
[ ] Name files descriptively (title-case, hyphens)
[ ] Store in raw/ directory

Phase 2: Structure
[ ] Create wiki directory structure (8 subdirectories)
[ ] Verify directory exists and is writable

Phase 3: Triage
[ ] Run Triage prompt → get catalog.md
[ ] Run Deep Read prompt → get synthesis-plan.md
[ ] Identify sub-index candidates (domains with 5+ files)

Phase 4: Synthesize
[ ] Create all entity pages (entities/)
[ ] Create all concept pages (concepts/)
[ ] Create comparison and guide pages if needed

Phase 5: Index
[ ] Build sub-indexes (_index-{domain}.md)
[ ] Build master index.md
[ ] Write _hot.md (under 500 tokens)

Phase 6: Connect
[ ] Set wiki_path in runtime_config.json
[ ] Set wiki_enabled: true
[ ] Test retrieval with a known question

Phase 7: Log
[ ] Write initial entry in log.md
```

### The Retrieval Sequence (For Reference)

```
Query arrives
→ Read _hot.md (~100 tokens)
  → Answered? Stop.
  → Not answered? Continue.
→ Read index.md (~200 tokens)
  → Identified page? Go to Step 4.
  → Identified domain? Go to Step 3.
→ Read _index-{domain}.md (~150 tokens)
  → Identified page? Go to Step 4.
→ Read 1-2 wiki pages (~500-800 tokens)
→ Hard cap: never exceed 5 pages per query
```

---

*For configuration field details, see `docs/configuration.md`.*
*For installation and setup, see the project README.*
*For the runtime context router that drives retrieval, see `C:/Users/yourname/.claude_runtime/core/context_router.md`.*
