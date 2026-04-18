"""Handle CLAUDE.md creation, appending, updating, and removal."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from installer.paths import apply_substitutions

START_MARKER = "<!-- RUNTIME:START -->"
END_MARKER = "<!-- RUNTIME:END -->"


def setup_claude_md(
    paths: dict,
    substitutions: dict,
    mode: str = "auto",
    target_override: Path | None = None,
    block_variant: str = "full",
) -> dict:
    """Set up CLAUDE.md with the runtime block.

    Args:
        paths: from get_paths()
        substitutions: from build_substitutions()
        mode: 'auto' (detect), 'create' (new file), 'append' (add to existing),
              'update' (replace between markers), 'skip' (do nothing)
        target_override: if set, write to this file instead of ~/.claude/CLAUDE.md
        block_variant: 'full' (default) or 'minimal' — selects which block template to use

    Returns:
        dict with 'status', 'action', 'message'
    """
    claude_dir = Path(paths["claude_dir"])
    if target_override is not None:
        claude_md = Path(target_override)
        claude_dir = claude_md.parent
    else:
        claude_md = claude_dir / "CLAUDE.md"
    repo_root = Path(paths["repo_root"])

    # Load the template block
    block_name = "claude_md_block_minimal.md" if block_variant == "minimal" else "claude_md_block.md"
    block_template = repo_root / "templates" / block_name
    # Fall back to the standard block if the minimal one doesn't exist
    if block_variant == "minimal" and not block_template.exists():
        block_template = repo_root / "templates" / "claude_md_block.md"
    full_template = repo_root / "templates" / "claude_md_full.md"

    if not block_template.exists() and not full_template.exists():
        return {"status": "error", "message": "Template files not found in templates/"}

    if mode == "skip":
        return {"status": "skipped", "action": "skip", "message": "CLAUDE.md modification skipped."}

    # Auto-detect mode
    if mode == "auto":
        if not claude_md.exists():
            mode = "create"
        elif _has_markers(claude_md):
            mode = "update"
        else:
            mode = "append"

    try:
        claude_dir.mkdir(parents=True, exist_ok=True)

        if mode == "create":
            if claude_md.exists():
                _backup(claude_md)
            # Per-repo injections (target_override set) and minimal variants get just the block.
            # The full Prompt Architect template is reserved for the default global CLAUDE.md create.
            use_full = (
                target_override is None
                and block_variant != "minimal"
                and full_template.exists()
            )
            template = full_template if use_full else block_template
            content = template.read_text(encoding="utf-8")
            content = apply_substitutions(content, substitutions)
            claude_md.write_text(content, encoding="utf-8")
            label = "full Prompt Architect + runtime block" if use_full else f"{block_variant} runtime block"
            return {"status": "success", "action": "created",
                    "message": f"Created {claude_md} with {label}"}

        elif mode == "append":
            # Backup first
            _backup(claude_md)
            existing = claude_md.read_text(encoding="utf-8")
            block = block_template.read_text(encoding="utf-8")
            block = apply_substitutions(block, substitutions)
            new_content = existing.rstrip() + "\n\n" + block + "\n"
            claude_md.write_text(new_content, encoding="utf-8")
            return {"status": "success", "action": "appended",
                    "message": f"Appended runtime block to existing {claude_md}"}

        elif mode == "update":
            _backup(claude_md)
            existing = claude_md.read_text(encoding="utf-8")
            block = block_template.read_text(encoding="utf-8")
            block = apply_substitutions(block, substitutions)
            new_content = _replace_between_markers(existing, block)
            claude_md.write_text(new_content, encoding="utf-8")
            return {"status": "success", "action": "updated",
                    "message": f"Updated runtime block in {claude_md}"}

        else:
            return {"status": "error", "message": f"Unknown mode: {mode}"}

    except PermissionError:
        return {"status": "error",
                "message": f"Permission denied writing to {claude_md}. Make it writable and re-run."}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}


def remove_claude_md_block(paths: dict) -> dict:
    """Remove the runtime block from CLAUDE.md, preserving everything else."""
    claude_md = Path(paths["claude_dir"]) / "CLAUDE.md"

    if not claude_md.exists():
        return {"status": "skipped", "message": "CLAUDE.md does not exist."}

    content = claude_md.read_text(encoding="utf-8")
    if START_MARKER not in content:
        return {"status": "skipped", "message": "No runtime block found in CLAUDE.md."}

    _backup(claude_md)

    # Remove everything between markers (inclusive)
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL
    )
    new_content = pattern.sub("", content).strip() + "\n"
    claude_md.write_text(new_content, encoding="utf-8")

    return {"status": "success", "message": "Runtime block removed from CLAUDE.md."}


def check_claude_md(paths: dict) -> dict:
    """Check current state of CLAUDE.md."""
    claude_md = Path(paths["claude_dir"]) / "CLAUDE.md"

    if not claude_md.exists():
        return {"exists": False, "has_markers": False, "line_count": 0}

    content = claude_md.read_text(encoding="utf-8")
    lines = content.splitlines()
    is_symlink = claude_md.is_symlink()
    is_readonly = not os.access(str(claude_md), os.W_OK)

    return {
        "exists": True,
        "has_markers": _has_markers(claude_md),
        "line_count": len(lines),
        "is_symlink": is_symlink,
        "is_readonly": is_readonly,
        "path": str(claude_md),
        "warnings": _get_warnings(lines, is_symlink, is_readonly),
    }


def _has_markers(claude_md: Path) -> bool:
    """Check if CLAUDE.md contains runtime markers."""
    content = claude_md.read_text(encoding="utf-8")
    return START_MARKER in content and END_MARKER in content


def _replace_between_markers(content: str, new_block: str) -> str:
    """Replace content between START and END markers."""
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL
    )
    return pattern.sub(new_block.strip(), content)


def _backup(claude_md: Path):
    """Create a timestamped backup of CLAUDE.md."""
    if claude_md.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = claude_md.parent / f"CLAUDE.md.backup.{timestamp}"
        shutil.copy2(str(claude_md), str(backup))


def _get_warnings(lines: list, is_symlink: bool, is_readonly: bool) -> list:
    """Generate warnings about CLAUDE.md state."""
    warnings = []
    if len(lines) > 500:
        warnings.append(f"CLAUDE.md is {len(lines)} lines. Large files increase context cost.")
    if is_symlink:
        warnings.append("CLAUDE.md is a symlink. Modifications will affect the target file.")
    if is_readonly:
        warnings.append("CLAUDE.md is read-only. Make it writable before running the installer.")
    return warnings
