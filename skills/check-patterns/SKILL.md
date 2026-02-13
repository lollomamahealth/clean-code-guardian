---
name: check-patterns
description: Scan the codebase for anti-patterns defined in the plugin's pattern configuration and report findings
argument-hint: "[path]"
user-invocable: true
---

# Check Patterns

Scan the codebase (or a specific path) for anti-patterns defined in `reference/patterns.json` and report all findings.

## Instructions

1. **Load patterns** from `reference/patterns.json` in this plugin directory. Each pattern has an `id`, `pattern` (regex), `message`, `suggestion`, `file_globs`, `severity`, and `tags`.

2. **Determine scan scope**:
   - If a path argument was provided ($ARGUMENTS), scan only that path.
   - Otherwise, scan the entire project working directory.

3. **For each pattern**, use Grep to search for matches in files that match the pattern's `file_globs`:
   - Report the file, line number, matched text, and the pattern's `message` and `suggestion`.
   - Respect the `severity` level (error vs warning).

4. **Report findings** in a summary table:

```markdown
## Anti-Pattern Scan Results

### Errors
| File | Line | Pattern | Message | Suggestion |
|------|------|---------|---------|------------|
| ... | ... | ... | ... | ... |

### Warnings
| File | Line | Pattern | Message | Suggestion |
|------|------|---------|---------|------------|
| ... | ... | ... | ... | ... |

### Summary
- **X** errors found
- **Y** warnings found
- **Z** files scanned
```

5. If no violations are found, report a clean result.

## Notes

- Patterns are fully configurable in `reference/patterns.json` - users can add patterns for any language.
- Use the `tags` field to group related patterns in the report if many results are found.
- Do not modify any files - this is a read-only scan.
