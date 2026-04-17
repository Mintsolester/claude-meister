"""Detect current repository name and ensure memory directories exist."""

import os
import re
import configparser
from pathlib import Path

MEMORY_ROOT = Path.home() / ".claude_memory"
REPOS_DIR = MEMORY_ROOT / "repos"

REPO_SUBDIRS = ["sessions", "decisions", "patterns", "structure", "outcomes", "evolution"]


def detect_repo_name(working_dir: str = None) -> str:
    """Extract repo name from .git/config remote URL, fallback to directory name."""
    if working_dir is None:
        working_dir = os.getcwd()

    git_config = os.path.join(working_dir, ".git", "config")
    if os.path.exists(git_config):
        try:
            config = configparser.ConfigParser()
            config.read(git_config)
            for section in config.sections():
                if section.startswith('remote "'):
                    url = config.get(section, "url", fallback="")
                    if url:
                        name = _extract_name_from_url(url)
                        if name:
                            return name
        except Exception:
            pass

    return os.path.basename(os.path.abspath(working_dir))


def _extract_name_from_url(url: str) -> str:
    """Extract repo name from git remote URL."""
    # SSH: git@github.com:user/repo.git
    match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if match:
        return match.group(1).replace("/", "_")
    # HTTPS: https://github.com/user/repo.git
    match = re.search(r"//[^/]+/(.+?)(?:\.git)?$", url)
    if match:
        return match.group(1).replace("/", "_")
    return ""


def ensure_repo_dirs(repo_name: str) -> Path:
    """Create repo memory directories if they don't exist. Returns repo path."""
    repo_path = REPOS_DIR / repo_name
    for subdir in REPO_SUBDIRS:
        (repo_path / subdir).mkdir(parents=True, exist_ok=True)
    return repo_path


def ensure_local_memory(working_dir: str = None) -> Path:
    """Create .repo_memory/ in the working directory if it doesn't exist."""
    if working_dir is None:
        working_dir = os.getcwd()
    local_path = Path(working_dir) / ".repo_memory"
    local_path.mkdir(exist_ok=True)

    hot_md = local_path / "hot.md"
    if not hot_md.exists():
        hot_md.write_text("# Active Context\n\nNo active context yet.\n", encoding="utf-8")

    recent = local_path / "recent_sessions.json"
    if not recent.exists():
        recent.write_text("[]", encoding="utf-8")

    local_index = local_path / "local_index.json"
    if not local_index.exists():
        local_index.write_text("[]", encoding="utf-8")

    return local_path
