# Test Patterns

Project-specific testing conventions extracted from CLAUDE.md and observed patterns.

## Required Before Commit

```bash
pytest tests/
```

**100% pass rate required before committing code.**

---

## Test File Structure

```python
"""Tests for [module_name]."""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Import fixtures from conftest
# DO NOT create raw MagicMock instances - use fixtures

@pytest.mark.asyncio
async def test_function_does_something():
    """Test that function does expected behavior."""
    # Arrange
    # Act
    # Assert
```

---

## Required Patterns

### Async Tests

All async tests MUST have the decorator:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Fixtures Over Mocks

```python
# GOOD - Use fixtures from conftest.py
def test_with_fixture(mock_db_connection, sample_patient):
    result = process_patient(sample_patient, mock_db_connection)

# BAD - Raw MagicMock
def test_with_raw_mock():
    mock = MagicMock()  # Don't do this
```

### Database Test Pattern

```python
@pytest.mark.asyncio
async def test_db_operation(test_db_pool):
    async with test_db_pool.acquire() as conn:
        result = await queries.get_something(conn, "id")
        assert result is not None
```

### LLM Mock Pattern

```python
@pytest.mark.asyncio
async def test_llm_extraction(mock_llm_client):
    mock_llm_client.generate_structured.return_value = ExpectedModel(...)

    result = await extractor.extract(mock_llm_client, input_data)

    assert result.value == expected_value
    mock_llm_client.generate_structured.assert_called_once()
```

---

## Common Fixtures (from tests/fixtures/)

| Fixture | Purpose |
|---------|---------|
| `mock_db_connection` | Async database connection mock |
| `test_db_pool` | Actual test database pool |
| `mock_llm_client` | LLM client with AsyncMock |
| `sample_patient` | PatientProfile test data |
| `sample_transcript` | Interview transcript test data |

---

## Test Naming Convention

```
test_<function_name>_<scenario>_<expected_outcome>
```

Examples:
- `test_get_patient_valid_id_returns_profile`
- `test_get_patient_invalid_id_raises_not_found`
- `test_extract_variables_empty_list_returns_empty`

---

## Assertions

```python
# Preferred assertions
assert result == expected
assert result is None
assert len(items) == 3
assert "error" in str(exception.value)

# For approximate values
assert result == pytest.approx(3.14, rel=0.01)

# For exceptions
with pytest.raises(ValueError, match="invalid input"):
    function_that_raises()
```

---

## Effort Cap

**20% effort cap on writing tests** - Focus on:
1. Critical paths
2. Edge cases that have caused bugs
3. Public API functions

---

## Running Tests

```bash
# All tests
pytest tests/

# Specific file
pytest tests/test_extractor.py

# With coverage
pytest tests/ --cov=src/quantitative_agent

# Verbose with output
pytest tests/ -v -s
```
