# Shared Learnings

Cross-project insights and patterns that apply broadly.

---

## General Principles

### 1. Read Before Write
Always read existing code before modifying. Understand:
- Current patterns in use
- Existing utilities that can be reused
- Project-specific conventions

### 2. Move vs Modify
When asked to "move" code:
- **Move** = relocate without modification
- **Refactor** = modify structure
- **Update** = change behavior

Clarify intent before proceeding.

### 3. Test Before Commit
Always run the full test suite before committing:
```bash
pytest tests/
```

### 4. Atomic Commits
Each commit should:
- Do one thing
- Pass all tests
- Have a descriptive message following conventional commits

---

## Language-Specific

### Python

1. **Type hints everywhere** - All function signatures need type hints
2. **Async by default** - Any I/O should be async
3. **Pydantic for data** - Use Pydantic models, not dicts
4. **f-strings for display** - But never for SQL

### SQL

1. **Always parameterize** - Never interpolate user data
2. **Use transactions** - For multi-table operations
3. **Index your queries** - Check EXPLAIN before complex queries

---

## Common Pitfalls

### 1. Mutable Default Arguments
```python
# WRONG
def func(items=[]):
    items.append(1)
    return items

# RIGHT
def func(items=None):
    items = items or []
    items.append(1)
    return items
```

### 2. Not Awaiting Coroutines
```python
# WRONG - Returns coroutine object, not result
result = async_function()

# RIGHT
result = await async_function()
```

### 3. Catching Too Broadly
```python
# WRONG - Hides bugs
except Exception:
    pass

# RIGHT - Specific handling
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
```

---

## Project Conventions Checklist

Before submitting code, verify:
- [ ] Type hints on all functions
- [ ] Docstrings on public functions
- [ ] Async for all I/O
- [ ] Pydantic v2 syntax
- [ ] Parameterized SQL
- [ ] Tests written (20% effort cap)
- [ ] All tests pass

---

## Resources

- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Python Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)

---

## Last Updated

*Updated automatically as patterns are discovered across projects.*
