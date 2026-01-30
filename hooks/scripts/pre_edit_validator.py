#!/usr/bin/env python3
"""
Pre-edit validator hook for Clean Code Guardian.

Blocks anti-patterns before they're written to files.
Called by Claude Code's PreToolUse hook for Edit and Write tools.

Input: JSON on stdin with tool_input containing file_path and content/new_string
Output: JSON with decision (allow/block) and reason
"""

import json
import re
import sys
from typing import NamedTuple


class ValidationResult(NamedTuple):
    """Result of a validation check."""
    blocked: bool
    reason: str
    pattern_name: str
    suggestion: str


# Anti-patterns to block
ANTI_PATTERNS = [
    # Pydantic v1 patterns
    {
        "name": "pydantic_dict",
        "pattern": r"\.dict\(\)",
        "message": "Use .model_dump() instead of .dict() (Pydantic v2)",
        "suggestion": ".model_dump()",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_parse_obj",
        "pattern": r"\.parse_obj\(",
        "message": "Use .model_validate() instead of .parse_obj() (Pydantic v2)",
        "suggestion": ".model_validate(",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_parse_raw",
        "pattern": r"\.parse_raw\(",
        "message": "Use .model_validate_json() instead of .parse_raw() (Pydantic v2)",
        "suggestion": ".model_validate_json(",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_mutable_default_list",
        "pattern": r":\s*list\[.*\]\s*=\s*\[\]",
        "message": "Use Field(default_factory=list) for mutable defaults",
        "suggestion": ": list[...] = Field(default_factory=list)",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_mutable_default_dict",
        "pattern": r":\s*dict\[.*\]\s*=\s*\{\}",
        "message": "Use Field(default_factory=dict) for mutable defaults",
        "suggestion": ": dict[...] = Field(default_factory=dict)",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_old_config",
        "pattern": r"class Config:\s*\n\s+\w+\s*=",
        "message": "Use model_config = ConfigDict(...) instead of class Config (Pydantic v2)",
        "suggestion": "model_config = ConfigDict(...)",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_old_validator",
        "pattern": r"@validator\(",
        "message": "Use @field_validator instead of @validator (Pydantic v2)",
        "suggestion": "@field_validator(",
        "file_types": [".py"],
    },
    {
        "name": "pydantic_old_root_validator",
        "pattern": r"@root_validator",
        "message": "Use @model_validator instead of @root_validator (Pydantic v2)",
        "suggestion": "@model_validator",
        "file_types": [".py"],
    },
    # SQL injection patterns
    {
        "name": "sql_fstring_select",
        "pattern": r'f["\']SELECT\s+.*\{.*\}',
        "message": "SQL injection risk: Use parameterized queries ($1, $2) instead of f-strings",
        "suggestion": 'await conn.fetch("SELECT ... WHERE col = $1", value)',
        "file_types": [".py"],
    },
    {
        "name": "sql_fstring_insert",
        "pattern": r'f["\']INSERT\s+.*\{.*\}',
        "message": "SQL injection risk: Use parameterized queries ($1, $2) instead of f-strings",
        "suggestion": 'await conn.execute("INSERT INTO ... VALUES ($1)", value)',
        "file_types": [".py"],
    },
    {
        "name": "sql_fstring_update",
        "pattern": r'f["\']UPDATE\s+.*\{.*\}',
        "message": "SQL injection risk: Use parameterized queries ($1, $2) instead of f-strings",
        "suggestion": 'await conn.execute("UPDATE ... SET col = $1", value)',
        "file_types": [".py"],
    },
    {
        "name": "sql_fstring_delete",
        "pattern": r'f["\']DELETE\s+.*\{.*\}',
        "message": "SQL injection risk: Use parameterized queries ($1, $2) instead of f-strings",
        "suggestion": 'await conn.execute("DELETE FROM ... WHERE col = $1", value)',
        "file_types": [".py"],
    },
    # Datetime patterns
    {
        "name": "naive_datetime_now",
        "pattern": r"datetime\.now\(\)(?!\s*\.\s*replace\(tzinfo)",
        "message": "Use datetime.now(UTC) for timezone-aware datetimes",
        "suggestion": "datetime.now(UTC)",
        "file_types": [".py"],
        # Allow if in string or comment
        "exclude_pattern": r'["\'].*datetime\.now\(\)|#.*datetime\.now\(\)',
    },
    # Bare except
    {
        "name": "bare_except",
        "pattern": r"except\s*:",
        "message": "Avoid bare except: - catch specific exceptions",
        "suggestion": "except ValueError as e:",
        "file_types": [".py"],
    },
    # Wrong conditional import pattern (not TYPE_CHECKING)
    {
        "name": "wrong_conditional_import",
        "pattern": r"try:\s*\n\s+import\s+\w+\s*\nexcept\s+ImportError",
        "message": "Use TYPE_CHECKING pattern for conditional imports",
        "suggestion": "if TYPE_CHECKING:\n    import module",
        "file_types": [".py"],
    },
]


def get_content(tool_input: dict) -> str:
    """Extract content to validate from tool input."""
    # For Edit tool
    if "new_string" in tool_input:
        return tool_input["new_string"]
    # For Write tool
    if "content" in tool_input:
        return tool_input["content"]
    return ""


def get_file_path(tool_input: dict) -> str:
    """Extract file path from tool input."""
    return tool_input.get("file_path", "")


def check_pattern(content: str, pattern_def: dict) -> ValidationResult | None:
    """Check if content matches an anti-pattern."""
    pattern = pattern_def["pattern"]

    # Check for exclusion pattern first
    if "exclude_pattern" in pattern_def:
        exclude_matches = re.findall(pattern_def["exclude_pattern"], content, re.IGNORECASE)
        matches = re.findall(pattern, content, re.IGNORECASE)
        # If all matches are excluded, skip
        if len(exclude_matches) >= len(matches):
            return None

    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
        return ValidationResult(
            blocked=True,
            reason=pattern_def["message"],
            pattern_name=pattern_def["name"],
            suggestion=pattern_def["suggestion"],
        )
    return None


def validate_content(content: str, file_path: str) -> list[ValidationResult]:
    """Validate content against all anti-patterns."""
    results = []

    # Determine file type
    file_ext = "." + file_path.split(".")[-1] if "." in file_path else ""

    for pattern_def in ANTI_PATTERNS:
        # Skip if file type doesn't match
        if file_ext and file_ext not in pattern_def.get("file_types", []):
            continue

        result = check_pattern(content, pattern_def)
        if result:
            results.append(result)

    return results


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only validate Edit and Write tools
        if tool_name not in ("Edit", "Write"):
            print(json.dumps({"decision": "allow"}))
            return

        content = get_content(tool_input)
        file_path = get_file_path(tool_input)

        if not content:
            print(json.dumps({"decision": "allow"}))
            return

        # Validate
        violations = validate_content(content, file_path)

        if violations:
            # Block with detailed message
            messages = []
            for v in violations:
                messages.append(f"[{v.pattern_name}] {v.reason}\n  Suggestion: {v.suggestion}")

            result = {
                "decision": "block",
                "reason": "Anti-pattern detected:\n" + "\n\n".join(messages),
            }
        else:
            result = {"decision": "allow"}

        print(json.dumps(result))

    except json.JSONDecodeError:
        # If we can't parse input, allow the operation
        print(json.dumps({"decision": "allow"}))
    except Exception as e:
        # Log error but allow operation to not block workflow
        print(json.dumps({
            "decision": "allow",
            "warning": f"Validator error: {e}"
        }))


if __name__ == "__main__":
    main()
