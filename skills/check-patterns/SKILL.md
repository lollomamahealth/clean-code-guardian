# /check-patterns

Scan the codebase for anti-patterns and update memory files.

## Description

This skill performs a comprehensive scan of the codebase to:
1. Find existing utilities and index them in `reusable-code.md`
2. Detect anti-patterns that should be fixed
3. Validate test patterns against conventions
4. Update memory files with findings

## Usage

```
/check-patterns [path]
```

- `path` (optional): Specific directory or file to check. Defaults to entire project.

## What It Does

### 1. Code Reuse Scan

Searches for utilities that should be indexed:

```bash
# Find utility functions
rg "def (get|create|update|delete|process|validate|parse|format|build)_\w+" --type py

# Find async utilities
rg "async def \w+" src/*/utils/ --type py

# Find helper classes
rg "class \w+(Helper|Utility|Manager|Factory)" --type py
```

Updates `memory/reusable-code.md` with findings.

### 2. Anti-Pattern Detection

Scans for patterns that violate project conventions:

| Pattern | Issue |
|---------|-------|
| `.dict()` | Pydantic v1 (use .model_dump()) |
| `default=[]` | Mutable default (use Field(default_factory=list)) |
| `f"SELECT...{var}"` | SQL injection risk |
| `datetime.now()` | Naive datetime (use UTC) |
| `except:` | Bare except clause |

Reports files and line numbers to fix.

### 3. Test Validation

Checks test files for:
- Missing `@pytest.mark.asyncio` decorators
- Raw `MagicMock` instead of fixtures
- Vague test names
- Missing assertions

### 4. Fixture Discovery

Scans `tests/conftest.py` and `tests/fixtures/` to update available fixtures list.

## Output

```markdown
## Check Patterns Report

### Utilities Found
- `validate_email` in `src/utils/validators.py:23`
- `async_retry` in `src/utils/retry.py:45`

### Anti-Patterns Detected
| File | Line | Pattern | Fix |
|------|------|---------|-----|
| src/models/user.py | 15 | .dict() | .model_dump() |
| src/db/queries.py | 42 | f-string SQL | Parameterize |

### Test Issues
- tests/test_api.py:30 - Missing @pytest.mark.asyncio

### Memory Updated
- reusable-code.md: +5 utilities
- test-patterns.md: +2 fixtures
```

## Implementation

When `/check-patterns` is invoked:

1. **Launch code-reuse-detector** subagent to find utilities
2. **Run pattern matching** for anti-patterns (using pre_edit_validator patterns)
3. **Launch test-validator** subagent to check tests
4. **Update memory files** with findings
5. **Report summary** to user

## Examples

### Full Project Scan
```
/check-patterns
```

### Scan Specific Directory
```
/check-patterns src/quantitative_agent/
```

### Scan Test Files Only
```
/check-patterns tests/
```

## Automated Triggers

Consider running `/check-patterns` when:
- Starting work on a new feature
- After merging changes from main
- Before creating a PR
- Weekly as part of code hygiene

## Related

- `memory/reusable-code.md` - Utility index
- `memory/api-migrations.md` - Pattern migrations
- `memory/test-patterns.md` - Test conventions
- `agents/code-reuse-detector.md` - Utility finder
- `agents/test-validator.md` - Test checker
