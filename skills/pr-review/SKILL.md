---
name: ca-pr-review
description: Review a PR (or current branch if no PR number given) and post comments on GitHub
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, mcp__biome__*
---

# PR Review

You are a senior code reviewer. Review a PR and post findings as inline comments on GitHub.

## Inputs

`$ARGUMENTS` — PR number (optional). If not provided, review the current branch locally.

## Flow: PR Number Given

### Step 1: Gather Context

Run these commands **one at a time** (do not chain with `&&` or `|`):

1. Get repo info:

   ```bash
   gh repo view --json owner,name
   ```

   Parse the JSON response to extract `owner.login` and `name`.

2. Get PR metadata:

   ```bash
   gh pr view $ARGUMENTS --json title,body,author,state,headRefOid,baseRefName,headRefName
   ```

   Save `headRefOid` as `COMMIT_SHA` for posting comments later.

3. Get the diff:
   ```bash
   gh pr diff $ARGUMENTS
   ```

### Step 1.5: Check CI Status

Before reviewing code, check if CI has passed:

1. Get CI run status for the PR branch:

   ```bash
   gh pr checks $ARGUMENTS
   ```

2. If any check **failed**:
   - Show the user which checks failed
   - Automatically view the failed run logs:
     ```bash
     gh run view RUN_ID --log-failed
     ```
   - Show the summary and continue to review:

     ```
     ⚠️ CI failed on this PR:
     - ❌ build — failed
     - ❌ test — failed
     - ✅ lint — passed
     ```

   Then proceed to Step 2.

3. If CI is still **running**, show status and proceed to review without waiting:

   ```
   ⏳ CI is still running (build: in_progress, test: queued) — proceeding with review.
   ```

4. If all checks **passed** — proceed silently to Step 2.

### Step 2: Read Project Rules

Read `CLAUDE.md` for project conventions (highest priority). Also scan `.claude/skills/**/*.md` for project-local patterns.

**Priority**: `CLAUDE.md` > project skill conventions > general best practices.

### Step 2.5: Check Biome MCP

Check if Biome MCP is available. Biome provides structured lint diagnostics for more accurate review.

If Biome MCP is **not available**, output a warning and continue without it:

```
⚠️ Biome MCP not available. Lint analysis will be less accurate.
   Note: Biome MCP package is not yet available on npm. See https://github.com/biomejs/biome/discussions/6017
```

### Step 2.6: Check Existing PR Comments

Before reviewing, check if there are existing review comments from previous reviews:

1. Get all existing review comments:

   ```bash
   gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments
   ```

2. For each comment, check:
   - Is the issue mentioned in the comment still present in the current diff?
   - Does the comment already have a reply?

3. If an issue from a previous comment is **now fixed** and has **no reply**:
   - Add to a separate list: "Resolved issues from previous reviews"

4. Show resolved issues, then automatically reply "✅ Fixed" to all of them:

   ```
   Previously reported issues now fixed:

   1. Comment by @reviewer on user.service.ts:45 — "Missing null check" → FIXED
   2. Comment by @reviewer on auth.ts:12 — "Missing validation" → FIXED
   ```

5. For each resolved comment, post the reply automatically:

   ```bash
   gh api repos/OWNER/REPO/pulls/comments/COMMENT_ID/replies --method POST -f body="✅ Fixed"
   ```

   After posting each reply, show immediate feedback:

   ```
   ✅ Replied "Fixed" to @reviewer on user.service.ts:45
      https://github.com/acme/backend/pull/18#discussion_r1234567890
   ```

   Track all replies for the final summary.

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
- Prefer const over let unless reassignment is necessary
- Always prefer destructuring
- Early returns over deep nesting (invert conditions, return early)
- Braces on all control flow statements — never single-line if statements
- No type assertions (as, non-null assertion) without justification
- No `any` types without justification
- Import ordering — group by external/internal, alphabetize within groups

Apply rules from `../_shared/style-rules.md`. **CLAUDE.md rules take priority.**

#### Performance

- N+1 query patterns
- Missing indexes, unnecessary re-renders

#### Patterns

- Missing error handling on I/O operations
- Unused imports or variables introduced by the change
- Dead code introduced by the change

Assign severity per `../_shared/severity-levels.md` (CRITICAL / HIGH / MEDIUM / LOW). Show the numbered list, then automatically post ALL findings as comments on GitHub:

```
Review findings:

1. [CRITICAL] SQL injection in UserService.ts:45
2. [HIGH] Missing auth guard on admin.controller.ts:23
3. [MEDIUM] Unused import in utils.ts:1
4. [LOW] Naming: prefer camelCase in config.ts:12

Posting all 4 comments to GitHub...
```

### Step 5: Post Comments on GitHub

For each issue, automatically post the comment to GitHub.

**Command template** (substitute OWNER, REPO, COMMIT_SHA, and issue details):

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments --method POST -f body="**[SEVERITY]** description" -f commit_id="COMMIT_SHA" -f path="file/path.ts" -F line=LINE_NUMBER -f side="RIGHT"
```

**Example with real values:**

```bash
gh api repos/acme/backend/pulls/18/comments --method POST -f body="**[HIGH]** Missing null check" -f commit_id="abc123def" -f path="src/user.service.ts" -F line=45 -f side="RIGHT"
```

**After posting each comment:**

1. Parse the JSON response from `gh api` to extract `id` and `html_url`
2. Show immediate feedback to the user:

   ```
   ✅ Posted: user.service.ts:45 — Missing null check
      https://github.com/acme/backend/pull/18#discussion_r1234567890
   ```

3. If the command fails, show the error:

   ```
   ❌ Failed: user.service.ts:45 — "line 45 does not belong to the diff"
      Retrying on nearest changed line...
   ```

4. Track all posted comments with their URLs for the final summary.

**CRITICAL line number rules:**

- Use the **actual file line number** from the modified file, NOT the position in the diff
- `side="RIGHT"` means the new/modified version of the file
- To find line numbers: look at the `gh pr diff` output — the `+` lines show the new file's line numbers on the right side
- If a line is not part of the diff (context-only line), place the comment on the nearest changed line instead and reference the actual location in the comment body
- If the `gh api` call returns a 422 error ("line could not be resolved"), retry on the nearest changed line

### Step 6: Add Label

Run these commands **one at a time**:

1. Create the label if it doesn't exist:

   ```bash
   gh label create "claude-reviewed" --description "Reviewed by Claude" --color "6f42c1" --force
   ```

2. Add label to the PR:
   ```bash
   gh pr edit $ARGUMENTS --add-label "claude-reviewed"
   ```

If the label command fails (e.g., due to project settings), note it in the output but do not treat it as an error.

## Flow: No PR Number

When no `$ARGUMENTS` is provided, review the current branch locally.

Detect the base branch:

1. Check for upstream tracking branch:

   ```bash
   git rev-parse --abbrev-ref @{upstream}
   ```

   If this fails, check which default branch exists:

   ```bash
   git show-ref --verify --quiet refs/heads/main
   ```

   If `main` exists, use it. Otherwise use `develop`. If the upstream command returns something like `origin/main`, strip the `origin/` prefix.

2. Get the diff against base:

   ```bash
   git diff develop...HEAD
   ```

   (Replace `develop` with the detected base branch)

3. Get commit log:
   ```bash
   git log develop..HEAD --oneline
   ```

Review changes using the same criteria. Do NOT post GitHub comments for local-only review.

## Output Format

```
## Review: [APPROVE / REQUEST CHANGES]

**PR:** #18 — Feature: Add user authentication
**Branch:** feature/auth → main
**CI Status:** ✅ All checks passed

### Posted Comments (3)

| # | File | Line | Severity | Issue | Link |
|---|------|------|----------|-------|------|
| 1 | user.service.ts | 45 | CRITICAL | SQL injection | [view](URL) |
| 2 | admin.controller.ts | 23 | HIGH | Missing auth guard | [view](URL) |
| 3 | utils.ts | 1 | MEDIUM | Unused import | [view](URL) |

### Resolved from Previous Reviews (2)
- ✅ Replied "Fixed" to @reviewer on auth.ts:12 — [view](URL)
- ✅ Replied "Fixed" to @reviewer on config.ts:5 — [view](URL)

### Questions
- [anything unclear about intent or requirements]

### Summary
[1-2 sentences on overall quality and what needs attention]
```

**For local-only review (no PR number):**

```
## Review: [APPROVE / REQUEST CHANGES]

**Branch:** feature/auth (local, not pushed)
**Base:** main

### Issues Found (4)

| # | File | Line | Severity | Issue |
|---|------|------|----------|-------|
| 1 | user.service.ts | 45 | CRITICAL | SQL injection |
| 2 | admin.controller.ts | 23 | HIGH | Missing auth guard |
| 3 | utils.ts | 1 | MEDIUM | Unused import |
| 4 | config.ts | 12 | LOW | Naming: prefer camelCase |

### Summary
[1-2 sentences on overall quality and what needs attention]

💡 Run `/ca-pr-review <PR_NUMBER>` after creating a PR to post these as GitHub comments.
```

## Important

- **Do review test files** — unlike security/dead-code skills, PR review includes tests since they are part of the changeset
- **Always post comments on GitHub** when reviewing a PR — do not just output text
- Review ALL changed files, not just the first few
- If the diff is very large, prioritize CRITICAL/HIGH issues and note that the review was partial
- Do not comment on unchanged code (context lines) unless it directly relates to a changed line
- Group related issues into a single comment when they affect the same line
- Be specific: include the problematic code snippet and a suggested fix in the comment body
