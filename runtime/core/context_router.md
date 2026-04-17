# Context Router

You are reading this because the current task is Moderate or higher complexity. Use this decision tree to determine what context to load. Follow ONLY the branches that match — skip everything else.

## Step 1: Select Mode

Read `{{RUNTIME_PATH}}/core/mode_selector.md` to determine LIGHT/STANDARD/DEEP based on your task classification. This sets your context budget.

## Step 2: Walk the Decision Tree

Check each condition. If it matches, execute the action. Multiple branches can match.

### Memory (Does this task involve prior work in this repo?)

**Yes →** Determine the best memory source:
```bash
python "{{RUNTIME_PATH}}/controllers/mcp_router.py" --check --working-dir "." --query "YOUR_TASK_KEYWORDS"
```
Follow the returned recommendation (local cache, memory_controller, or MCP tool).

**No →** Skip memory entirely. Do not call memory_retrieve.

### Wiki (Does this task involve Claude/Anthropic capabilities?)

Tasks involving the Claude API, MCP, Agent SDK, model selection, prompt engineering, or Claude Code features.

**Yes →** Read `{{WIKI_PATH}}/_hot.md` first (~500 tokens). If that doesn't resolve your question, read `wiki/index.md` and open 1-2 relevant sub-indexes. Never read more than 5 wiki pages total.

**No →** Skip the wiki entirely.

### Skills (Is this a feature, bug fix, or multi-step task?)

**Yes →** Read `{{RUNTIME_PATH}}/core/skill_router.md` for the task-to-skill mapping. Invoke the matching skill before starting work.

**No →** Skip skill routing.

### Tool Discovery (Unfamiliar codebase or many tools available?)

**Yes →** Discover available tools:
```bash
python "{{RUNTIME_PATH}}/controllers/tool_loader.py" --query "TASK_KEYWORD"
```
Add additional `--scan-dir` arguments for repo-specific tool directories.

**No →** Use tools you already know about.

### Advisor (Architectural decision with multiple valid approaches?)

Only if you have a custom advisor tool configured in `tools_dirs`:
```bash
python "YOUR_ADVISOR_TOOL" -p "YOUR_STRATEGIC_QUESTION" [-c context_file]
```

### Cross-Repo (Does this task span multiple repositories?)

**Yes →** Query memory across all repos:
```bash
python "{{RUNTIME_PATH}}/controllers/memory_controller.py" --query "KEYWORDS" --cross-repo --max-tokens 300
```

**No →** Stay within current repo context.

## Step 3: Token Budget Check

Read `{{RUNTIME_PATH}}/core/token_budget.md` for your mode's budget. Ensure you haven't exceeded it.

## Step 4: After Task Completion

For STANDARD and DEEP mode tasks, log usage:
```bash
python "{{RUNTIME_PATH}}/controllers/usage_logger.py" --mode MODE --tools-used "tool1,tool2" --memory-tokens N --task-summary "what you did"
```

For DEEP mode, also store intelligence if the task produced reusable insights:
- Call `memory_store` MCP tool with compressed findings (max 200 tokens)
