#!/usr/bin/env python3
"""
Post-tool learner hook for Clean Code Guardian.

Detects failures from tool execution and queues them for analysis.
Called by Claude Code's PostToolUse hook for Bash tool.

Input: JSON on stdin with tool output
Output: JSON acknowledgment, may trigger mistake-analyzer subagent
"""

import json
import os
import re
import sys
from datetime import datetime, UTC
from pathlib import Path


# Failure patterns to detect
FAILURE_PATTERNS = [
    {
        "name": "pytest_failure",
        "pattern": r"FAILED|ERROR|(?:\d+) failed",
        "category": "TEST",
        "extract_pattern": r"(FAILED.*?(?=FAILED|$)|ERROR.*?(?=ERROR|$))",
    },
    {
        "name": "import_error",
        "pattern": r"ImportError|ModuleNotFoundError",
        "category": "RUNTIME",
        "extract_pattern": r"((?:ImportError|ModuleNotFoundError).*?)(?:\n\n|\Z)",
    },
    {
        "name": "type_error",
        "pattern": r"TypeError:",
        "category": "RUNTIME",
        "extract_pattern": r"(TypeError:.*?)(?:\n\n|\Z)",
    },
    {
        "name": "attribute_error",
        "pattern": r"AttributeError:",
        "category": "RUNTIME",
        "extract_pattern": r"(AttributeError:.*?)(?:\n\n|\Z)",
    },
    {
        "name": "validation_error",
        "pattern": r"ValidationError|pydantic.*error",
        "category": "PATTERN",
        "extract_pattern": r"(ValidationError.*?)(?:\n\n|\Z)",
    },
    {
        "name": "syntax_error",
        "pattern": r"SyntaxError:",
        "category": "LOGIC",
        "extract_pattern": r"(SyntaxError:.*?)(?:\n\n|\Z)",
    },
    {
        "name": "sql_error",
        "pattern": r"asyncpg.*Error|PostgresError|SQL.*error",
        "category": "RUNTIME",
        "extract_pattern": r"((?:asyncpg|Postgres|SQL).*?Error.*?)(?:\n\n|\Z)",
    },
    {
        "name": "assertion_error",
        "pattern": r"AssertionError",
        "category": "TEST",
        "extract_pattern": r"(AssertionError.*?)(?:\n\n|\Z)",
    },
]


def get_plugin_dir() -> Path:
    """Get the plugin directory path."""
    return Path(__file__).parent.parent.parent


def get_queue_file() -> Path:
    """Get the path to the failure queue file."""
    return get_plugin_dir() / "memory" / ".failure_queue.json"


def detect_failures(output: str) -> list[dict]:
    """Detect failures in tool output."""
    failures = []

    for pattern_def in FAILURE_PATTERNS:
        if re.search(pattern_def["pattern"], output, re.IGNORECASE):
            # Extract the relevant error message
            match = re.search(
                pattern_def["extract_pattern"],
                output,
                re.IGNORECASE | re.DOTALL
            )
            error_text = match.group(1).strip() if match else "Error detected"

            # Truncate if too long
            if len(error_text) > 500:
                error_text = error_text[:500] + "..."

            failures.append({
                "name": pattern_def["name"],
                "category": pattern_def["category"],
                "error": error_text,
                "timestamp": datetime.now(UTC).isoformat(),
            })

    return failures


def queue_for_analysis(failures: list[dict], command: str):
    """Queue failures for analysis by mistake-analyzer subagent."""
    queue_file = get_queue_file()

    # Load existing queue
    queue = []
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text())
        except json.JSONDecodeError:
            queue = []

    # Add new failures
    for failure in failures:
        failure["command"] = command[:200]  # Truncate command
        queue.append(failure)

    # Keep only last 50 failures
    queue = queue[-50:]

    # Save queue
    queue_file.write_text(json.dumps(queue, indent=2))


def should_trigger_analyzer(failures: list[dict]) -> bool:
    """Determine if we should trigger the mistake-analyzer subagent."""
    # Trigger if we have test failures or multiple errors
    test_failures = [f for f in failures if f["category"] == "TEST"]
    return len(test_failures) > 0 or len(failures) >= 3


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_output = input_data.get("tool_output", {})
        tool_input = input_data.get("tool_input", {})

        # Only process Bash tool
        if tool_name != "Bash":
            print(json.dumps({"status": "skipped", "reason": "not Bash tool"}))
            return

        # Get output content
        output = ""
        if isinstance(tool_output, dict):
            output = tool_output.get("stdout", "") + tool_output.get("stderr", "")
        elif isinstance(tool_output, str):
            output = tool_output

        if not output:
            print(json.dumps({"status": "skipped", "reason": "no output"}))
            return

        # Detect failures
        command = tool_input.get("command", "")
        failures = detect_failures(output)

        if failures:
            # Queue for analysis
            queue_for_analysis(failures, command)

            result = {
                "status": "failures_detected",
                "count": len(failures),
                "categories": list(set(f["category"] for f in failures)),
                "trigger_analyzer": should_trigger_analyzer(failures),
            }
        else:
            result = {"status": "success", "failures": 0}

        print(json.dumps(result))

    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "reason": "invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))


if __name__ == "__main__":
    main()
