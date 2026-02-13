---
name: analyze-mistakes
description: Analyze recent errors and failures to identify patterns and suggest preventions
user-invocable: true
---

# Analyze Mistakes

Review recent errors, test failures, and runtime issues to identify recurring patterns and suggest preventions.

## Instructions

1. **Gather recent errors** by reviewing:
   - Recent terminal output and command history in this session
   - Any test failures from recent `pytest` runs
   - Runtime errors from recent command executions
   - Diagnostic output from the IDE if available

2. **Categorize each error** into one of these categories:
   - **PATTERN**: Code anti-pattern issues (deprecated APIs, unsafe patterns)
   - **TEST**: Test-related failures (missing decorators, wrong assertions)
   - **RUNTIME**: Runtime errors (import errors, type errors, attribute errors)
   - **LOGIC**: Logical errors (wrong algorithm, off-by-one, missing edge cases)

3. **For each error, identify**:
   - Root cause
   - The file and approximate location
   - What was wrong
   - How to fix it
   - How to prevent it in future

4. **Report findings**:

```markdown
## Mistake Analysis Report

### Errors Analyzed

| # | Category | Error | File | Root Cause | Fix |
|---|----------|-------|------|------------|-----|
| 1 | PATTERN | .dict() AttributeError | src/model.py | Pydantic v1 syntax | Use .model_dump() |

### Suggested Preventions

- Add pattern `X` to `reference/patterns.json` to block in future
- Update `reference/shared-learnings.md` with lesson learned

### Recommended Pattern Additions

If new anti-patterns were discovered, suggest additions to `reference/patterns.json` in the correct format.
```

5. **Optionally update reference files**:
   - If the user agrees, add newly discovered anti-patterns to `reference/patterns.json`
   - If the user agrees, add lessons to `reference/shared-learnings.md`
   - Always ask before modifying reference files

## Notes

- This skill replaces the old automated failure queue pipeline. It is interactive and on-demand.
- Focus on actionable findings - patterns that can be prevented, not one-off typos.
- When suggesting new patterns for `reference/patterns.json`, provide them in the exact JSON format the file expects.
