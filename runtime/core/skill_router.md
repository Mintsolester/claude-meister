# Skill Router

Use this table to determine which superpowers skill to invoke for the current task. If a match exists, invoke the skill BEFORE starting implementation work.

## Task-to-Skill Mapping

| Task Pattern | Skill | When to Invoke |
|---|---|---|
| Building a new feature or component | `superpowers:brainstorming` | Before any implementation. Explores intent and design. |
| Planning a multi-step implementation | `superpowers:writing-plans` | Complex+ tasks that need a structured approach |
| Executing an existing plan | `superpowers:executing-plans` | When a plan file already exists in the session |
| 2+ independent tasks in one request | `superpowers:dispatching-parallel-agents` | When subtasks have no shared state or dependencies |
| Bug, test failure, unexpected behavior | `superpowers:systematic-debugging` | Before proposing any fix. Diagnose first. |
| About to claim work is "done" or "fixed" | `superpowers:verification-before-completion` | Always. Run verification commands before success claims. |
| Major feature completed, ready for review | `superpowers:requesting-code-review` | After significant implementation milestones |
| Receiving code review feedback | `superpowers:receiving-code-review` | Before implementing review suggestions |
| Implementation complete, deciding how to integrate | `superpowers:finishing-a-development-branch` | When all tests pass and work is ready to merge/PR |
| Need isolated workspace for feature work | `superpowers:using-git-worktrees` | Before starting work that needs repo isolation |
| Creating or editing a skill | `superpowers:writing-skills` | When building automation or new skills |
| Test-driven development | `superpowers:test-driven-development` | When implementing features where tests should come first |

## Rules

1. **One process skill first.** If both brainstorming and debugging could apply, pick the one that matches the primary intent.
2. **Don't invoke for LIGHT mode.** Trivial/Simple tasks skip skill routing entirely.
3. **Skills are not optional for Complex+.** If the table has a match for a Complex or Architectural task, you must invoke it.
