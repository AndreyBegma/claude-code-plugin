# Claude Code Analyzer Plugin

A collection of Claude Code skills for automated codebase analysis.

All commands use the `ca-` prefix (code-analyzer) to avoid conflicts with built-in or other plugin commands.

## Structure

```
skills/
  security/SKILL.md          — /ca-security — Security vulnerability scanner (OWASP Top 10, secrets, injections)
  dead-code/SKILL.md         — /ca-dead-code — Dead code detector (unused exports, files, dependencies)
  code-review/SKILL.md       — /ca-code-review — Local code review for style and correctness
  pr-review/SKILL.md         — /ca-pr-review — Review a PR and post inline comments on GitHub
  pr-prepare-merge/SKILL.md  — /ca-pr-prepare-merge — Extract rules from PR comments and update CLAUDE.md via PR
```

## Skills Overview

### 🔴 `/ca-security`

**Finds:** Exposed secrets, SQL/NoSQL injection, SSRF, auth bypass, insecure validation, race conditions, data exposure, weak crypto

**Examples:**

- Hardcoded API keys, AWS credentials, JWT tokens in source code
- SQL queries with string interpolation: `query(\`SELECT \* FROM users WHERE id = ${id}\`)`
- Missing CORS validation, open redirects, weak password hashing
- Debug endpoints in production, GraphQL introspection enabled

**Output:** CRITICAL & HIGH issues only with file:line and remediation

---

### ⚰️ `/ca-dead-code`

**Finds:** Unused npm packages, unreferenced files, orphaned exports

**Examples:**

- Package in package.json but never imported: `uuid`, `ts-node`, deprecated packages
- Files with 0 imports: old components, orphaned utilities
- Exported function used nowhere: `export const unusedHelper = () => {}`

**Output:** HIGH confidence findings organized by type (dependencies, files, exports)

---

### 🔍 `/ca-code-review`

**Does:** Quick local code review for style and correctness — generic, project-agnostic

**Workflow:**

1. Reads project `CLAUDE.md` for project-specific rules (priority over general best practices)
2. Gets diff (staged/unstaged changes)
3. Reviews: correctness, security, style, patterns
4. Severity: HIGH / MEDIUM / LOW

**Usage:** `/ca-code-review` (all local changes) or `/ca-code-review <path>` (specific file/directory)

**Output:** Summary + Issues list + Verdict (APPROVE / REQUEST CHANGES)

**Difference from `/ca-pr-review`:** `/ca-code-review` is a lightweight local review without GitHub interaction. `/ca-pr-review` posts inline comments on GitHub.

---

### 👀 `/ca-pr-review`

**Does:** Reviews a PR (or current branch) for correctness, security, style, and performance — posts inline comments directly on GitHub

**Workflow:**

1. Fetches PR metadata, diff, and commit SHA
2. Reads project `CLAUDE.md` for project-specific rules
3. Reviews all changed files (correctness, security, style, performance, types)
4. Posts inline comments via `gh api` with severity labels
5. Adds `claude-reviewed` label to the PR

**Usage:** `/ca-pr-review <PR_NUMBER>` or `/ca-pr-review` (no args = local review against `develop`)

**Output:** `APPROVE` or `REQUEST CHANGES` with all issues listed, each commented on GitHub

---

### 🔀 `/ca-pr-prepare-merge`

**Does:** Reads all human comments on a PR, extracts generalizable coding rules, and opens a PR against `main` updating CLAUDE.md

**Workflow:**

1. Fetches all review comments, issue comments, and review bodies from the PR
2. Filters out bot comments, approvals, and PR-specific feedback
3. Extracts patterns that apply broadly (coding conventions, architecture rules, security practices)
4. Checks existing CLAUDE.md to avoid duplicates
5. Creates a new branch and PR with the CLAUDE.md updates

**Usage:** Run before merging an approved PR: `/ca-pr-prepare-merge <PR_NUMBER>`

**Output:** A new PR against `main` with extracted rules, or a report that no generalizable rules were found

---

## Configuration

The plugin reads `.code-analyzer-config.json` in the project root to customize analysis:

```json
{
  "exclusions": {
    "directories": ["node_modules", "dist", ".next", "build"],
    "files": ["*.lock", "*.log"],
    "patterns": ["**/@generated/**", "**/migrations/**"]
  },

  "dead-code": {
    "enabled": true,
    "skipDependencyCheck": false,
    "skipUnusedExports": false
  },

  "security": {
    "enabled": true,
    "checkSecrets": true,
    "checkInjection": true,
    "secretPatterns": {
      "aws": "AKIA[0-9A-Z]{16}",
      "github": "ghp_[0-9a-zA-Z]{36}"
    }
  }
}
```

**Key settings:**

- `exclusions.directories` — skip these folders in all analyses (node_modules always included)
- `exclusions.patterns` — glob patterns to exclude (e.g., generated code, migrations)
- Per-skill `enabled` flags to skip certain analyses
- `dead-code.skipDependencyCheck` — disable npm audit if project has no package.json
- `security.secretPatterns` — customize regex for secret detection

---

## How it works

Each skill is a standalone SKILL.md with frontmatter metadata and instructions for a Claude Code agent:

- **Single-agent design** — each skill runs ONE sequential analysis (not parallel)
- **Token efficient** — focuses on HIGH/CRITICAL findings only
- **Scope-aware** — respects `$ARGUMENTS` to analyze just one directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Read-only** — analysis skills never modify the target project

## Conventions

- Analysis skills are read-only — they never modify the target project
- Action skills (e.g., `ca-pr-prepare-merge`) may create branches/PRs but only modify instruction files (CLAUDE.md)
- Each SKILL.md stays under 200 lines (optimized for token efficiency)
- All commands use the `ca-` prefix to avoid naming conflicts
- All exclusions respect `.code-analyzer-config.json`
- `node_modules`, `dist`, `.next` are **always** excluded across all skills
