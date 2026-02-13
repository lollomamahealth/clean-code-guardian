# Clean Code Guardian

A Claude Code plugin that blocks anti-patterns before they're written, enriches prompts with project context, and provides codebase scanning skills. Language-agnostic and fully configurable.

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

## How It Works

### Hooks

Three hooks fire automatically during your coding session:

| Hook | Event | Purpose |
|------|-------|---------|
| `pre_edit_validator.py` | PreToolUse (Edit, Write) | Blocks anti-patterns before code is written |
| `exfil_guard.py` | PreToolUse (WebSearch, WebFetch, Bash) | Blocks secret exfiltration via outbound tool calls |
| `prompt_enricher.py` | UserPromptSubmit | Injects relevant project context based on detected intent |

**Pre-edit validation** loads patterns from `reference/patterns.json` and denies Edit/Write tool calls that contain matches. For example, writing `.dict()` in a Python file is blocked with a suggestion to use `.model_dump()`.

**Exfiltration guard** protects against indirect prompt injection attacks that trick the AI into leaking secrets through outbound channels. See the [Security](#security) section below.

**Prompt enrichment** loads intent rules from `reference/intent-rules.json` and appends relevant context from reference files when it detects keywords like "write tests", "pydantic", or "move code" in your prompt.

### Skills

Three user-invocable skills are available:

| Skill | Description |
|-------|-------------|
| `/check-patterns [path]` | Scan the codebase for anti-patterns and report findings |
| `/analyze-mistakes` | Analyze recent errors to identify patterns and suggest preventions |
| `/validate-tests [path]` | Validate test files against project conventions |

## Customization

### Adding Anti-Patterns

Edit `reference/patterns.json` to add, remove, or modify patterns. Each pattern has:

```json
{
  "id": "my-pattern-id",
  "pattern": "regex_here",
  "message": "Human-readable explanation",
  "suggestion": "What to use instead",
  "file_globs": ["*.py", "*.js"],
  "severity": "error",
  "tags": ["category"]
}
```

Patterns work for any language — just set the appropriate `file_globs`.

### Adding Intent Detection Rules

Edit `reference/intent-rules.json` to customize prompt enrichment:

```json
{
  "id": "my-intent",
  "patterns": ["\\bkeyword\\b"],
  "context": "Static context to inject",
  "reference_file": "optional-reference-file.md",
  "reference_section": "Optional Section Name"
}
```

### Reference Files

The `reference/` directory contains project knowledge used by hooks and skills:

| File | Purpose |
|------|---------|
| `patterns.json` | Anti-pattern definitions (used by pre-edit hook and /check-patterns) |
| `exfil-patterns.json` | Secret patterns, suspicious domains, and entropy thresholds (used by exfil guard) |
| `intent-rules.json` | Intent detection rules (used by prompt enricher) |
| `api-migrations.md` | Legacy → modern API mappings |
| `test-patterns.md` | Project-specific test conventions |
| `shared-learnings.md` | Cross-project insights and common pitfalls |

## Structure

```
clean-code-guardian/
├── .claude-plugin/
│   └── plugin.json                # Plugin manifest
├── hooks/
│   └── hooks.json                 # Hook configuration
├── scripts/
│   ├── pre_edit_validator.py      # Blocks anti-patterns on Edit/Write
│   ├── exfil_guard.py             # Blocks secret exfiltration
│   └── prompt_enricher.py         # Enriches prompts with context
├── skills/
│   ├── check-patterns/
│   │   └── SKILL.md              # /check-patterns command
│   ├── analyze-mistakes/
│   │   └── SKILL.md              # /analyze-mistakes command
│   └── validate-tests/
│       └── SKILL.md              # /validate-tests command
└── reference/
    ├── patterns.json              # Configurable anti-pattern definitions
    ├── exfil-patterns.json        # Exfiltration detection config
    ├── intent-rules.json          # Configurable intent detection rules
    ├── api-migrations.md          # API migration guide
    ├── test-patterns.md           # Test conventions
    └── shared-learnings.md        # Cross-project insights
```

## Shipped Patterns

The plugin ships with Python-focused patterns out of the box:

| Pattern | Issue | Suggestion |
|---------|-------|------------|
| `.dict()` | Pydantic v1 | `.model_dump()` |
| `.parse_obj()` | Pydantic v1 | `.model_validate()` |
| `default=[]` | Mutable default | `Field(default_factory=list)` |
| `f"SELECT...{var}"` | SQL injection | Parameterized queries |
| `datetime.now()` | Naive datetime | `datetime.now(UTC)` |
| `except:` | Bare except | Specific exceptions |
| `@validator` | Pydantic v1 | `@field_validator` |

Add your own patterns for any language by editing `reference/patterns.json`.

## Security

### Exfiltration Guard

The `exfil_guard.py` hook defends against **indirect prompt injection** — malicious instructions hidden in fetched web pages, repos, or code comments that trick the AI into leaking secrets through outbound tool calls. It intercepts WebSearch, WebFetch, and Bash calls before execution.

**What it detects:**

| Layer | Description |
|-------|-------------|
| Secret patterns | AWS keys, GitHub tokens, private keys, JWTs, Stripe keys, and more |
| Suspicious domains | Known exfiltration endpoints (webhook.site, requestbin.com, interact.sh, etc.) |
| Entropy analysis | High-entropy tokens that may encode secrets (base64, hex-encoded data) |
| Bash bypass patterns | `sed` with `e` modifier, `git --upload-pack`, `man --html` (command execution bypasses) |

**Design choice — fail-open:** If the config file is missing or the hook encounters an error, it outputs `{}` (allow) rather than blocking. This ensures legitimate work is never interrupted by a broken guard.

### Customizing Detection

Edit `reference/exfil-patterns.json` to:

- **Add secret patterns** — each entry has `id`, `pattern` (regex), and `description`
- **Add suspicious domains** — hostnames that should never appear in outbound requests
- **Add bash exfil commands** — patterns for binaries that can exfiltrate data
- **Tune entropy detection** — adjust `entropy_threshold` (default 4.0 bits/char) and `entropy_min_length` (default 20 chars)

## License

MIT
