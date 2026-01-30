# Clean Code Guardian

A Claude Code plugin that enforces clean code practices, prevents common AI coding mistakes, and learns over time through persistent memory files.

## Features

- **Anti-Pattern Blocking**: Prevents deprecated APIs and dangerous patterns before they're written
- **Context Injection**: Automatically enriches prompts with relevant project conventions
- **Failure Learning**: Detects errors and logs them for future prevention
- **Code Reuse Detection**: Finds existing utilities before creating duplicates
- **Test Validation**: Ensures tests follow project conventions

## Installation

### Option 1: CLI Flag

```bash
claude --plugin-dir /path/to/clean-code-guardian
```

### Option 2: Settings File

Add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": ["/path/to/clean-code-guardian"]
}
```

## What It Does

### Pre-Edit Validation

Blocks anti-patterns before code is written:

| Pattern | Issue | Suggestion |
|---------|-------|------------|
| `.dict()` | Pydantic v1 | Use `.model_dump()` |
| `.parse_obj()` | Pydantic v1 | Use `.model_validate()` |
| `default=[]` | Mutable default | Use `Field(default_factory=list)` |
| `f"SELECT...{var}"` | SQL injection | Use parameterized queries |
| `datetime.now()` | Naive datetime | Use `datetime.now(UTC)` |
| `except:` | Bare except | Catch specific exceptions |

### Prompt Enrichment

Automatically injects context based on user intent:

- **"write tests"** → Injects test patterns and available fixtures
- **"move code"** → Clarifies move vs. modify intent
- **"create function"** → Reminds to check for existing utilities
- **"pydantic model"** → Injects Pydantic v2 patterns

### Failure Learning

When errors occur:

1. `post_tool_learner.py` detects failures from command output
2. `mistake-analyzer` subagent categorizes the error
3. `update_memory.py` persists learnings to memory files
4. Future prompts benefit from accumulated knowledge

## Structure

```
clean-code-guardian/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── agents/
│   ├── code-reuse-detector.md   # Finds existing utilities
│   ├── test-validator.md        # Validates test patterns
│   ├── doc-lookup.md            # Version-specific documentation
│   └── mistake-analyzer.md      # Categorizes errors
├── hooks/
│   ├── hooks.json               # Hook configuration
│   └── scripts/
│       ├── pre_edit_validator.py
│       ├── prompt_enricher.py
│       ├── post_tool_learner.py
│       └── update_memory.py
├── skills/
│   └── check-patterns/SKILL.md  # /check-patterns command
└── memory/
    ├── reusable-code.md         # Utility index
    ├── test-patterns.md         # Test conventions
    ├── api-migrations.md        # API migration guide
    ├── mistakes.md              # Error log
    └── shared-learnings.md      # Cross-project insights
```

## Skills

### `/check-patterns`

Scan the codebase for anti-patterns and update memory files:

```
/check-patterns [path]
```

- Indexes existing utilities
- Detects anti-patterns
- Validates test files
- Updates memory files

## Memory Files

The plugin maintains persistent memory across sessions:

| File | Purpose |
|------|---------|
| `reusable-code.md` | Index of project utilities to prevent duplication |
| `test-patterns.md` | Project-specific test conventions |
| `api-migrations.md` | Legacy → modern API mappings |
| `mistakes.md` | Log of errors with corrections |
| `shared-learnings.md` | Cross-project insights |

## Customization

### Adding Patterns

Edit `hooks/scripts/pre_edit_validator.py` to add new anti-patterns:

```python
ANTI_PATTERNS = [
    {
        "name": "my_pattern",
        "pattern": r"regex_here",
        "message": "User-friendly message",
        "suggestion": "What to use instead",
        "file_types": [".py"],
    },
    # ...
]
```

### Adding Intent Detection

Edit `hooks/scripts/prompt_enricher.py` to detect new intents:

```python
INTENT_PATTERNS = [
    {
        "name": "my_intent",
        "patterns": [r"keyword1", r"keyword2"],
        "context": "Context to inject",
        "memory_file": "optional-memory-file.md",
    },
    # ...
]
```

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `prompt_enricher.py` | UserPromptSubmit | Inject context |
| `pre_edit_validator.py` | PreToolUse[Edit,Write] | Block anti-patterns |
| `post_tool_learner.py` | PostToolUse[Bash] | Detect failures |
| `update_memory.py` | SubagentStop[mistake-analyzer] | Persist learnings |

## Subagents

| Agent | Purpose |
|-------|---------|
| `code-reuse-detector` | Search for existing utilities before writing new code |
| `test-validator` | Validate tests against project conventions |
| `doc-lookup` | Fetch version-specific documentation |
| `mistake-analyzer` | Categorize errors and generate memory updates |

## License

MIT
