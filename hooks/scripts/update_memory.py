#!/usr/bin/env python3
"""
Memory updater hook for Clean Code Guardian.

Persists learnings from the mistake-analyzer subagent to memory files.
Called by Claude Code's SubagentStop hook.

Input: JSON on stdin with subagent output
Output: JSON acknowledgment
"""

import json
import os
import re
import sys
from datetime import datetime, UTC
from pathlib import Path


def get_plugin_dir() -> Path:
    """Get the plugin directory path."""
    return Path(__file__).parent.parent.parent


def get_memory_file(name: str) -> Path:
    """Get path to a memory file."""
    return get_plugin_dir() / "memory" / name


def update_mistakes_log(mistakes: list[dict]):
    """Append mistakes to the mistakes.md log."""
    mistakes_file = get_memory_file("mistakes.md")

    if not mistakes_file.exists():
        return

    content = mistakes_file.read_text()

    # Find the "Recent Mistakes" section
    recent_section = "## Recent Mistakes"
    if recent_section not in content:
        return

    # Build new entries
    new_entries = []
    for mistake in mistakes:
        entry = f"""
### [{mistake.get('category', 'UNKNOWN')}] {mistake.get('title', 'Untitled')}
- **Date**: {datetime.now(UTC).strftime('%Y-%m-%d')}
- **File**: {mistake.get('file', 'unknown')}
- **Error**: {mistake.get('error', 'No error message')}
- **Mistake**: {mistake.get('mistake', 'Unknown')}
- **Correction**: {mistake.get('correction', 'See documentation')}
- **Prevention**: {mistake.get('prevention', 'Add to blocklist')}
"""
        new_entries.append(entry)

    # Insert after "Recent Mistakes" header
    parts = content.split(recent_section)
    if len(parts) == 2:
        # Find where the next section starts
        rest = parts[1]
        next_section_match = re.search(r'\n## ', rest)

        if next_section_match:
            insert_point = next_section_match.start()
            new_content = (
                parts[0] +
                recent_section +
                rest[:insert_point] +
                "\n".join(new_entries) +
                rest[insert_point:]
            )
        else:
            new_content = (
                parts[0] +
                recent_section +
                rest +
                "\n".join(new_entries)
            )

        mistakes_file.write_text(new_content)


def update_statistics(categories: list[str]):
    """Update the statistics section in mistakes.md."""
    mistakes_file = get_memory_file("mistakes.md")

    if not mistakes_file.exists():
        return

    content = mistakes_file.read_text()

    # Update counts in the statistics table
    for category in categories:
        # Find the row for this category
        pattern = rf"\| {category} \| (\d+) \|"
        match = re.search(pattern, content)
        if match:
            current_count = int(match.group(1))
            new_count = current_count + 1
            today = datetime.now(UTC).strftime('%Y-%m-%d')
            content = re.sub(
                pattern,
                f"| {category} | {new_count} |",
                content
            )
            # Also update last occurrence
            content = re.sub(
                rf"\| {category} \| {new_count} \| [^|]+ \|",
                f"| {category} | {new_count} | {today} |",
                content
            )

    mistakes_file.write_text(content)


def update_api_migrations(patterns: list[dict]):
    """Add new patterns to api-migrations.md if discovered."""
    migrations_file = get_memory_file("api-migrations.md")

    if not migrations_file.exists():
        return

    content = migrations_file.read_text()

    # Add to "Last Updated" section
    last_updated_marker = "## Last Updated"
    if last_updated_marker in content:
        new_patterns_text = "\n".join([
            f"- {p.get('legacy', '')} → {p.get('modern', '')}: {p.get('notes', '')}"
            for p in patterns
        ])

        content = content.replace(
            last_updated_marker,
            f"## Newly Discovered Patterns\n\n{new_patterns_text}\n\n{last_updated_marker}"
        )

        migrations_file.write_text(content)


def update_reusable_code(utilities: list[dict]):
    """Add newly discovered utilities to reusable-code.md."""
    reusable_file = get_memory_file("reusable-code.md")

    if not reusable_file.exists():
        return

    content = reusable_file.read_text()

    # Add to "Recently Added" section
    recently_added_marker = "## Recently Added"
    if recently_added_marker in content:
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        new_utilities_text = "\n".join([
            f"- [{today}] `{u.get('name', '')}` in `{u.get('location', '')}` - {u.get('purpose', '')}"
            for u in utilities
        ])

        parts = content.split(recently_added_marker)
        if len(parts) == 2:
            content = (
                parts[0] +
                recently_added_marker +
                f"\n\n{new_utilities_text}" +
                parts[1]
            )

        reusable_file.write_text(content)


def clear_failure_queue():
    """Clear the failure queue after processing."""
    queue_file = get_plugin_dir() / "memory" / ".failure_queue.json"
    if queue_file.exists():
        queue_file.write_text("[]")


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        subagent_name = input_data.get("subagent_name", "")
        subagent_output = input_data.get("output", {})

        # Only process mistake-analyzer output
        if subagent_name != "mistake-analyzer":
            print(json.dumps({"status": "skipped", "reason": "not mistake-analyzer"}))
            return

        # Parse the subagent's structured output
        if isinstance(subagent_output, str):
            try:
                subagent_output = json.loads(subagent_output)
            except json.JSONDecodeError:
                subagent_output = {}

        updates_made = []

        # Update mistakes log
        mistakes = subagent_output.get("mistakes", [])
        if mistakes:
            update_mistakes_log(mistakes)
            updates_made.append(f"mistakes ({len(mistakes)})")

            # Update statistics
            categories = [m.get("category", "UNKNOWN") for m in mistakes]
            update_statistics(categories)

        # Update API migrations
        patterns = subagent_output.get("new_patterns", [])
        if patterns:
            update_api_migrations(patterns)
            updates_made.append(f"api_patterns ({len(patterns)})")

        # Update reusable code
        utilities = subagent_output.get("discovered_utilities", [])
        if utilities:
            update_reusable_code(utilities)
            updates_made.append(f"utilities ({len(utilities)})")

        # Clear the failure queue
        clear_failure_queue()

        result = {
            "status": "success",
            "updates": updates_made,
        }

        print(json.dumps(result))

    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "reason": "invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))


if __name__ == "__main__":
    main()
