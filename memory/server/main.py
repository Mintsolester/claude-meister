"""Global Memory + Evolution Engine — MCP Server.

A pure-local intelligence layer for Claude Code.
Zero API calls, all processing on-device.
"""

import sys
import os

# Add server directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

import memory_store
import memory_retriever
import memory_scorer
import evolution_engine
import debate_engine
import cleanup
import repo_detector

mcp = FastMCP("Claude Memory")


@mcp.tool()
def memory_retrieve(
    query: str,
    repo: str,
    context_type: str = "all",
    max_tokens: int = 500,
    working_dir: str = "",
) -> dict:
    """Retrieve relevant memory context for the current task.

    Searches local repo cache first (hot.md, recent sessions), then global memory.
    Returns ranked results within token budget.

    Args:
        query: What context is needed (describe the task or question)
        repo: Current repository name
        context_type: Filter by type: session, decision, pattern, structure, or all
        max_tokens: Maximum tokens to return (default 500)
        working_dir: Working directory path (for local cache access)
    """
    return memory_retriever.retrieve(
        query=query,
        repo=repo,
        context_type=context_type,
        max_tokens=max_tokens,
        working_dir=working_dir or None,
    )


@mcp.tool()
def memory_store(
    repo: str,
    type: str,
    content: str,
    tags: list[str] = None,
    outcome: dict = None,
    working_dir: str = "",
) -> dict:
    """Store compressed intelligence after completing a task.

    Compresses content, assigns scores, updates local and global indexes.

    Args:
        repo: Repository name
        type: Entry type: session, decision, pattern, structure, or outcome
        content: The intelligence to store (will be compressed)
        tags: Descriptive tags for search
        outcome: Optional outcome data: {decision_id, expected_result, actual_result, success, error_analysis}
        working_dir: Working directory path (for local cache update)
    """
    return memory_store.store_entry(
        repo=repo,
        entry_type=type,
        content=content,
        tags=tags,
        outcome=outcome,
        working_dir=working_dir or None,
    )


@mcp.tool()
def memory_evolve(
    repo: str,
    decision_id: str,
    expected_result: str,
    actual_result: str,
    success: bool,
    error_analysis: str = "",
) -> dict:
    """Process an outcome and generate evolution signals.

    Compares expected vs actual results, classifies failures, adjusts confidence
    on linked decisions, and detects recurring patterns. Conservative mode:
    returns suggestions but doesn't auto-apply.

    Args:
        repo: Repository name
        decision_id: ID of the decision this outcome relates to
        expected_result: What was supposed to happen
        actual_result: What actually happened
        success: Whether the outcome was successful
        error_analysis: Explanation of what went wrong (if failure)
    """
    return evolution_engine.record_outcome(
        repo=repo,
        decision_id=decision_id,
        expected_result=expected_result,
        actual_result=actual_result,
        success=success,
        error_analysis=error_analysis,
    )


@mcp.tool()
def memory_debate(
    decision: str,
    context: str,
    repo: str,
) -> dict:
    """Generate structured debate templates for multi-perspective analysis.

    Returns 5 role-specific prompts (Optimist, Skeptic, Analyst, Risk, Judge)
    pre-filled with context and related past outcomes. Work through each role
    in-conversation to stress-test the decision.

    Args:
        decision: The decision to debate
        context: Relevant background information
        repo: Repository name (for finding related past outcomes)
    """
    return debate_engine.generate_debate(
        decision=decision,
        context=context,
        repo=repo,
    )


@mcp.tool()
def memory_cleanup(
    repo: str = "",
    dry_run: bool = False,
) -> dict:
    """Remove stale and orphan memory entries.

    Removes entries with: score < 10, unused > 90 days, or orphan references.
    Use dry_run=true to preview what would be removed without deleting.

    Args:
        repo: Specific repo to clean, or empty for all repos
        dry_run: If true, only preview removals without deleting
    """
    return cleanup.run_cleanup(
        repo=repo or None,
        dry_run=dry_run,
    )


@mcp.tool()
def memory_status() -> dict:
    """Dashboard of memory system health.

    Returns entry counts per repo, storage size, average scores,
    last cleanup date, and pending evolution signals.
    """
    import json
    from pathlib import Path

    root = repo_detector.MEMORY_ROOT
    repos_dir = root / "repos"
    global_patterns_dir = root / "global_patterns"

    repos_info = {}
    total_entries = 0
    total_size = 0

    if repos_dir.exists():
        for repo_path in repos_dir.iterdir():
            if not repo_path.is_dir():
                continue
            count = 0
            size = 0
            for type_dir in ["sessions", "decisions", "patterns", "structure", "outcomes", "evolution"]:
                td = repo_path / type_dir
                if td.exists():
                    for f in td.glob("*.json"):
                        count += 1
                        size += f.stat().st_size
            repos_info[repo_path.name] = {"entries": count, "size_kb": round(size / 1024, 1)}
            total_entries += count
            total_size += size

    # Global patterns count
    gp_count = 0
    if global_patterns_dir.exists():
        gp_count = len(list(global_patterns_dir.glob("*.json")))

    # Last cleanup
    cleanup_log = root / "cleanup_log.json"
    last_cleanup = None
    try:
        log = json.loads(cleanup_log.read_text(encoding="utf-8"))
        if log:
            last_cleanup = log[-1].get("timestamp")
    except Exception:
        pass

    # Pending evolution signals
    pending_signals = 0
    for repo_name, info in repos_info.items():
        evo_dir = repos_dir / repo_name / "evolution"
        if evo_dir.exists():
            pending_signals += len(list(evo_dir.glob("*.json")))

    return {
        "repos": repos_info,
        "global_patterns": gp_count,
        "total_entries": total_entries,
        "total_size_kb": round(total_size / 1024, 1),
        "last_cleanup": last_cleanup,
        "pending_evolution_signals": pending_signals,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
