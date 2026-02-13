#!/usr/bin/env python3
"""
Prompt enricher hook for Clean Code Guardian.

Detects user intent and injects relevant context from reference files.
Called by Claude Code's UserPromptSubmit hook.

Input: JSON on stdin with session_id, transcript_path, cwd, etc.
       The user's prompt is in the input as "prompt".
Output: JSON with hookSpecificOutput containing additionalContext
"""

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
    return Path(__file__).parent.parent


def load_intent_rules() -> list[dict]:
    """Load intent detection rules from reference/intent-rules.json."""
    rules_file = get_plugin_dir() / "reference" / "intent-rules.json"
    if not rules_file.exists():
        return []
    try:
        data = json.loads(rules_file.read_text())
        return data.get("intents", [])
    except (json.JSONDecodeError, OSError):
        return []


def load_reference_file(filename: str, section_filter: str | None = None) -> str:
    """Load content from a reference file, optionally filtering to a section."""
    ref_path = get_plugin_dir() / "reference" / filename

    if not ref_path.exists():
        return ""

    content = ref_path.read_text()

    if section_filter:
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

    # Return first 100 lines if no filter or section not found
    lines = content.split("\n")[:100]
    return "\n".join(lines)


def detect_intents(prompt: str, rules: list[dict]) -> list[dict]:
    """Detect user intent from prompt text using configurable rules."""
    prompt_lower = prompt.lower()
    matched = []

    for rule in rules:
        for pattern in rule.get("patterns", []):
            if re.search(pattern, prompt_lower):
                matched.append(rule)
                break

    return matched


def build_enrichment(intents: list[dict]) -> str:
    """Build enrichment context from matched intents."""
    sections = []

    for intent in intents:
        parts = []

        context = intent.get("context")
        if context:
            parts.append(context)

        ref_file = intent.get("reference_file")
        if ref_file:
            ref_content = load_reference_file(
                ref_file,
                intent.get("reference_section"),
            )
            if ref_content:
                parts.append(ref_content)

        if parts:
            sections.append("\n\n".join(parts))

    if sections:
        return "\n\n---\n\n".join(sections)
    return ""


def main():
    """Main entry point for the hook."""
    try:
        input_data = json.load(sys.stdin)

        # UserPromptSubmit provides the prompt in "prompt"
        prompt = input_data.get("prompt", "")

        if not prompt:
            print(json.dumps({}))
            return

        rules = load_intent_rules()
        if not rules:
            print(json.dumps({}))
            return

        intents = detect_intents(prompt, rules)

        if not intents:
            print(json.dumps({}))
            return

        enrichment = build_enrichment(intents)

        if enrichment:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"## Project Conventions (clean-code-guardian)\n\n{enrichment}",
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
