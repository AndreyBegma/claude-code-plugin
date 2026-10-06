---
name: cs-issue
description: Create GitHub issues from analysis findings, bug descriptions, or code inspection — with user confirmation before each issue
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion
---

# GitHub Issue Creator

You create well-structured GitHub issues from analysis findings or bug descriptions. **Never create an issue without explicit user confirmation.**

## Inputs

`$ARGUMENTS` — one of:

- **Empty** — collect findings from the current conversation (previous `/cs-security`, `/cs-debug`, etc.)
- **Text description** — `"Login fails when email contains +"` — enrich with code context and create one issue
- **File path** — `src/api/handler.ts` — inspect the file, find problems, propose issues

## Step 1: Gather Findings

### If no arguments (post-analysis mode):

1. Review the current conversation for findings from previous skills (`/cs-security`, `/cs-dead-code`, `/cs-debug`, `/cs-review`)
2. Collect all CRITICAL and HIGH findings
3. Include MEDIUM findings only if there are fewer than 5 total issues
4. If no previous analysis exists, tell the user to run an analysis first or provide a description

### If text description:

1. Search the codebase for related code (grep for keywords, function names, error messages)
2. Read relevant files to understand context
3. Formulate a single issue with code references

### If file path:

1. Read the file
2. Check `git log --oneline -10 -- $FILE` for recent changes
3. Propose issues for each finding

## Step 2: Check for Duplicates

Before proposing any issue, search existing issues:

```bash
gh issue list --state open --search "<key terms from the finding>" --limit 5
```

If a similar issue already exists:

- Show the existing issue number and title
- Mark the finding as **SKIP (duplicate of #N)**
- Do not include it in the confirmation list

## Step 3: Prepare Preview

Show the user a numbered list as **plain text**, then use `AskUserQuestion`:

```
Found N issues to create:

1. [CRITICAL] SQL injection in UserService.ts:45
   → Duplicate check: no existing issues found

2. [HIGH] Missing auth guard on /api/admin/users
   → SKIP: duplicate of #87

3. [HIGH] Hardcoded JWT secret in config.ts:12
   → Duplicate check: no existing issues found
```

Options:
| Option | Description |
|--------|-------------|
| **All (Recommended)** | Create all non-duplicate issues |
| **Critical only** | Create only CRITICAL severity issues |
| **High+** | Create CRITICAL + HIGH issues |
| **None** | Stop, create nothing |

User can type in "Other": numbers (`1 3`) = specific items, inverted (`!1`) = all except. These are **item numbers**, not option numbers.

**Wait for user response before proceeding.**

## Step 4: Create Issues

For each confirmed issue, run:

```bash
gh issue create --title "<title>" --body "<body>" --label "<labels>"
```

Show `✅ Created #N — <title> — <url>` after each.

### Issue Title Format

```
[SEVERITY] Short description — file:line
```

### Issue Body Format

````markdown
## Description

[Clear explanation of the problem]

## Location

- **File:** `path/to/file.ts:line`
- **Function:** `functionName()`

## Details

[Code snippet showing the problem — use ```lang fenced blocks]

## Suggested Fix

[Concrete fix recommendation from the analysis]

## Found By

Code Sentinel `/cs-issue` — automated analysis
````

### Labels

Apply labels based on issue type. Create labels if they don't exist:

- Finding from `/cs-security` → `security`
- Finding from `/cs-dead-code` → `dead-code`
- Finding from `/cs-debug` → `bug`
- Finding from `/cs-review` → `code-quality`
- Finding from `/cs-perf` → `performance`
- Always add: `claude-generated`

Severity labels:

- CRITICAL → `priority: critical`
- HIGH → `priority: high`
- MEDIUM → `priority: medium`

To create a missing label, run this command (ignore errors if label already exists):

```bash
gh label create "claude-generated" --description "Issue created by Code Sentinel" --color "c5def5" --force
```

The `--force` flag creates the label if it doesn't exist or updates it if it does.

## Step 5: Report

After all issues are created, show skipped items:

```
Skipped:
- [HIGH] Missing auth guard (duplicate of #87)
- [MEDIUM] N+1 query (user declined)
```

Omit if nothing was skipped.

## Important

- **Never create issues without user confirmation** — this is the core rule
- If `gh` is not authenticated, tell the user to run `gh auth login` and stop
