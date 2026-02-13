#!/usr/bin/env python3
"""
Pre-edit validator hook for Clean Code Guardian.

Blocks anti-patterns before they're written to files.
Called by Claude Code's PreToolUse hook for Edit and Write tools.

Input: JSON on stdin with tool_name, tool_input
Output: JSON with hookSpecificOutput containing permissionDecision
"""

import fnmatch
import json
import os
import re
import sys
from pathlib import Path


def get_plugin_dir() -> Path:
    """Get the plugin directory path via env var or relative path."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).parent.parent.parent


def load_patterns() -> list[dict]:
    """Load anti-pattern definitions from reference/patterns.json."""
    patterns_file = get_plugin_dir() / "reference" / "patterns.json"
    if not patterns_file.exists():
        return []
    try:
        data = json.loads(patterns_file.read_text())
        return data.get("patterns", [])
    except (json.JSONDecodeError, OSError):
        return []


def get_content(tool_input: dict) -> str:
    """Extract content to validate from tool input."""
    if "new_string" in tool_input:
        return tool_input["new_string"]
    if "content" in tool_input:
        return tool_input["content"]
    return ""


def get_file_path(tool_input: dict) -> str:
    """Extract file path from tool input."""
    return tool_input.get("file_path", "")


def file_matches_globs(file_path: str, globs: list[str]) -> bool:
    """Check if a file path matches any of the given glob patterns."""
    basename = os.path.basename(file_path)
    for glob_pattern in globs:
        if fnmatch.fnmatch(basename, glob_pattern):
            return True
    return False


def check_pattern(content: str, pattern_def: dict) -> dict | None:
    """Check if content matches an anti-pattern. Returns violation info or None."""
    pattern = pattern_def["pattern"]

    # Check for exclusion pattern first
    exclude_pattern = pattern_def.get("exclude_pattern")
    if exclude_pattern:
        exclude_matches = re.findall(exclude_pattern, content, re.IGNORECASE)
        matches = re.findall(pattern, content, re.IGNORECASE)
        if len(exclude_matches) >= len(matches):
            return None

    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
        return {
            "id": pattern_def["id"],
            "message": pattern_def["message"],
            "suggestion": pattern_def.get("suggestion", ""),
            "severity": pattern_def.get("severity", "error"),
        }
    return None


def validate_content(content: str, file_path: str, patterns: list[dict]) -> list[dict]:
    """Validate content against all anti-patterns."""
    violations = []

    for pattern_def in patterns:
        file_globs = pattern_def.get("file_globs", [])
        if file_globs and file_path and not file_matches_globs(file_path, file_globs):
            continue

        result = check_pattern(content, pattern_def)
        if result:
            violations.append(result)

    return violations


def main():
    """Main entry point for the hook."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name not in ("Edit", "Write"):
            print(json.dumps({}))
            return

        content = get_content(tool_input)
        file_path = get_file_path(tool_input)

        if not content:
            print(json.dumps({}))
            return

        patterns = load_patterns()
        if not patterns:
            print(json.dumps({}))
            return

        violations = validate_content(content, file_path, patterns)

        if violations:
            messages = []
            for v in violations:
                messages.append(f"[{v['id']}] {v['message']}")
                if v["suggestion"]:
                    messages.append(f"  Suggestion: {v['suggestion']}")

            reason = "Anti-pattern detected:\n" + "\n".join(messages)

            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }))
        else:
            print(json.dumps({}))

    except json.JSONDecodeError:
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
