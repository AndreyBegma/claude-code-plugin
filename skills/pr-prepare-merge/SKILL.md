---
name: ca-pr-prepare-merge
description: Extract generalizable rules from PR comments and open a PR updating CLAUDE.md instructions
user-invocable: true
---

# PR Prepare Merge

You are a senior engineering standards curator. Given a PR number, you review all human comments, extract feedback that can be generalized into reusable CLAUDE.md rules, and open a PR against the source PR's branch with the updates.

## Inputs

`$ARGUMENTS` — the PR number to process (required).

## Step 1: Gather Context

Run these commands **one at a time** (do not chain):

1. Get repo info:

   ```bash
   gh repo view --json owner,name
   ```

   Parse the JSON to extract `owner.login` and `name`. Use these as `OWNER` and `REPO` below.

2. Get PR details:

   ```bash
   gh pr view $ARGUMENTS --json title,body,author,baseRefName,headRefName
   ```

3. Get all review comments (inline code comments):

   ```bash
   gh api repos/OWNER/REPO/pulls/$ARGUMENTS/comments --paginate
   ```

4. Get all issue-level comments (general discussion):

   ```bash
   gh api repos/OWNER/REPO/issues/$ARGUMENTS/comments --paginate
   ```

5. Get all review bodies (approve/request-changes comments):
   ```bash
   gh api repos/OWNER/REPO/pulls/$ARGUMENTS/reviews --paginate
   ```

Replace `OWNER` and `REPO` with the values from command 1.

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

If no `CLAUDE.md` exists, create one with this structure:

```markdown
# Project Name

Brief description of the project.

## Architecture

- [Layer/module structure rules]

## Code Style

- [Naming conventions, formatting rules]

## Patterns

- [Preferred patterns and anti-patterns]

## Security

- [Security-related rules]

## Testing

- [Testing conventions]
```

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

**Never create a PR without user confirmation.**

First, output the numbered list of extracted rules as plain text (NOT inside AskUserQuestion):

```
Extracted N rules from PR #$ARGUMENTS:

1. "Use findUniqueOrThrow instead of findUnique + null check"
   → Source: @reviewer — "we should always use the throwing variant"

2. "Services must not import from controllers"
   → Source: @lead — "this breaks our layered architecture"

3. "Use Decimal.js for all monetary values"
   → Source: @reviewer — "floating point will cause rounding bugs"

Skipped: 5 comments (not generalizable / duplicates / bot)
```

Then use `AskUserQuestion` with a **short** question and **concise** option descriptions (do NOT repeat the rules list inside the options):

- **question**: "Which rules should be included in CLAUDE.md?"
- **options**:

| Option | Description |
|--------|-------------|
| **All (Recommended)** | Include all N rules |
| **None** | Do not create a branch or PR |

User can type numbers (`1 3`) or inverted (`!2`) in "Other".

Wait for the user's response before proceeding. If the user picks `None`, skip to Step 7 (Output) and report that no PR was created.

### Step 5a: Confirm Each Rule

For each **confirmed** rule, show the full rule text and use `AskUserQuestion` (Single-Item Confirmation — see `../_shared/confirmation-flow.md`):

```
Rule 1:

- "Use findUniqueOrThrow instead of findUnique + null check"
  → Source: @reviewer — "we should always use the throwing variant"
  → Section: Patterns
```

Options:
| Option | Description |
|--------|-------------|
| **Send (Recommended)** | Add the rule as-is |
| **Edit** | Modify the rule text before adding |

If the user picks **Edit**, apply their changes to the rule text. Then continue to the next rule.

## Step 5.5: Check Branch Protection & Merge Readiness

Before creating the rules PR, check if the **source PR** is ready to merge:

1. Check PR status:

   ```bash
   gh pr view $ARGUMENTS --json mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
   ```

2. Parse the response and show a checklist:

   ```
   ## Merge Readiness for PR #$ARGUMENTS

   - [✅/❌] CI Status: [passed/failed/pending]
   - [✅/❌] Reviews: [approved/changes_requested/review_required]
   - [✅/❌] Conflicts: [none/has conflicts]
   - [✅/❌] Mergeable: [yes/no/unknown]

   Overall: [READY TO MERGE / NOT READY]
   ```

3. If there are **conflicts**:

   ```
   ⚠️ PR #$ARGUMENTS has merge conflicts.
   The author needs to resolve conflicts before merging.
   ```

4. If **reviews are required** but not approved:

   ```
   ⚠️ PR #$ARGUMENTS requires review approval.
   Current status: [CHANGES_REQUESTED / REVIEW_REQUIRED]
   ```

5. If **CI failed**:

   ```
   ⚠️ CI checks failed on PR #$ARGUMENTS.
   Failed checks: [list of failed checks]
   ```

6. Continue to Step 6 regardless — the rules PR can be created even if source PR isn't ready.
   The checklist is informational for the user.

## Step 6: Create PR

Run these commands **one at a time**:

1. Switch to the source PR's branch (`headRefName` from Step 1) and update:

   ```bash
   git checkout <HEAD_REF_NAME>
   ```

   ```bash
   git pull origin <HEAD_REF_NAME>
   ```

2. Create new branch from the PR's branch:

   ```bash
   git checkout -b claude-instructions-from-pr-<PR_NUMBER>
   ```

3. Apply the CLAUDE.md changes using the Edit tool.

4. Stage and commit:

   ```bash
   git add CLAUDE.md
   ```

   ```bash
   git commit -m "Update CLAUDE.md with rules from PR #<PR_NUMBER>" --no-gpg-sign
   ```

5. Push the branch:
   ```bash
   git push -u origin claude-instructions-from-pr-<PR_NUMBER>
   ```

**Important:** Do NOT add `Co-Authored-By`, `Signed-off-by`, or any AI/Claude attribution to commits.

6. Before creating the PR, show the full PR body and use `AskUserQuestion` (Single-Item Confirmation — see `../_shared/confirmation-flow.md`):

   ```
   PR preview:

   Title: Update CLAUDE.md with rules extracted from PR #18
   Base: <HEAD_REF_NAME> (PR #$ARGUMENTS branch)

   ## Summary
   [full body here]
   ```

   Options:
   | Option | Description |
   |--------|-------------|
   | **Send (Recommended)** | Create the PR as-is |
   | **Edit** | Modify the title or body before creating |

   Then create the PR with `gh pr create --base <HEAD_REF_NAME>` (targeting the source PR's branch).

7. Add label (run separately):
   ```bash
   gh label create "claude-rules" --description "Auto-extracted rules from PR comments" --color "1d76db" --force
   ```
   ```bash
   gh pr edit --add-label "claude-rules"
   ```

Use the following structure for the body (replace placeholders with actual values):

- **Base**: `<HEAD_REF_NAME>` (the source PR's branch)
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
- Base: <HEAD_REF_NAME> (PR #$ARGUMENTS branch)

### No Changes Needed
[If no generalizable rules were found, state this and do NOT create a PR]
```

## Important

- **Read-only on the target PR** — do not modify, comment on, or merge the original PR
- **Only modify CLAUDE.md** — do not touch any other files
- **Preserve existing structure** — add rules to existing sections where they fit; only create new sections if necessary
- **No duplicates** — if a rule already exists in CLAUDE.md or project-local skills (even worded differently), skip it
- **If no rules found** — report that no generalizable feedback was found and exit without creating a PR
