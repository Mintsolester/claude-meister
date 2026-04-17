"""Structured debate template generator for multi-perspective decision analysis."""

import json
from pathlib import Path

from repo_detector import MEMORY_ROOT


def generate_debate(decision: str, context: str, repo: str) -> dict:
    """
    Generate structured debate templates for 5 internal agents.

    Claude Code works through each role in-conversation, then records verdict.
    """
    # Gather related past outcomes for this repo
    related_outcomes = _get_related_outcomes(repo, decision)

    outcome_context = ""
    if related_outcomes:
        outcome_context = "\n\nRelevant past outcomes:\n"
        for o in related_outcomes[:3]:
            status = "SUCCESS" if o.get("success") else "FAILURE"
            outcome_context += f"- [{status}] Expected: {o.get('expected_result', 'N/A')[:80]} | Actual: {o.get('actual_result', 'N/A')[:80]}\n"
            if o.get("improvement_signal"):
                outcome_context += f"  Signal: {o['improvement_signal'][:100]}\n"

    base_context = f"Decision: {decision}\n\nContext: {context}{outcome_context}"

    return {
        "initial_decision": decision,
        "roles": {
            "optimist": {
                "prompt": (
                    "You are the OPTIMIST. Defend this decision.\n"
                    "- What are the strongest arguments in favor?\n"
                    "- What goes right if we proceed?\n"
                    "- What opportunities does this create?\n"
                    "Be specific and evidence-based, not blindly positive."
                ),
                "context": base_context,
            },
            "skeptic": {
                "prompt": (
                    "You are the SKEPTIC. Attack the assumptions.\n"
                    "- What assumptions are being made that might be wrong?\n"
                    "- What evidence contradicts this decision?\n"
                    "- What's being overlooked or hand-waved?\n"
                    "Be constructively critical, not contrarian."
                ),
                "context": base_context,
            },
            "analyst": {
                "prompt": (
                    "You are the ANALYST. Evaluate the logic.\n"
                    "- Is the reasoning chain sound?\n"
                    "- Are the premises valid?\n"
                    "- Does the conclusion follow from the evidence?\n"
                    "- Are there logical gaps or leaps?\n"
                    "Be rigorous and methodical."
                ),
                "context": base_context,
            },
            "risk": {
                "prompt": (
                    "You are the RISK ASSESSOR. Identify downsides.\n"
                    "- What could go wrong?\n"
                    "- What's the worst-case scenario?\n"
                    "- What's the cost of being wrong?\n"
                    "- Are there irreversible consequences?\n"
                    "Quantify risk where possible."
                ),
                "context": base_context,
            },
            "judge": {
                "prompt": (
                    "You are the JUDGE. Synthesize all perspectives.\n"
                    "- Weigh the optimist's case against the skeptic's objections\n"
                    "- Consider the analyst's logic assessment\n"
                    "- Factor in the risk assessor's concerns\n"
                    "- Deliver a clear verdict: PROCEED, MODIFY, or REJECT\n"
                    "- If MODIFY, specify exactly what to change\n"
                    "Be decisive."
                ),
                "context": base_context,
            },
        },
        "related_outcomes": related_outcomes[:3],
        "instructions": (
            "Work through each role in order: Optimist → Skeptic → Analyst → Risk → Judge.\n"
            "For each role, think from that perspective using the provided prompt.\n"
            "After the Judge's verdict, record the final decision using memory_store (type: decision)\n"
            "and note the debate result in the tags."
        ),
    }


def _get_related_outcomes(repo: str, decision: str) -> list:
    """Find past outcomes that might be relevant to this decision."""
    outcomes_dir = MEMORY_ROOT / "repos" / repo / "outcomes"
    if not outcomes_dir.exists():
        return []

    results = []
    decision_lower = decision.lower()
    decision_words = set(decision_lower.split())

    for f in outcomes_dir.glob("*.json"):
        try:
            outcome = json.loads(f.read_text(encoding="utf-8"))
            # Simple keyword overlap check
            outcome_text = (
                outcome.get("expected_result", "") + " " + outcome.get("actual_result", "")
            ).lower()
            outcome_words = set(outcome_text.split())
            overlap = len(decision_words & outcome_words)
            if overlap >= 2:
                results.append(outcome)
        except Exception:
            continue

    # Sort by timestamp descending
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results
