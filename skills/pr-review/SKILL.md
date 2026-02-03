---
name: ca-pr-review
description: Review a PR (or current branch if no PR number given) and post comments on GitHub
user-invocable: true
---

# PR Review

You are a senior code reviewer. Review a PR and post findings as inline comments on GitHub.

## Inputs

`$ARGUMENTS` — PR number (optional). If not provided, review the current branch locally.

## Flow: PR Number Given

### Step 1: Gather Context

```bash
# Get repo owner/name
REPO=$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')

# Get PR metadata
gh pr view $ARGUMENTS

# Get the diff
gh pr diff $ARGUMENTS

# Get commit SHA (needed for posting comments)
COMMIT_SHA=$(gh pr view $ARGUMENTS --json headRefOid --jq '.headRefOid')
```

### Step 2: Read Project Rules

Gather project-specific rules (**in priority order**):

1. **`CLAUDE.md`** — project-specific coding conventions, patterns, and rules. Highest priority.
2. **Project-local skills** — scan for `.claude/skills/**/*.md` in the target project. These may define architectural patterns, naming conventions, or workflow rules that the code should follow. **Do not** read the analyzer plugin's own skill files — only the target project's skills.

Read all found files. Extract any conventions, patterns, or constraints relevant to code review. **Priority**: `CLAUDE.md` > project skill conventions > built-in rules below > general best practices.

### Step 2.5: Use Biome MCP (if available)

If Biome MCP is available, use it to get structured lint diagnostics:

1. Call Biome MCP `lint` on changed files
2. Get structured errors with exact locations and rule IDs
3. Include Biome violations in the review (respect project's `biome.json`)

This is more accurate than manual style checking — Biome's rules take priority.

### Step 3: Review the Diff

Analyze every changed file in the diff. Check for:

#### Correctness

- Logic errors, missing edge cases, off-by-one errors
- Broken control flow (unreachable code, missing returns)
- Incorrect async/await usage (missing await, unhandled promises)

#### Security

- Injection vulnerabilities (SQL, NoSQL, command, template)
- Hardcoded secrets or credentials
- Missing input validation on user-facing endpoints
- Auth bypass, OWASP Top 10 (reference the security skill categories)

#### Style (defer to CLAUDE.md rules first, then these defaults)

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

#### React/NextJS

- Never report "Missing React import" — not needed in modern React
- Wrap callbacks in `useCallback`, computed objects in `useMemo`
- Do not memoize simple values (strings, numbers, booleans)
- Mark components with `React.FC`: `const MyComponent: React.FC = () => ...`
- Use explicit strings in JSX: `<>{'text'}</>` not `<>text</>`
- Export directly: `export const X = () => ...` not `const X = ...; export { X }`
- Avoid extra `<div>`s — use fragments `<>...</>` when possible
- Put loaders in parent components instead of passing `isLoading` props
- Extract all components from page files to separate files

#### NestJS

- Never add exports/imports to modules unless necessary
- Use typed EntityId (`UserId`, `VesselId`) instead of plain strings

#### Performance

- N+1 query patterns
- Missing indexes, unnecessary re-renders

#### Patterns

- Missing error handling on I/O operations
- Unused imports or variables introduced by the change
- Dead code introduced by the change

Assign severity to each issue:

- **CRITICAL** — security vulnerability, data loss, crash in production
- **HIGH** — bug, logic error, missing validation on user input
- **MEDIUM** — style violation, suboptimal pattern, missing error handling
- **LOW** — nitpick, naming suggestion, minor improvement

### Step 4: Confirm with User

**Never post comments without user confirmation.** Show a numbered preview of all findings:

```
Found N issues in PR #$ARGUMENTS:

1. [CRITICAL] SQL injection in UserService.ts:45
2. [HIGH] Missing auth guard on admin.controller.ts:23
3. [MEDIUM] Unused import in utils.ts:1
4. [LOW] Naming: prefer camelCase in config.ts:12

Post all 4 comments to GitHub? (yes / pick / no)
```

- **yes** — post all comments to GitHub
- **pick** — go through each issue one by one, showing full comment body, asking yes/no
- **no** — output the review locally only, do not post any comments

Wait for the user's response before proceeding. If the user picks `no`, skip Step 5 (Post) and Step 6 (Label) — go directly to the Output section with all issues listed as "local only".

### Step 5: Post Comments on GitHub

For each **confirmed** issue, post an inline comment on the PR:

```bash
gh api repos/OWNER/REPO/pulls/$ARGUMENTS/comments \
  --method POST \
  -f body="**[SEVERITY]** description" \
  -f commit_id="COMMIT_SHA" \
  -f path="file/path.ts" \
  -F line=LINE_NUMBER \
  -f side="RIGHT"
```

**CRITICAL line number rules:**

- Use the **actual file line number** from the modified file, NOT the position in the diff
- `side="RIGHT"` means the new/modified version of the file
- To find line numbers: look at the `gh pr diff` output — the `+` lines show the new file's line numbers on the right side
- If a line is not part of the diff (context-only line), place the comment on the nearest changed line instead and reference the actual location in the comment body
- If the `gh api` call returns a 422 error ("line could not be resolved"), retry on the nearest changed line

### Step 6: Add Label

```bash
# Create the label if it doesn't exist (--force is a no-op if it already exists)
gh label create "claude-reviewed" --description "Reviewed by Claude" --color "6f42c1" --force

gh pr edit $ARGUMENTS --add-label "claude-reviewed"
```

If the label command fails (e.g., due to project settings), note it in the output but do not treat it as an error.

## Flow: No PR Number

When no `$ARGUMENTS` is provided, review the current branch locally.

Detect the base branch automatically:

```bash
# Try the upstream tracking branch first, then fall back to develop
BASE=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null | sed 's|origin/||' || echo "develop")
git diff $BASE...HEAD
git log $BASE..HEAD --oneline
```

Review changes using the same criteria. Do NOT post GitHub comments for local-only review.

## Output Format

```
## Review: [APPROVE / REQUEST CHANGES]

### Issues
- file:line — issue (commented on GitHub ✓ / local only)

### Questions
- [anything unclear about intent or requirements]

### vs Requirements (if provided)
- [MEETS / PARTIAL / MISSING] — note

### Summary
[1-2 sentences on overall quality and what needs attention]
```

## Important

- **Do review test files** — unlike security/dead-code skills, PR review includes tests since they are part of the changeset
- **Always post comments on GitHub** when reviewing a PR — do not just output text
- Review ALL changed files, not just the first few
- If the diff is very large, prioritize CRITICAL/HIGH issues and note that the review was partial
- Do not comment on unchanged code (context lines) unless it directly relates to a changed line
- Group related issues into a single comment when they affect the same line
- Be specific: include the problematic code snippet and a suggested fix in the comment body
