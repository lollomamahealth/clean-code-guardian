---
name: validate-tests
description: Validate test files against project conventions defined in reference/test-patterns.md
argument-hint: "[path]"
user-invocable: true
---

# Validate Tests

Check test files against project conventions defined in `reference/test-patterns.md`.

## Instructions

1. **Load conventions** from `reference/test-patterns.md` in this plugin directory.

2. **Determine scan scope**:
   - If a path argument was provided ($ARGUMENTS), validate only that file or directory.
   - Otherwise, scan all test files in the project (files matching `test_*.py` or `*_test.py`).

3. **Check each test file for**:

   - **Missing async decorators**: Async test functions must have `@pytest.mark.asyncio`
   - **Raw mock usage**: Flag `MagicMock()` instantiation that should use fixtures from `conftest.py`
   - **Test naming**: Should follow `test_<function>_<scenario>_<outcome>` convention
   - **Vague assertions**: Flag bare `assert result` without specific comparison
   - **Import style**: Project imports should use absolute paths
   - **Fixture availability**: Suggest available fixtures from conftest when raw mocks are used

4. **Report findings**:

```markdown
## Test Validation Report

### Issues Found

| File | Line | Issue | Severity | Suggestion |
|------|------|-------|----------|------------|
| test_api.py | 12 | Missing @pytest.mark.asyncio | error | Add decorator above async test |
| test_api.py | 15 | Raw MagicMock() | warning | Use mock_db_connection fixture |
| test_api.py | 8 | Vague test name | warning | test_get_user_valid_id_returns_profile |

### Summary
- **X** errors found
- **Y** warnings found
- **Z** test files scanned
- **N** test functions checked
```

5. If all tests pass validation, report a clean result.

## Notes

- Conventions are loaded from `reference/test-patterns.md` - users can customize them.
- This is a static analysis check, not a test runner. It validates style and conventions, not correctness.
- Do not modify test files - report findings for the user to address.
