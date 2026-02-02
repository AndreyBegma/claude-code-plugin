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

Read the project's `CLAUDE.md` to understand project-specific coding conventions. Review against those rules first, then apply general best practices.

### Step 3: Review the Diff

Analyze every changed file in the diff. Focus on:

- **Correctness**: Logic errors, missing edge cases, off-by-one errors
- **Security**: Injection, auth bypass, secrets, OWASP Top 10 (reference the security skill categories)
- **Style**: Violations of CLAUDE.md rules
- **Performance**: N+1 queries, missing indexes, unnecessary re-renders
- **Types**: Unsafe casts, `any` usage, missing validation

Assign severity to each issue:

- **CRITICAL** — security vulnerability, data loss, crash in production
- **HIGH** — bug, logic error, missing validation on user input
- **MEDIUM** — style violation, suboptimal pattern, missing error handling
- **LOW** — nitpick, naming suggestion, minor improvement

### Step 4: Post Comments on GitHub

For each issue found, post an inline comment on the PR:

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

### Step 5: Add Label

```bash
# Create the label if it doesn't exist (--force is a no-op if it already exists)
gh label create "claude-reviewed" --description "Reviewed by Claude" --color "6f42c1" --force

gh pr edit $ARGUMENTS --add-label "claude-reviewed"
```

If the label command fails (e.g., due to project settings), note it in the output but do not treat it as an error.

## Flow: No PR Number

When no `$ARGUMENTS` is provided, review the current branch locally:

```bash
git diff develop...HEAD
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

- **Always post comments on GitHub** when reviewing a PR — do not just output text
- Review ALL changed files, not just the first few
- If the diff is very large, prioritize CRITICAL/HIGH issues and note that the review was partial
- Do not comment on unchanged code (context lines) unless it directly relates to a changed line
- Group related issues into a single comment when they affect the same line
- Be specific: include the problematic code snippet and a suggested fix in the comment body
