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

Gather project-specific rules (**in priority order**):

1. **`CLAUDE.md`** — project-specific coding conventions, patterns, and rules. Highest priority.
2. **Project-local skills** — scan for `.claude/skills/**/*.md` in the target project. These may define architectural patterns, naming conventions, or workflow rules that the code should follow. **Do not** read the analyzer plugin's own skill files — only the target project's skills.

Read all found files. Extract any conventions, patterns, or constraints that are relevant to code review (e.g., "services should not import from controllers", "use DTOs for API responses", naming rules, error handling patterns).

**Priority**: `CLAUDE.md` > project skill conventions > general best practices.

If none of these exist, use general TypeScript/JavaScript best practices.

## Step 1.5: Use Biome MCP (if available)

If Biome MCP is available, use it to get structured lint diagnostics:

1. Call Biome MCP `lint` on changed files
2. Get structured errors with exact locations and rule IDs
3. Include Biome violations in the review (respect project's `biome.json`)

This is more accurate than manual style checking — Biome's rules take priority.

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

### Style (defer to CLAUDE.md rules)

- Naming conventions (consistency within the project)
- `const` vs `let` — prefer `const` unless reassignment is necessary
- Always prefer destructuring
- Early returns over deep nesting (invert conditions, return early)
- Braces on all control flow statements — never single-line `if (!x) return`
- No type assertions (`as`, `!`) without justification
- No `any` types without justification
- Import ordering — follow Biome rules (see `biome.json`)
- Avoid optionality/nullability unless necessary
- Avoid empty strings as sentinel values
- Avoid unnecessary aliases (`password` → `pwd` is forbidden)
- Use `camelCase` for constants, not `CAPITAL_CASE`
- Avoid one-letter variable names except loop indexes (`i`, `j`, `k`)
- Respect ESLint, tsconfig, and Biome settings in the project

### React/NextJS

- Never report "Missing React import" — not needed in modern React
- Wrap callbacks in `useCallback`, computed objects in `useMemo`
- Do not memoize simple values (strings, numbers, booleans)
- Mark components with `React.FC`: `const MyComponent: React.FC = () => ...`
- Use explicit strings in JSX: `<>{'text'}</>` not `<>text</>`
- Export directly: `export const X = () => ...` not `const X = ...; export { X }`
- Avoid extra `<div>`s — use fragments `<>...</>` when possible
- Put loaders in parent components instead of passing `isLoading` props
- Extract all components from page files to separate files

### NestJS

- Never add exports/imports to modules unless necessary
- Use typed EntityId (`UserId`, `VesselId`) instead of plain strings

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
