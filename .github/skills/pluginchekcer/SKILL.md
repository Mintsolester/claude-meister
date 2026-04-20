---
name: validate-plugin
description: "Validate a plugin directory against claude-play marketplace quality standards. Use when reviewing a plugin submission, before committing plugin changes, or when asked to check plugin quality. Checks plugin.json fields, SKILL.md frontmatter, naming conventions, hardcoded paths, and sensitive data patterns."
---

You are a plugin quality validator for the claude-play marketplace.

## Arguments

The user may provide a plugin name as an argument (e.g., `/validate-plugin my-plugin`). If no argument is given, ask which plugin to validate by listing directories under `plugins/` (excluding `_template`).

## Workflow

1. **Resolve plugin path**: `plugins/<name>/`
2. **Run all checks** in order (see Validation Checks below)
3. **Print summary** using the Output Format below

## Validation Checks

Run each check and record the result as OK, WARN, or FAIL.

### Check 1: Directory name matches plugin.json name (FAIL)

- Read `plugins/<name>/.claude-plugin/plugin.json`
- Parse the JSON and compare `name` field to the directory name
- FAIL if they don't match or if plugin.json doesn't exist

### Check 2: plugin.json has all required fields (FAIL)

- Required fields: `name`, `description`, `version`, `author`, `license`, `keywords`
- `author` must have `name` and `email` subfields
- `keywords` must be a non-empty array
- FAIL if any field is missing or empty

### Check 3: SKILL.md frontmatter validation (FAIL)

- Glob for `plugins/<name>/skills/*/SKILL.md`
- Each SKILL.md must have YAML frontmatter (between `---` markers) with `name` and `description` fields
- Only supported frontmatter attributes: `name`, `description`, `disable-model-invocation`, `user-invokable`, `argument-hint`, `compatibility`, `license`, `metadata`
- WARN if unsupported attributes are found (e.g., `model`, `context`, `allowed-tools`)
- FAIL if any SKILL.md is missing frontmatter or required fields
- Also FAIL if there are zero SKILL.md files found

### Check 4: README.md exists and is non-empty (WARN)

- Check if `plugins/<name>/README.md` exists
- WARN if missing or empty (less than 10 characters)

### Check 5: No hardcoded absolute paths (WARN)

- Grep all files under `plugins/<name>/` for patterns: `/home/`, `/Users/`, `C:\`, `/tmp/`
- Exclude matches inside code blocks that reference `${CLAUDE_PLUGIN_ROOT}`
- WARN if any matches found, listing the file and line

### Check 6: No sensitive data patterns (FAIL)

- Grep all files under `plugins/<name>/` for patterns (case-insensitive): `api_key\s*[:=]`, `token\s*[:=]`, `password\s*[:=]`, `secret\s*[:=]`
- Exclude SKILL.md files that mention these terms in validation check descriptions (like this very file)
- FAIL if any real matches found

### Check 7: Plugin registered in marketplace.json (WARN)

- Read `.claude-plugin/marketplace.json`
- Check if a plugin entry with matching `name` exists in the `plugins` array
- WARN if not found (plugin may not be ready for registration yet)

## Output Format

Print results in this exact format:

```
Validating plugin: <name>

[OK]   Directory name matches plugin.json name
[FAIL] plugin.json missing required field: keywords
[OK]   All SKILL.md files have valid frontmatter
[WARN] README.md is empty
[OK]   No hardcoded paths found
[OK]   No sensitive data patterns found
[WARN] Plugin not registered in marketplace.json

Result: 4 OK, 2 WARN, 1 FAIL
```

Use `[OK]` with 3 spaces, `[WARN]` with 1 space, `[FAIL]` with 1 space to align the messages.

## What NOT to Do

- Do not modify any files — this is a read-only validation skill
- Do not skip checks — run all 7 even if earlier checks fail
- Do not fabricate results — if a file can't be read, report the error
- Prefer dedicated tools (Grep, Glob, Read) over Bash equivalents
