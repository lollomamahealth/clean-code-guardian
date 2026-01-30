---
description: Scan the codebase for anti-patterns and update memory files
---

# Check Patterns

Perform a comprehensive scan of the codebase to:
1. Find existing utilities and index them in `reusable-code.md`
2. Detect anti-patterns that should be fixed
3. Validate test patterns against conventions
4. Update memory files with findings

## What to Do

### 1. Code Reuse Scan

Search for utilities that should be indexed:

```bash
# Find utility functions
rg "def (get|create|update|delete|process|validate|parse|format|build)_\w+" --type py

# Find async utilities
rg "async def \w+" src/*/utils/ --type py

# Find helper classes
rg "class \w+(Helper|Utility|Manager|Factory)" --type py
```

### 2. Anti-Pattern Detection

Scan for patterns that violate project conventions:

| Pattern | Issue | Fix |
|---------|-------|-----|
| `.dict()` | Pydantic v1 | `.model_dump()` |
| `default=[]` | Mutable default | `Field(default_factory=list)` |
| `f"SELECT...{var}"` | SQL injection | Parameterized query |
| `datetime.now()` | Naive datetime | `datetime.now(UTC)` |
| `except:` | Bare except | Specific exception |

Use grep to find these:
```bash
rg "\.dict\(\)" --type py
rg "default=\[\]" --type py
rg 'f"SELECT.*\{' --type py
```

### 3. Test Validation

Check test files for:
- Missing `@pytest.mark.asyncio` decorators on async tests
- Raw `MagicMock` instead of fixtures from conftest.py
- Vague test names (should be `test_<func>_<scenario>_<outcome>`)

### 4. Report Findings

Output a summary like:

```markdown
## Check Patterns Report

### Anti-Patterns Found
| File | Line | Pattern | Fix |
|------|------|---------|-----|

### Utilities Discovered
- `function_name` in `path/to/file.py`

### Test Issues
- file.py:line - issue description
```

If path argument provided ($ARGUMENTS), scan only that path. Otherwise scan the entire project.
