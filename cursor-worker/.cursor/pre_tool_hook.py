#!/usr/bin/env python3
"""
Githeri Pre-Tool Hook Sentinel

This script runs as a pre-tool hook for Cursor/Claude Code.
It checks if an agent attempts to edit files in routers/ without an existing spec
in .githeri/specs/, and injects a warning into the agent's turn.

Usage (Cursor):
  Add to .cursorrules or Cursor settings as a pre-tool hook:
  "preToolHook": "python /path/to/pre_tool_hook.py"

Usage (Claude Code):
  Add to settings.json hooks section.
"""

import json
import sys
from pathlib import Path
from typing import Optional


def check_spec_exists_for_router_changes(
    changed_files: list[str], githeri_root: Path
) -> Optional[str]:
    """Check if any changed file is in routers/ and if a spec exists."""
    # Check if any changed file is a router file
    router_files = [f for f in changed_files if "routers/" in f and f.endswith(".py")]
    if not router_files:
        return None

    # Check if .githeri/specs/ has any spec
    specs_dir = githeri_root / ".githeri" / "specs"
    if not specs_dir.is_dir():
        return (
            "⚠️ Githeri Warning: You're editing router files but no contract specs exist.\n"
            'Run `githeri spec "your feature"` first to create a validated YAML spec.\n'
            "This ensures your implementation matches the contract and passes drift verification."
        )

    spec_files = list(specs_dir.glob("*.spec.yaml"))
    if not spec_files:
        return (
            "⚠️ Githeri Warning: You're editing router files but no contract specs exist.\n"
            'Run `githeri spec "your feature"` first to create a validated YAML spec.\n'
            "This ensures your implementation matches the contract and passes drift verification."
        )

    return None


def main():
    try:
        # Read hook input from stdin (JSON with tool name and arguments)
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool", "")
    args = data.get("arguments", {})

    # Only check for file edit/write operations
    if tool_name not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        sys.exit(0)

    file_path = args.get("file_path") or args.get("path") or ""
    if not file_path:
        sys.exit(0)

    # Get project root (where .githeri would be)
    project_root = Path.cwd()
    # Could also look for .githeri directory upwards
    for parent in [project_root] + list(project_root.parents):
        if (parent / ".githeri").is_dir():
            project_root = parent
            break

    # For multi-edit, check all files
    if tool_name == "MultiEdit":
        edits = args.get("edits", [])
        files = [file_path] + [e.get("file_path", "") for e in edits if e.get("file_path")]
    else:
        files = [file_path]

    warning = check_spec_exists_for_router_changes(files, project_root)
    if warning:
        # Output warning to stderr which Cursor/Claude will show to agent
        print(warning, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
