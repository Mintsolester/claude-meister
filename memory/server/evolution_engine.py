"""Outcome-driven evolution engine: track results, detect patterns, suggest improvements."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from repo_detector import MEMORY_ROOT, ensure_repo_dirs

EVOLUTION_LOG = MEMORY_ROOT / "evolution_log.json"

FAILURE_TYPES = {
    "logic_error": "Reasoning or logic was flawed",
    "wrong_approach": "Chose an incorrect strategy or method",
    "incomplete_info": "Lacked necessary information to decide correctly",
    "external_failure": "External system or dependency failed",
    "scope_creep": "Task expanded beyond original intent",
    "misunderstanding": "Misinterpreted the requirement",
}


def _load_json(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_outcome(
    repo: str,
    decision_id: str,
    expected_result: str,
    actual_result: str,
    success: bool,
    error_analysis: str = "",
) -> dict:
    """
    Record an outcome and generate evolution signals.

    Conservative mode: returns suggestions but doesn't auto-apply changes.
    """
    repo_path = ensure_repo_dirs(repo)
    now = datetime.now(timezone.utc).isoformat()
    outcome_id = str(uuid.uuid4())

    # Build outcome record
    outcome = {
        "id": outcome_id,
        "decision_id": decision_id,
        "expected_result": expected_result,
        "actual_result": actual_result,
        "success": success,
        "error_analysis": error_analysis,
        "improvement_signal": "",
        "timestamp": now,
    }

    # Classify failure and generate improvement signal
    signals = []
    if not success:
        failure_type = _classify_failure(error_analysis, expected_result, actual_result)
        recommendation = _generate_recommendation(failure_type, error_analysis)
        outcome["improvement_signal"] = recommendation

        signal = {
            "id": str(uuid.uuid4()),
            "outcome_id": outcome_id,
            "decision_id": decision_id,
            "failure_type": failure_type,
            "root_cause": error_analysis,
            "pattern_detected": "",
            "fix_recommendation": recommendation,
            "confidence_adjustment": -0.2,
            "timestamp": now,
        }

        # Check for recurring patterns
        pattern = _detect_recurring_pattern(repo_path, failure_type)
        if pattern:
            signal["pattern_detected"] = pattern

        signals.append(signal)

        # Write signal to evolution directory
        signal_path = repo_path / "evolution" / f"{signal['id']}.json"
        signal_path.write_text(json.dumps(signal, indent=2), encoding="utf-8")
    else:
        signals.append({
            "confidence_adjustment": 0.1,
            "decision_id": decision_id,
        })

    # Save outcome
    outcome_path = repo_path / "outcomes" / f"{outcome_id}.json"
    outcome_path.write_text(json.dumps(outcome, indent=2), encoding="utf-8")

    # Update linked decision's confidence_weight
    _adjust_decision_confidence(repo_path, decision_id, success)

    # Append to global evolution log
    log = _load_json(EVOLUTION_LOG)
    log.append({
        "outcome_id": outcome_id,
        "repo": repo,
        "success": success,
        "failure_type": signals[0].get("failure_type", "") if not success else "",
        "timestamp": now,
    })
    # Keep log bounded
    log = log[-500:]
    _save_json(EVOLUTION_LOG, log)

    return {
        "outcome": outcome,
        "signals": signals,
        "updated_decision": {"id": decision_id, "adjustment": 0.1 if success else -0.2},
    }


def _classify_failure(error_analysis: str, expected: str, actual: str) -> str:
    """Classify failure type based on error analysis text."""
    text = (error_analysis + " " + expected + " " + actual).lower()

    if any(w in text for w in ["logic", "reasoning", "incorrect calculation", "wrong result"]):
        return "logic_error"
    if any(w in text for w in ["approach", "strategy", "method", "technique", "wrong way"]):
        return "wrong_approach"
    if any(w in text for w in ["missing", "lacked", "didn't know", "no information", "incomplete"]):
        return "incomplete_info"
    if any(w in text for w in ["timeout", "api", "server", "network", "external", "dependency"]):
        return "external_failure"
    if any(w in text for w in ["scope", "expanded", "grew", "too much", "beyond"]):
        return "scope_creep"
    if any(w in text for w in ["misunderstood", "misinterpreted", "wrong requirement", "confused"]):
        return "misunderstanding"

    return "wrong_approach"  # default


def _generate_recommendation(failure_type: str, error_analysis: str) -> str:
    """Generate a fix recommendation based on failure type."""
    recommendations = {
        "logic_error": "Review reasoning chain step by step. Validate intermediate results before proceeding.",
        "wrong_approach": "Consider alternative approaches before committing. Use debate engine for critical decisions.",
        "incomplete_info": "Gather more context before deciding. Check existing memory and ask clarifying questions.",
        "external_failure": "Add error handling for external dependencies. Consider fallback strategies.",
        "scope_creep": "Define clear boundaries upfront. Resist adding features beyond the original ask.",
        "misunderstanding": "Restate requirements back to the user before starting work. Verify assumptions.",
    }
    base = recommendations.get(failure_type, "Review the approach and try again with adjusted strategy.")
    if error_analysis:
        return f"{base} Specific issue: {error_analysis[:100]}"
    return base


def _detect_recurring_pattern(repo_path: Path, failure_type: str) -> str:
    """Check if a failure type has occurred 3+ times — indicates a recurring pattern."""
    outcomes_dir = repo_path / "outcomes"
    if not outcomes_dir.exists():
        return ""

    # Count failures of the same type via evolution signals
    evolution_dir = repo_path / "evolution"
    if not evolution_dir.exists():
        return ""

    count = 0
    for f in evolution_dir.glob("*.json"):
        try:
            signal = json.loads(f.read_text(encoding="utf-8"))
            if signal.get("failure_type") == failure_type:
                count += 1
        except Exception:
            continue

    if count >= 3:
        desc = FAILURE_TYPES.get(failure_type, failure_type)
        return f"Recurring pattern: '{failure_type}' ({desc}) has occurred {count}+ times. Systemic issue likely."
    return ""


def _adjust_decision_confidence(repo_path: Path, decision_id: str, success: bool):
    """Adjust confidence_weight on a linked decision."""
    if not decision_id:
        return

    decision_path = repo_path / "decisions" / f"{decision_id}.json"
    if not decision_path.exists():
        return

    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        weight = decision.get("confidence_weight", 1.0)
        if success:
            weight = min(2.0, weight + 0.1)
        else:
            weight = max(0.1, weight - 0.2)
        decision["confidence_weight"] = weight
        decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_evolution_summary(repo: str) -> dict:
    """Get a summary of evolution signals for a repo."""
    repo_path = MEMORY_ROOT / "repos" / repo
    evolution_dir = repo_path / "evolution"
    outcomes_dir = repo_path / "outcomes"

    signals = []
    if evolution_dir.exists():
        for f in evolution_dir.glob("*.json"):
            try:
                signals.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue

    total_outcomes = 0
    successes = 0
    if outcomes_dir.exists():
        for f in outcomes_dir.glob("*.json"):
            try:
                o = json.loads(f.read_text(encoding="utf-8"))
                total_outcomes += 1
                if o.get("success"):
                    successes += 1
            except Exception:
                continue

    failure_types = {}
    for s in signals:
        ft = s.get("failure_type", "unknown")
        failure_types[ft] = failure_types.get(ft, 0) + 1

    return {
        "total_outcomes": total_outcomes,
        "success_rate": successes / total_outcomes if total_outcomes > 0 else None,
        "total_signals": len(signals),
        "failure_distribution": failure_types,
        "recent_signals": signals[-5:],
    }
