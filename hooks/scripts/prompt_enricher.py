#!/usr/bin/env python3
"""
Prompt enricher hook for Clean Code Guardian.

Detects user intent and injects relevant context from memory files.
Called by Claude Code's UserPromptSubmit hook.

Input: JSON on stdin with user prompt
Output: JSON with enriched prompt or original if no enrichment needed
"""

import json
import os
import re
import sys
from pathlib import Path


# Intent patterns and their corresponding memory/context injections
INTENT_PATTERNS = [
    {
        "name": "move_code",
        "patterns": [
            r"\bmove\b.*\b(function|class|method|code|file)\b",
            r"\brelocate\b",
            r"\bmove\b.*\bto\b",
        ],
        "context": """
## Clarification: Move vs Modify

When you say "move" code, please clarify:
- **Move only**: Relocate code to new location WITHOUT modifying it
- **Move and refactor**: Relocate and update structure/imports
- **Move and update**: Relocate and change behavior

The code should be moved as-is unless you explicitly want modifications.
""",
    },
    {
        "name": "test_request",
        "patterns": [
            r"\bwrite\s+tests?\b",
            r"\badd\s+tests?\b",
            r"\btest\b.*\bfor\b",
            r"\bunit\s+tests?\b",
            r"\bpytest\b",
        ],
        "memory_file": "test-patterns.md",
        "context_prefix": "## Test Patterns for This Project\n\n",
    },
    {
        "name": "create_function",
        "patterns": [
            r"\bcreate\b.*\b(function|method|utility|helper)\b",
            r"\bwrite\b.*\b(function|method|utility|helper)\b",
            r"\badd\b.*\b(function|method|utility|helper)\b",
            r"\bimplement\b.*\b(function|method)\b",
        ],
        "context": """
## Before Creating New Code

IMPORTANT: Before creating a new utility function:
1. Check if similar functionality already exists in the codebase
2. Search in `src/*/utils/` directories
3. Check `reusable-code.md` memory file for indexed utilities
4. If found, reuse existing code instead of duplicating

Run the code-reuse-detector subagent if uncertain.
""",
        "memory_file": "reusable-code.md",
    },
    {
        "name": "pydantic_model",
        "patterns": [
            r"\bpydantic\b",
            r"\bbasemodel\b",
            r"\bmodel\b.*\bclass\b",
            r"\bdata\s*class\b",
        ],
        "memory_file": "api-migrations.md",
        "context_prefix": "## Pydantic v2 Patterns Required\n\n",
        "section_filter": "Pydantic",
    },
    {
        "name": "database_query",
        "patterns": [
            r"\bsql\b",
            r"\bquery\b.*\bdatabase\b",
            r"\bpostgres\b",
            r"\basyncpg\b",
            r"\bdb\s*\.\b",
        ],
        "memory_file": "api-migrations.md",
        "context_prefix": "## SQL Safety Required\n\n",
        "section_filter": "SQL",
    },
    {
        "name": "async_code",
        "patterns": [
            r"\basync\b",
            r"\bawait\b",
            r"\basyncio\b",
            r"\bcoroutine\b",
        ],
        "memory_file": "api-migrations.md",
        "context_prefix": "## Async Patterns\n\n",
        "section_filter": "Async",
    },
    {
        "name": "fix_error",
        "patterns": [
            r"\bfix\b.*\berror\b",
            r"\bdebug\b",
            r"\bfailing\b",
            r"\bbroken\b",
        ],
        "memory_file": "mistakes.md",
        "context_prefix": "## Previous Mistakes to Avoid\n\n",
    },
]


def get_plugin_dir() -> Path:
    """Get the plugin directory path."""
    # This script is in hooks/scripts/, plugin root is ../..
    return Path(__file__).parent.parent.parent


def load_memory_file(filename: str, section_filter: str | None = None) -> str:
    """Load content from a memory file, optionally filtering to a section."""
    memory_path = get_plugin_dir() / "memory" / filename

    if not memory_path.exists():
        return ""

    content = memory_path.read_text()

    if section_filter:
        # Extract relevant section
        lines = content.split("\n")
        in_section = False
        section_lines = []

        for line in lines:
            if line.startswith("## ") and section_filter.lower() in line.lower():
                in_section = True
                section_lines.append(line)
            elif line.startswith("## ") and in_section:
                break
            elif in_section:
                section_lines.append(line)

        if section_lines:
            return "\n".join(section_lines)

    # Return first 100 lines if no filter
    lines = content.split("\n")[:100]
    return "\n".join(lines)


def detect_intent(prompt: str) -> list[dict]:
    """Detect user intent from prompt text."""
    prompt_lower = prompt.lower()
    matched_intents = []

    for intent in INTENT_PATTERNS:
        for pattern in intent["patterns"]:
            if re.search(pattern, prompt_lower):
                matched_intents.append(intent)
                break  # Only match each intent once

    return matched_intents


def build_enrichment(intents: list[dict]) -> str:
    """Build enrichment context from matched intents."""
    enrichments = []

    for intent in intents:
        parts = []

        # Add static context if present
        if "context" in intent:
            parts.append(intent["context"])

        # Load memory file if specified
        if "memory_file" in intent:
            memory_content = load_memory_file(
                intent["memory_file"],
                intent.get("section_filter")
            )
            if memory_content:
                prefix = intent.get("context_prefix", "")
                parts.append(f"{prefix}{memory_content}")

        if parts:
            enrichments.append("\n".join(parts))

    if enrichments:
        return "\n\n---\n\n".join(enrichments)

    return ""


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        prompt = input_data.get("prompt", "")

        if not prompt:
            print(json.dumps({"prompt": prompt}))
            return

        # Detect intent
        intents = detect_intent(prompt)

        if not intents:
            # No enrichment needed
            print(json.dumps({"prompt": prompt}))
            return

        # Build enrichment
        enrichment = build_enrichment(intents)

        if enrichment:
            # Append context to prompt
            enriched_prompt = f"{prompt}\n\n<context from=clean-code-guardian>\n{enrichment}\n</context>"
            print(json.dumps({"prompt": enriched_prompt}))
        else:
            print(json.dumps({"prompt": prompt}))

    except json.JSONDecodeError:
        # Return original if we can't parse
        print(json.dumps({"prompt": ""}))
    except Exception as e:
        # Log error but don't block
        print(json.dumps({
            "prompt": input_data.get("prompt", "") if 'input_data' in dir() else "",
            "warning": f"Enricher error: {e}"
        }))


if __name__ == "__main__":
    main()
