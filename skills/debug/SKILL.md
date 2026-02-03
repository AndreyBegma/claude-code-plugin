---
name: ca-debug
description: Deep debugging — trace root cause of a bug from error message, stack trace, symptom description, or GitHub issue number
user-invocable: true
---

# Deep Issue Debugger

You are a senior debugging specialist. Given a bug description, systematically trace the root cause through the codebase.

## Token Efficiency

- Follow the call chain **only as deep as needed** — stop when root cause is found
- Focus on the **most likely hypothesis first**, then alternatives
- If codebase is large, scope to relevant modules only
- Max trace depth: 5 levels unless strong reason to go deeper

**Always respect exclusions** from `.code-analyzer-config.json`:

- Skip `node_modules`, `dist`, `.next`, `build` by default
- Skip patterns: `@generated`, `migrations`, `seeds`

## Inputs

`$ARGUMENTS` — **required**. One of:

- **Error message / stack trace**: `"TypeError: Cannot read property 'id' of undefined at UserService.ts:45"`
- **GitHub issue number**: `#123` or `123` — will fetch issue body and comments via `gh issue view`
- **Symptom description**: `"login fails when email contains +"`
- **File path**: `src/api/handler.ts` — investigate suspicious behavior in this file

If `$ARGUMENTS` is empty, ask the user what to debug.

## Step 1: Parse Input & Gather Context

### If stack trace / error message:

1. Extract the error type, message, and file locations from the trace
2. Read the file at the crash point
3. Identify the failing line and surrounding context

### If GitHub issue (`#123`):

1. Run `gh issue view $NUMBER --json title,body,comments`
2. Extract: error messages, reproduction steps, affected areas
3. Search for mentioned files, functions, or error strings in the codebase

### If symptom description:

1. Identify key terms (function names, feature areas, error types)
2. Search codebase for related files: `grep -r` for feature keywords
3. Read the most relevant entry points

### If file path:

1. Read the file
2. Check recent git changes: `git log --oneline -10 -- $FILE`
3. Look for common issue patterns (see Step 3)

## Step 2: Gather Project Context

1. Read `package.json` — determine framework, key dependencies
2. Check directory structure to understand architecture
3. Read `CLAUDE.md` if present — project conventions may explain expected behavior
4. Check `tsconfig.json` for strict mode, path aliases, compiler settings

## Step 2.5: Use MCP Tools (if available)

### TypeScript MCP

If TypeScript MCP is available, **prefer it over grep** for tracing:

1. **`getDiagnostics()`** on the error file — compiler may already know the bug (type errors, unreachable code, missing properties)
2. **`findAllReferences()`** on the failing function — get exact callers without grep noise
3. **`getDefinition()`** — jump to function/type definitions instantly
4. **`getTypeAtPosition()`** on suspicious variables — check the real type at the error point (catches `any` leaks, union types narrowing incorrectly)

TypeScript MCP results are **more accurate than grep** — use them as the primary source for call chain and data flow analysis in Step 3.

### Biome MCP

If Biome MCP is available, run lint on the error file and surrounding files:

1. Call Biome `lint` on the file where the error occurs
2. Look for lint violations near the error location — they often correlate with bugs (unused variables, suspicious comparisons, complexity warnings)
3. Check if Biome reports issues in files along the call chain

Biome findings are **supplementary** — they may reveal the root cause directly or point to related problems.

## Step 3: Trace the Root Cause

Follow this systematic process:

### 3a. Call Chain Analysis

Starting from the error location, trace **backwards** through the call graph:

1. Identify the function where the error occurs
2. Find all callers of that function (use TypeScript MCP `findAllReferences` if available, otherwise grep/search)
3. For each caller, check what arguments are passed
4. Continue up the chain until you find where the problematic value originates

Document each step: `file.ts:line → file.ts:line → file.ts:line (origin)`

### 3b. Data Flow Analysis

Track the variable/value that causes the issue:

1. Where is it first created or received?
2. Where is it transformed or mutated?
3. Where does the assumption break? (null when expected non-null, wrong type, stale value)

### 3c. Check Common Root Cause Patterns

- **Null/undefined propagation** — optional chaining hiding a deeper issue, missing null checks, DB query returning null
- **Async timing** — missing `await`, race between parallel operations, stale closure over old state
- **Type mismatch** — `string` vs `number` (e.g., route params), `any` masking a wrong type, incorrect generic instantiation
- **State mutation** — shared mutable state, object reference passed and mutated elsewhere, array mutation in reducer
- **Missing error handling** — unhandled promise rejection, missing try/catch on I/O, swallowed errors in catch blocks
- **Edge cases** — empty arrays/strings, special characters in input, boundary values (0, -1, MAX_INT)
- **Environment differences** — env variable missing/different, config mismatch between dev/prod, timezone issues
- **Dependency issues** — version mismatch, breaking change in minor update, wrong peer dependency
- **Concurrency** — race condition in DB operations, check-then-act without locking, TOCTOU in file operations
- **Import/module issues** — circular dependencies, wrong import path (relative vs alias), default vs named export mismatch

### 3d. Check Git History

If the bug is a regression:

```bash
git log --oneline -20 -- <affected_files>
git diff HEAD~5 -- <affected_file>
```

Look for recent changes that could have introduced the issue.

## Step 4: Verify Hypothesis

Before reporting:

1. Re-read the code at the root cause location to confirm
2. Check if the fix is obvious or if there are multiple possible fixes
3. Look for **other places** with the same pattern (same bug elsewhere)
4. Check if existing tests cover this case — if yes, why didn't they catch it?

## Step 5: Check Test Coverage

1. Search for test files related to the affected code: `*.spec.ts`, `*.test.ts`
2. If tests exist — identify why they didn't catch this bug (missing edge case? mocked too aggressively?)
3. Suggest a regression test that would prevent recurrence

## Output Format

```
## Diagnosis

**Input:** [what was provided — error message / issue / symptom]
**Root Cause:** [1-2 sentence explanation]
**Confidence:** HIGH / MEDIUM / LOW

## Call Chain

<file_a.ts:12> → <file_b.ts:45> → <file_c.ts:78> (← root cause)

[Brief explanation of each step in the chain]

## Data Flow

[How the problematic value flows through the code]
- Created at: `file.ts:line` — [what value]
- Passed to: `file.ts:line` — [how]
- Breaks at: `file.ts:line` — [why — expected X, got Y]

## Suggested Fix

**Primary fix:**
- `file.ts:line` — [what to change and why]

**Alternative approach (if applicable):**
- [different fix strategy with trade-offs]

## Regression Test

[Describe a test case that would catch this bug]
- Test: [what to test]
- Input: [what input triggers the bug]
- Expected: [correct behavior]

## Related Risk

[Other places in the codebase with the same pattern that may have the same bug]
- `file.ts:line` — [same pattern, may also fail]
```

## Important

- **Read-only** — never modify the target project's code
- **Be specific** — every finding must reference `file:line`
- **One root cause** — don't list every possible issue; find THE cause
- If confidence is LOW, explain what additional info would help narrow it down
- If the bug is environment-specific, say so explicitly
- If you cannot determine the root cause, report what you ruled out and suggest next debugging steps (e.g., "add logging at X", "check the value of Y at runtime")
