---
name: ca-pr-prepare-merge
description: Extract generalizable rules from PR comments and open a PR updating CLAUDE.md instructions
user-invocable: true
---

# PR Prepare Merge

You are a senior engineering standards curator. Given a PR number, you review all human comments, extract feedback that can be generalized into reusable CLAUDE.md rules, and open a PR against `main` with the updates.

## Inputs

`$ARGUMENTS` — the PR number to process (required).

## Step 1: Gather Context

```bash
# Get repo owner/name
gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'

# Get PR details
gh pr view $ARGUMENTS --json title,body,author,baseRefName,headRefName

# Get all review comments (inline code comments)
gh api repos/OWNER/REPO/pulls/$ARGUMENTS/comments --paginate

# Get all issue-level comments (general discussion)
gh api repos/OWNER/REPO/issues/$ARGUMENTS/comments --paginate

# Get all review bodies (approve/request-changes comments)
gh api repos/OWNER/REPO/pulls/$ARGUMENTS/reviews --paginate
```

Replace `OWNER/REPO` with the values from the first command.

## Step 2: Filter Comments

From all collected comments, keep ONLY comments that:

1. **Come from humans** — skip bot comments (author association: `NONE` with bot-like names, or `login` containing `[bot]`)
2. **Contain actionable feedback** — skip approvals like "LGTM", "looks good", emoji-only reactions
3. **Are generalizable** — the feedback applies beyond this single PR. Skip comments that are purely about this PR's specific logic (e.g., "rename this variable to X", "this should be `userId` not `id`")

### What IS generalizable (extract these):

- Coding patterns: "always use early returns", "prefer `const` over `let`"
- Architecture rules: "services should not import from controllers", "use DTOs for API responses"
- Security practices: "never log request bodies", "always validate file upload types"
- Convention decisions: "use arrow functions for service methods", "use `findUniqueOrThrow` instead of null checks"
- Process rules: "add migration for schema changes", "update OpenAPI spec when changing endpoints"
- Domain rules: "use Decimal.js for monetary values", "vessel types must use Prisma enum"

### What is NOT generalizable (skip these):

- One-off fixes: "this variable name is wrong", "missing semicolon here"
- PR-specific logic: "this query should filter by orgId too"
- Questions: "why did you use X here?" (unless the answer establishes a rule)
- Nitpicks with no pattern: "typo in comment"

## Step 3: Read Current Rules

Read existing project rules to avoid duplicates:

1. **`CLAUDE.md`** — read and understand the existing rules and structure.
2. **Project-local skills** — scan for `.claude/skills/**/*.md` in the target project. These may already contain conventions that overlap with PR feedback. **Do not** read the analyzer plugin's own skill files.

If no `CLAUDE.md` exists, you will create one with a standard structure.

## Step 4: Draft Updates

For each generalizable comment:

1. Check if the rule already exists in `CLAUDE.md` or project-local skills — if yes, skip it
2. Determine the best section to place it (create a new section if needed)
3. Write the rule as a concise, imperative instruction (e.g., "Use `findUniqueOrThrow` instead of `findUnique` + null check")

### Rule format:

- One line per rule, prefixed with `- `
- Imperative mood: "Use X", "Always Y", "Never Z", "Prefer A over B"
- Include a brief "why" only if not obvious
- Include a bad/good code example ONLY if the pattern is non-trivial

## Step 5: Confirm with User

**Never create a PR without user confirmation.** Show a numbered preview of all extracted rules:

```
Extracted N rules from PR #$ARGUMENTS:

1. "Use findUniqueOrThrow instead of findUnique + null check"
   → Source: @reviewer — "we should always use the throwing variant"

2. "Services must not import from controllers"
   → Source: @lead — "this breaks our layered architecture"

3. "Use Decimal.js for all monetary values"
   → Source: @reviewer — "floating point will cause rounding bugs"

Skipped: 5 comments (not generalizable / duplicates / bot)

Add all 3 rules to CLAUDE.md and create PR? (yes / pick / no)
```

- **yes** — include all rules, create the PR
- **pick** — go through each rule one by one, asking yes/no
- **no** — stop, do not create a branch or PR

Wait for the user's response before proceeding. If the user picks `no`, skip to Step 7 (Output) and report that no PR was created.

## Step 6: Create PR

```bash
# Create a new branch from main
git checkout main
git pull origin main
git checkout -b claude-instructions-from-pr-<PR_NUMBER>

# Apply the CLAUDE.md changes (use Edit tool)

# Commit (without Co-Authored-By or AI attribution)
git add CLAUDE.md
git commit -m "Update CLAUDE.md with rules from PR #<PR_NUMBER>" --no-gpg-sign

# Push and create PR
git push -u origin claude-instructions-from-pr-<PR_NUMBER>
```

**Important:** Do NOT add `Co-Authored-By`, `Signed-off-by`, or any AI/Claude attribution to commits. The commit message should be clean and concise.

Create the PR with `gh pr create`. After creating the PR, add a label:

```bash
# Create the label if it doesn't exist
gh label create "claude-rules" --description "Auto-extracted rules from PR comments" --color "1d76db" --force

# Add label to the newly created PR
gh pr edit --add-label "claude-rules"
```

Use the following structure for the body (replace placeholders with actual values):

- **Base**: `main`
- **Title**: `Update CLAUDE.md with rules extracted from PR #<PR_NUMBER>`
- **Body**:

```
## Summary

Extracted generalizable coding rules from review comments on PR #<PR_NUMBER> and added them to CLAUDE.md.

## Extracted Rules

- **Rule**: [the rule added]
  - **Source**: PR #<PR_NUMBER> comment by @[author] — "[original comment snippet]"

## Notes

- Only generalizable patterns were extracted (project-specific feedback was skipped)
- Existing rules were not duplicated
- Rules were placed in the most appropriate section of CLAUDE.md
```

## Step 7: Output

```
## PR Prepare Merge: #$ARGUMENTS

### Extracted Rules
- [each new rule with source reference]

### Skipped Comments
- [count] comments skipped (not generalizable / already covered / bot comments)

### PR Created
- PR URL: [link]
- Branch: claude-instructions-from-pr-$ARGUMENTS
- Base: main

### No Changes Needed
[If no generalizable rules were found, state this and do NOT create a PR]
```

## Important

- **Read-only on the target PR** — do not modify, comment on, or merge the original PR
- **Only modify CLAUDE.md** — do not touch any other files
- **Preserve existing structure** — add rules to existing sections where they fit; only create new sections if necessary
- **No duplicates** — if a rule already exists in CLAUDE.md or project-local skills (even worded differently), skip it
- **If no rules found** — report that no generalizable feedback was found and exit without creating a PR
