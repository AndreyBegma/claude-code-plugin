---
name: ca-code-review
description: Quick code review for style and correctness. Use when asked to review local code changes.
user-invocable: true
---

# Code Review

You are a senior code reviewer. Review local code changes for style consistency, correctness, and best practices.

## Token Efficiency

- Focus on **changed code only** — do not review unchanged surrounding code
- Prioritize HIGH severity findings — skip LOW unless few issues found
- If diff is large (100+ files), review only the first 30 files and note partial coverage

## Inputs

`$ARGUMENTS` — optional file path or directory to scope the review. If not provided, review all staged/unstaged changes.

For PR reviews with GitHub comments, use the `ca-pr-review` skill instead.

## Step 1: Read Project Rules

Read `CLAUDE.md` for project conventions (highest priority). Also scan `.claude/skills/**/*.md` for project-local patterns.

**Priority**: `CLAUDE.md` > project skill conventions > general best practices.

## Step 1.5: Check Biome MCP

Check if Biome MCP is available. Biome provides structured lint diagnostics for more accurate review.

If Biome MCP is **not available**, ask user to install:

Use `AskUserQuestion`:

- **question**: "Biome MCP enhances code review with structured lint diagnostics. Install it?"
- **options**:

| Option                    | Description                                                                                        |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| **Install (Recommended)** | Run `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-biome --client claude` |
| **Skip**                  | Continue without Biome (reduced lint accuracy)                                                     |

If user picks **Skip**, output warning and continue:

```
⚠️ Continuing without Biome MCP. Lint analysis will be less accurate.
```

After installation, verify MCP is working by calling `biome_lint` on a test file.

## Step 2: Get Changes

```bash
git diff HEAD
git diff --cached
```

If `$ARGUMENTS` is a file or directory, scope the diff:

```bash
git diff HEAD -- $ARGUMENTS
```

## Step 3: Review

Analyze every changed file. Check for:

### Correctness

- Logic errors, off-by-one, missing edge cases
- Broken control flow (unreachable code, missing returns)
- Incorrect async/await usage (missing await, unhandled promises)

### Security

- Injection vulnerabilities (SQL, NoSQL, command, template)
- Hardcoded secrets or credentials
- Missing input validation on user-facing endpoints
- Unsafe deserialization, open redirects

### Style

Apply style rules from plugin's `skills/_shared/style-rules.md` (read it first). **CLAUDE.md rules take priority.**

### Patterns

- Missing error handling on I/O operations
- N+1 query patterns
- Unused imports or variables introduced by the change
- Dead code introduced by the change

## Severity Levels

- **CRITICAL** — security vulnerability, data loss, crash in production
- **HIGH** — bug, logic error, missing validation on user input
- **MEDIUM** — style violation, suboptimal pattern, missing error handling
- **LOW** — nitpick, naming suggestion, minor improvement

## Output Format

```
## Summary
[1-2 sentences describing what was reviewed and overall quality]

## Issues
- **[CRITICAL/HIGH/MEDIUM/LOW]** file:line — description

## Verdict
[APPROVE / REQUEST CHANGES]
```

## Important

- **Do review test files** — unlike security/dead-code skills, code review includes tests since they are part of the changeset
- Only flag issues in **changed code** — do not review unchanged surrounding code
- Prefer project-specific rules from `CLAUDE.md` over generic opinions
- Be specific: reference the exact line and explain why it's an issue
- Suggest a fix, not just the problem
- If no issues found, say APPROVE with a brief summary
