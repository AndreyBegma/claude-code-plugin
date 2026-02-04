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
   - Offer to view the failed run logs:
     ```bash
     gh run view RUN_ID --log-failed
     ```
   - Show which checks failed, then use `AskUserQuestion` (see `../_shared/confirmation-flow.md` — Three-Way Choice):

     ```
     ⚠️ CI failed on this PR:
     - ❌ build — failed
     - ❌ test — failed
     - ✅ lint — passed
     ```

     Options:
     | Option | Description |
     |--------|-------------|
     | **View logs (Recommended)** | Show failed CI logs, then continue to review |
     | **Skip logs** | Continue to review without viewing logs |
     | **Cancel review** | Stop the review entirely |

3. If CI is still **running**, show status then use `AskUserQuestion` (Binary Choice):

   ```
   ⏳ CI is still running (build: in_progress, test: queued)
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **Wait (Recommended)** | Re-check every 30 seconds (max 5 minutes) |
   | **Continue** | Proceed with review without waiting for CI |

4. If all checks **passed** — proceed silently to Step 2.

### Step 2: Read Project Rules

Read `CLAUDE.md` for project conventions (highest priority). Also scan `.claude/skills/**/*.md` for project-local patterns.

**Priority**: `CLAUDE.md` > project skill conventions > general best practices.

### Step 2.5: Check Biome MCP

Check if Biome MCP is available. Biome provides structured lint diagnostics for more accurate review.

If Biome MCP is **not available**, ask user to install:

Use `AskUserQuestion`:

- **question**: "Biome MCP enhances PR review with structured lint diagnostics. Install it?"
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
   - After user confirmation, reply to those comments with "✅ Fixed"

4. Show resolved issues, then use `AskUserQuestion` (Bulk Selection without severity — see `../_shared/confirmation-flow.md`):

   ```
   Previously reported issues now fixed:

   1. Comment by @reviewer on user.service.ts:45 — "Missing null check" → FIXED
   2. Comment by @reviewer on auth.ts:12 — "Missing validation" → FIXED
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **All (Recommended)** | Reply "✅ Fixed" to all resolved comments |
   | **None** | Skip, don't reply to any |

   User can type numbers (`1`) or inverted (`!2`) in "Other".

5. For each confirmed resolved comment, show the reply and use `AskUserQuestion` (Single-Item Confirmation):

   ```
   Reply to comment by @reviewer on user.service.ts:45:
   "✅ Fixed"
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **Send (Recommended)** | Post the reply as-is |
   | **Edit** | Modify the reply before posting |

   Then post:

   ```bash
   gh api repos/OWNER/REPO/pulls/comments/COMMENT_ID/replies --method POST -f body="✅ Fixed"
   ```

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
- No any types without justification
- Import o

Apply rules from `../_shared/style-rules.md`. **CLAUDE.md rules take priority.**

#### Performance

- N+1 query patterns
- Missing indexes, unnecessary re-renders

#### Patterns

- Missing error handling on I/O operations
- Unused imports or variables introduced by the change
- Dead code introduced by the change

Assign severity per `../_shared/severity-levels.md` (CRITICAL / HIGH / MEDIUM / LOW). Then show the numbered list and use `AskUserQuestion` (Bulk Selection with severity — see `../_shared/confirmation-flow.md`):

```
Review findings:

1. [CRITICAL] SQL injection in UserService.ts:45
2. [HIGH] Missing auth guard on admin.controller.ts:23
3. [MEDIUM] Unused import in utils.ts:1
4. [LOW] Naming: prefer camelCase in config.ts:12
```

Options:
| Option | Description |
|--------|-------------|
| **All (Recommended)** | Post all 4 comments to GitHub |
| **Critical only** | Post only CRITICAL severity comments |
| **High+** | Post CRITICAL + HIGH comments |
| **None** | Output review locally only, don't post |

User can type numbers (`1 3`) or inverted (`!3 4`) in "Other".

````

Wait for the user's response before proceeding. If the user picks `None`, skip Step 5 (Post) and Step 6 (Label) — go directly to the Output section with all issues listed as "local only".

### Step 5: Post Comments on GitHub

For each **confirmed** issue, show the full comment body and use `AskUserQuestion` (Single-Item Confirmation):

```
Comment for user.service.ts:45:

**[HIGH]** Missing null check — `user` can be undefined when...
```

Options:
| Option | Description |
|--------|-------------|
| **Send (Recommended)** | Post the comment as-is |
| **Edit** | Modify the comment body before posting |

**Command template** (substitute OWNER, REPO, COMMIT_SHA, and issue details):

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments --method POST -f body="**[SEVERITY]** description" -f commit_id="COMMIT_SHA" -f path="file/path.ts" -F line=LINE_NUMBER -f side="RIGHT"
````

**Example with real values:**

```bash
gh api repos/acme/backend/pulls/18/comments --method POST -f body="**[HIGH]** Missing null check" -f commit_id="abc123def" -f path="src/user.service.ts" -F line=45 -f side="RIGHT"
```

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

### Step 7: Offer to Create Issues

After posting comments, **always** offer to create GitHub issues for all findings (any severity) so they don't get lost in PR comments.

1. If no issues were found at all, skip this step
2. Show the user **all** findings, then use `AskUserQuestion` (Bulk Selection with severity — see `../_shared/confirmation-flow.md`):

   ```
   Create GitHub issues for review findings?

   1. [CRITICAL] SQL injection in UserService.ts:45
   2. [HIGH] Missing auth guard on admin.controller.ts:23
   3. [MEDIUM] No allowedUsers check on unmarked-threads command
   4. [LOW] Fire-and-forget async without await
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **All (Recommended)** | Create issues for every finding |
   | **Critical only** | Create issues only for CRITICAL findings |
   | **High+** | Create issues for CRITICAL + HIGH findings |
   | **None** | Skip issue creation entirely |

   User can type numbers (`1 3`) or inverted (`!4`) in "Other".

3. For each confirmed issue, invoke `/ca-issue` with:
   - Title: `[SEVERITY] Brief description`
   - Body: Full details from the review comment + link to PR
   - Labels: `bug` for CRITICAL, `bug` or `code-review` for HIGH, `code-quality` for MEDIUM/LOW
   - Reference: `Found during PR review: #PR_NUMBER`

4. After creating issues, show summary:

   ```
   Created 2 issues:
   - #123: [CRITICAL] SQL injection in UserService.ts
   - #124: [HIGH] Missing auth guard in admin.controller.ts

   Skipped:
   - [LOW] Fire-and-forget async (user declined)
   ```

5. For CRITICAL issues, offer to start debugging. Use `AskUserQuestion` (Bulk Selection without severity):

   ```
   Start deep analysis for critical issues?

   1. #123: [CRITICAL] SQL injection in UserService.ts
   2. #124: [CRITICAL] Auth bypass in admin.controller.ts
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **All (Recommended)** | Run `/ca-debug` for all critical issues |
   | **None** | Skip debugging |

   User can type numbers (`1`) or inverted (`!2`) in "Other".

   This creates a full workflow: Review → Issue → Debug

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
