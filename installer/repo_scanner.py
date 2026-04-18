"""Scan a single repo to profile its stack and pick the right CLAUDE.md block variant.

Used by `install.py --inject-here` to choose between the full runtime block
and a minimal variant based on how heavy the repo is.
"""

import os
from collections import Counter
from pathlib import Path


# Extension → language. Ordered by informativeness — first match wins.
_LANG_EXTENSIONS = {
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".md": "markdown",
}

_EXCLUDED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".tmp",
    "vendor", "dist", "build", ".next", ".nuxt", "target", ".pytest_cache",
    ".mypy_cache", ".tox", "out", "coverage",
}

# Directory or file basename substrings that strongly indicate tests.
_TEST_SIGNALS = ("tests", "test", "__tests__", "spec", "specs", "e2e")


def scan_repo(repo_path: Path) -> dict:
    """Profile a repo in a single pass. Bounded: stops after 2000 files."""
    repo_path = Path(repo_path).resolve()
    lang_counts: Counter = Counter()
    file_count = 0
    has_tests = False
    scanned = 0
    MAX_FILES = 2000

    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS and not d.startswith(".")]

        # Test-directory signal: any dir at any depth whose basename matches
        for d in dirnames:
            if d.lower() in _TEST_SIGNALS:
                has_tests = True

        for f in filenames:
            scanned += 1
            if scanned > MAX_FILES:
                break
            ext = Path(f).suffix.lower()
            if ext in _LANG_EXTENSIONS:
                file_count += 1
                lang_counts[_LANG_EXTENSIONS[ext]] += 1
                if any(sig in f.lower() for sig in _TEST_SIGNALS):
                    has_tests = True

        if scanned > MAX_FILES:
            break

    # Exclude markdown from primary-language pick — a docs repo shouldn't look like "markdown stack"
    primary = "unknown"
    for lang, _count in lang_counts.most_common():
        if lang != "markdown":
            primary = lang
            break
    if primary == "unknown" and lang_counts:
        primary = lang_counts.most_common(1)[0][0]

    if file_count < 50:
        size_bucket = "small"
    elif file_count < 500:
        size_bucket = "medium"
    else:
        size_bucket = "large"

    return {
        "path": str(repo_path),
        "primary_language": primary,
        "file_count": file_count,
        "size_bucket": size_bucket,
        "has_tests": has_tests,
        "language_distribution": dict(lang_counts),
        "truncated": scanned > MAX_FILES,
    }


def choose_block_variant(scan: dict) -> str:
    """Pick 'minimal' for small, light-weight repos; 'full' otherwise.

    Rationale: a tiny scratch repo gets the terse block; a real project
    benefits from the full Prompt Architect + runtime guidance.
    """
    if scan.get("size_bucket") == "small" and not scan.get("has_tests"):
        return "minimal"
    return "full"
