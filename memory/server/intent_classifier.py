"""Lightweight keyword-based intent classifier for memory retrieval.

Used to tag both queries and entries with one of:
    code | architecture | debug | decision | general

Goal: cheap, deterministic routing — no LLM calls. Misclassifications fall
back to 'general' (which never filters or boosts), so the worst case is
the pre-classifier system.

Ordering matters: check buckets from most-specific to least-specific so
'debug' wins over 'code' on "why is this function failing".
"""

import re

# Each bucket is a set of trigger substrings. Matched with word-boundary
# regex so "bug" doesn't match "debugging" but "debug" does match "debugger".
_BUCKETS = [
    ("debug", [
        "bug", "error", "traceback", "exception", "fail", "failing", "failed",
        "broken", "crash", "crashed", "stack trace", "stacktrace", "regression",
        "hang", "deadlock", "panic", "fatal", "wtf", "fix", "bugfix",
    ]),
    ("architecture", [
        "architecture", "design", "pattern", "structure", "layout", "refactor",
        "system", "module", "boundary", "coupling", "cohesion", "topology",
        "diagram", "component", "layer", "abstraction",
    ]),
    ("decision", [
        "decide", "decision", "choose", "tradeoff", "trade-off", "alternative",
        "rationale", "why did", "picked", "chose", "option", "vs.", " vs ",
        "pros and cons",
    ]),
    ("code", [
        "function", "method", "class", "variable", "implement", "implementation",
        "syntax", "import", "snippet", "api", "endpoint", "signature",
        "parameter", "argument", "return", "loop",
    ]),
]

_INTENTS = ("code", "architecture", "debug", "decision", "general")


def _has_term(text: str, term: str) -> bool:
    """Word-boundary match, case-insensitive. Phrases with spaces match as substrings."""
    if " " in term:
        return term.lower() in text.lower()
    return re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) is not None


def classify_intent(text: str) -> str:
    """Return one of: code | architecture | debug | decision | general.

    Empty or whitespace-only input returns 'general'.
    """
    if not text or not text.strip():
        return "general"

    for intent, terms in _BUCKETS:
        for term in terms:
            if _has_term(text, term):
                return intent
    return "general"


def valid_intents() -> tuple:
    """Public tuple of valid intent values."""
    return _INTENTS
