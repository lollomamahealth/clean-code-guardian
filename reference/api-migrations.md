# API Migrations Guide

Legacy patterns that should be replaced with modern equivalents.

---

## Pydantic v1 → v2

| Legacy (Block) | Modern (Require) | Notes |
|----------------|------------------|-------|
| `.dict()` | `.model_dump()` | Method renamed |
| `.parse_obj(data)` | `.model_validate(data)` | Method renamed |
| `.parse_raw(json_str)` | `.model_validate_json(json_str)` | Method renamed |
| `default=[]` | `Field(default_factory=list)` | Mutable defaults |
| `default={}` | `Field(default_factory=dict)` | Mutable defaults |
| `class Config:` | `model_config = ConfigDict(...)` | Config style |
| `@validator` | `@field_validator` | Decorator renamed |
| `@root_validator` | `@model_validator` | Decorator renamed |
| `__fields__` | `model_fields` | Attribute renamed |

### Examples

```python
# BLOCK: Pydantic v1
class MyModel(BaseModel):
    items: list[str] = []

    class Config:
        extra = "forbid"

    @validator("items")
    def validate_items(cls, v):
        return v

data = model.dict()

# REQUIRE: Pydantic v2
from pydantic import BaseModel, Field, ConfigDict, field_validator

class MyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[str] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        return v

data = model.model_dump()
```

---

## Sync → Async I/O

| Legacy (Block) | Modern (Require) |
|----------------|------------------|
| `def get_data():` | `async def get_data():` |
| `db.fetch()` | `await db.fetch()` |
| `requests.get()` | `await httpx.AsyncClient().get()` |
| `open(file)` | `aiofiles.open(file)` |
| `time.sleep()` | `await asyncio.sleep()` |

### Examples

```python
# BLOCK: Sync I/O
def get_patient(patient_id: str) -> PatientProfile:
    return db.fetch_one(f"SELECT * FROM patients WHERE id = {patient_id}")

# REQUIRE: Async I/O
async def get_patient(patient_id: str) -> PatientProfile:
    async with db.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM patients WHERE id = $1",
            patient_id
        )
```

---

## SQL Safety

| Legacy (Block) | Modern (Require) |
|----------------|------------------|
| `f"SELECT * FROM t WHERE x='{value}'"` | `"SELECT * FROM t WHERE x=$1", value` |
| `f"INSERT INTO t VALUES ('{v}')"` | `"INSERT INTO t VALUES ($1)", v` |
| `query.format(value)` | Parameterized query |
| `"...WHERE x IN (" + ",".join(ids) + ")"` | `"...WHERE x = ANY($1)", ids` |

### Examples

```python
# BLOCK: SQL injection risk
async def search(term: str):
    return await conn.fetch(f"SELECT * FROM items WHERE name LIKE '%{term}%'")

# REQUIRE: Parameterized
async def search(term: str):
    return await conn.fetch(
        "SELECT * FROM items WHERE name LIKE $1",
        f"%{term}%"
    )
```

---

## JSONB Queries (PostgreSQL)

| Pattern | Operator | Example |
|---------|----------|---------|
| Get key as JSON | `->` | `data->'config'` |
| Get key as text | `->>` | `data->>'name'` |
| Contains | `@>` | `data @> '{"status": "active"}'` |
| Contained by | `<@` | `'{"a":1}' <@ data` |
| Has key | `?` | `data ? 'email'` |

```python
# BLOCK: Using IN for JSONB
"SELECT * FROM t WHERE data->>'type' IN ('a', 'b')"

# REQUIRE: Use @> or ANY
"SELECT * FROM t WHERE data->>'type' = ANY($1)"
```

---

## Datetime Handling

| Legacy (Block) | Modern (Require) |
|----------------|------------------|
| `datetime.now()` | `datetime.now(UTC)` or `datetime.utcnow()` |
| `datetime(2024, 1, 1)` | `datetime(2024, 1, 1, tzinfo=UTC)` |
| Naive datetimes | Always use UTC-aware |

```python
from datetime import datetime, UTC

# BLOCK
created = datetime.now()  # Naive, uses local timezone

# REQUIRE
created = datetime.now(UTC)  # UTC-aware
```

---

## Conditional Imports

```python
# BLOCK: Wrong conditional import pattern
try:
    import optional_dep
except ImportError:
    optional_dep = None

if optional_dep:
    # Use it

# REQUIRE: TYPE_CHECKING pattern
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import optional_dep

def func():
    import optional_dep  # Import at use site
```

---

## Error Handling

```python
# BLOCK: Bare except
try:
    risky_operation()
except:
    pass

# REQUIRE: Specific exceptions
try:
    risky_operation()
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
except asyncpg.PostgresError as e:
    logger.error(f"Database error: {e}")
    raise
```
