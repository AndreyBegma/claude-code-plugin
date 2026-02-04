# Code Sentinel

AI code guardian — catches security issues, dead code, and style violations. Reviews PRs and learns your team's conventions.

All commands use the `ca-` prefix (code-sentinel) to avoid conflicts with built-in or other plugin commands.

## Structure

```
skills/
  _shared/style-rules.md          — Shared style rules (referenced by code-review and pr-review)
  _shared/confirmation-flow.md    — Shared confirmation UX patterns (AskUserQuestion selectors)
  security/SKILL.md               — /ca-security — Security vulnerability scanner (OWASP Top 10, secrets, injections)
  dead-code/SKILL.md         — /ca-dead-code — Dead code detector (unused exports, files, dependencies)
  code-review/SKILL.md       — /ca-code-review — Local code review for style and correctness
  pr-review/SKILL.md         — /ca-pr-review — Review a PR with CI status check, post inline comments on GitHub
  pr-prepare-merge/SKILL.md  — /ca-pr-prepare-merge — Extract rules from PR comments, check merge readiness, update CLAUDE.md via PR
  debug/SKILL.md             — /ca-debug — Deep debugger: trace root cause from error, stack trace, or symptom
  issue/SKILL.md             — /ca-issue — Create GitHub issues from analysis findings with user confirmation
  perf/SKILL.md              — /ca-perf — Performance analyzer: N+1 queries, re-renders, memory leaks, bundle size
  ux-review/SKILL.md         — /ca-ux-review — UX analysis: friction points, redesign proposals, before/after mockups
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

**Does:** Quick local code review for style and correctness — project-aware via CLAUDE.md and project-local skills

**Workflow:**

1. Reads project `CLAUDE.md` and project-local skills (`.claude/skills/`) for project-specific rules
2. Gets diff (staged/unstaged changes)
3. Reviews: correctness, security, style, patterns
4. Severity: CRITICAL / HIGH / MEDIUM / LOW

**Usage:** `/ca-code-review` (all local changes) or `/ca-code-review <path>` (specific file/directory)

**Output:** Summary + Issues list + Verdict (APPROVE / REQUEST CHANGES)

**Difference from `/ca-pr-review`:** `/ca-code-review` is a lightweight local review without GitHub interaction. `/ca-pr-review` posts inline comments on GitHub.

---

### 👀 `/ca-pr-review`

**Does:** Reviews a PR (or current branch) for correctness, security, style, and performance — posts inline comments directly on GitHub

**Workflow:**

1. Fetches PR metadata, diff, and commit SHA
2. **Checks CI status** — if failed, shows errors and offers to view logs before reviewing
3. Reads project `CLAUDE.md` and project-local skills (`.claude/skills/`) for project-specific rules
4. Checks existing PR comments — if previously reported issues are now fixed, offers to reply "✅ Fixed"
5. Reviews all changed files (correctness, security, style, performance, types)
6. Posts inline comments via `gh api` with severity labels
7. Adds `claude-reviewed` label to the PR
8. **Offers to create GitHub issues** for all findings (so they don't get lost in PR comments)
9. **Offers to run `/ca-debug`** for CRITICAL issues (full pipeline: Review → Issue → Debug)

**Usage:** `/ca-pr-review <PR_NUMBER>` or `/ca-pr-review` (no args = local review against base branch, detected automatically with `main` or `develop` as fallback)

**Output:** `APPROVE` or `REQUEST CHANGES` with all issues listed, each commented on GitHub

---

### 🔀 `/ca-pr-prepare-merge`

**Does:** Reads all human comments on a PR, extracts generalizable coding rules, and opens a PR against the source PR's branch updating CLAUDE.md

**Workflow:**

1. Fetches all review comments, issue comments, and review bodies from the PR
2. Filters out bot comments, approvals, and PR-specific feedback
3. Extracts patterns that apply broadly (coding conventions, architecture rules, security practices)
4. Checks existing CLAUDE.md to avoid duplicates
5. Creates a new branch and PR with the CLAUDE.md updates
6. Adds `claude-rules` label to the created PR

**Usage:** Run before merging an approved PR: `/ca-pr-prepare-merge <PR_NUMBER>`

**Output:** A new PR against the source PR's branch with extracted rules (labeled `claude-rules`), or a report that no generalizable rules were found

---

### 🐛 `/ca-debug`

**Does:** Deep bug analysis — traces root cause through call chain and data flow with advanced debugging techniques

**Workflow:**

1. Parses input (error message, stack trace, issue number, symptom description)
2. Gathers project context (framework, structure, conventions)
3. Traces the call chain backwards from the error point to the origin
4. Analyzes data flow: where the value was created, mutated, and broke
5. Applies advanced techniques:
   - **Git Bisect** — binary search for the exact breaking commit
   - **5 Whys** — drill down to the true root cause
   - **Hypothesis-Driven** — systematically test and refute hypotheses
   - **Flaky Bug Detection** — identify timing issues, race conditions, non-deterministic code
   - **Dependency Debugging** — check lock files, version mismatches, breaking changes
   - **Logging Injection Points** — suggest strategic places to add debug logging
6. Checks test coverage and suggests a regression test
7. If bug is already fixed: offers to close the GitHub issue or reply to PR comment with "✅ Fixed"

**Usage:** `/ca-debug "TypeError: Cannot read property 'id' of undefined at UserService.ts:45"` or `/ca-debug #123` (GitHub issue)

**Output:** Root cause diagnosis with call chain, data flow, 5 Whys analysis, suggested fix, and regression test

---

### 📋 `/ca-issue`

**Does:** Creates GitHub issues from analysis findings — with user confirmation before each issue

**Workflow:**

1. Collects findings from previous analysis (or from description/file)
2. Checks for duplicates via `gh issue list --search`
3. Shows a preview and asks for confirmation via interactive selector (with severity shortcuts)
4. Creates confirmed issues with labels and code context

**Usage:** `/ca-issue` (after analysis) or `/ca-issue "bug description"` or `/ca-issue src/file.ts`

**Output:** Created issues with numbers + report of skipped items (duplicates, declined)

---

### ⚡ `/ca-perf`

**Does:** Analyzes code for performance anti-patterns — N+1 queries, unnecessary re-renders, memory leaks, bundle bloat

**Categories:**

1. **Database/Queries:** N+1 patterns, missing includes, unbounded queries, missing pagination
2. **React Performance:** Unnecessary re-renders, missing memoization, context misuse, expensive computations in render
3. **Memory Leaks:** Uncleared intervals, missing cleanup, subscriptions not unsubscribed, event listeners not removed
4. **Bundle Size:** Heavy dependencies, importing entire libraries, dev deps in production, missing code splitting
5. **API/Network:** Sequential requests that could be parallel, missing caching, over/under-fetching

**Usage:** `/ca-perf` (full project) or `/ca-perf src/api` (directory) or `/ca-perf queries` (category)

**Output:** Findings table + detailed issues with code examples and fixes

---

### 🎨 `/ca-ux-review`

**Does:** Analyzes UI for friction points, proposes redesigns with before/after ASCII mockups, measures impact in clicks/time saved

**Workflow:**

1. Gathers project context (framework, UI library, app type)
2. Captures current state (screenshots via Puppeteer/Playwright MCP if available, otherwise code analysis)
3. Identifies friction: step bloat, cognitive load, keyboard hostility, feedback gaps, inconsistency
4. Proposes redesigns with before/after mockups and impact metrics
5. Outputs prioritized roadmap (quick wins vs bigger bets)

**Usage:** `/ca-ux-review http://localhost:3000/users` (URL) or `/ca-ux-review forms` (focus area) or `/ca-ux-review full` (complete audit)

**Output:** Friction score + redesign proposals with ASCII mockups + prioritized roadmap

**Enhanced with:** Puppeteer/Playwright/Browserbase MCP for live screenshots and interaction recording

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
    "skipUnusedExports": false,
    "skipEnvironmentVars": false,
    "minFilesToAnalyze": 10
  },

  "security": {
    "enabled": true,
    "checkSecrets": true,
    "checkInjection": true,
    "checkAuthentication": true,
    "checkInputValidation": true,
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
- `dead-code.skipDependencyCheck` — skip unused dependency scanning (e.g., if project has no package.json)
- `dead-code.skipUnusedExports` — skip orphaned export detection
- `dead-code.skipEnvironmentVars` — skip environment variable usage analysis
- `dead-code.minFilesToAnalyze` — minimum file count threshold before analysis runs
- `security.checkAuthentication` — enable/disable auth pattern checks
- `security.checkInputValidation` — enable/disable input validation checks
- `security.secretPatterns` — customize regex for secret detection

---

## Recommended MCP Servers

For enhanced analysis, install these MCP servers:

### Biome MCP

Runs Biome linter and returns structured diagnostics (no CLI parsing needed).

**Benefits for `/ca-code-review`, `/ca-pr-review`, and `/ca-debug`:**

- Get lint errors as structured JSON
- Exact error locations with rule IDs
- Auto-detect Biome config from project
- (`/ca-debug`) Lint violations near the error point often correlate with the root cause

**Install:** `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-biome --client claude`

### TypeScript MCP

Provides TypeScript compiler diagnostics and type information.

**Benefits for `/ca-dead-code`, `/ca-perf`, and `/ca-debug`:**

- Find unused exports via `findAllReferences()`
- Get compiler errors and warnings
- Detect unreachable code paths
- Type-aware dead code detection
- (`/ca-debug`) Trace call chains via `findAllReferences()`, check real types at error point via `getTypeAtPosition()`

**Install:** `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-typescript --client claude`

### Puppeteer MCP

Provides browser automation for capturing screenshots and interacting with UI.

**Benefits for `/ca-ux-review`:**

- Capture screenshots of current UI state
- Record user journeys and count interactions
- Test responsive behavior on different viewports
- Verify keyboard navigation support

**Install:** `bunx @anthropic-ai/mcp-install@latest install puppeteer --client claude`

### MCP Availability — Offer to Install

When a skill checks for an MCP server and it is **not available**, offer the user to install it using `AskUserQuestion` (Binary Choice — see `_shared/confirmation-flow.md`):

```
⚠️ [MCP Name] is not available. It enhances this analysis with [brief benefit].
```

Options:
| Option | Description |
|--------|-------------|
| **Install (Recommended)** | Run `bunx @anthropic-ai/mcp-install@latest install [package] --client claude` |
| **Skip** | Continue without it (reduced accuracy) |

After installation, restart the analysis to pick up the new MCP server.

---

## How it works

Each skill is a standalone SKILL.md with frontmatter metadata and instructions for a Claude Code agent:

- **Single-agent design** — each skill runs ONE sequential analysis (not parallel)
- **Token efficient** — prioritizes HIGH/CRITICAL findings; lower-severity issues are included where appropriate
- **Scope-aware** — respects `$ARGUMENTS` to analyze just one directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Read-only** — analysis skills never modify the target project

## Conventions

- Analysis skills are read-only — they never modify the target project
- Action skills (e.g., `ca-pr-prepare-merge`) may create branches/PRs but only modify instruction files (CLAUDE.md)
- All commands use the `ca-` prefix to avoid naming conflicts
- All exclusions respect `.code-analyzer-config.json`
- `node_modules`, `dist`, `.next`, `build` are **always** excluded across all skills

### User Confirmation UX

All confirmations use **interactive selectors** (`AskUserQuestion` tool), not text prompts. See `_shared/confirmation-flow.md` for full spec.

**Bulk selection (findings with severity):**

- Options: **All** / **Critical only** / **High+** / **None**
- "Other" field accepts: numbers (`1 3`), inverted selection (`!2 4`), severity keywords (`critical`, `high+`)

**Bulk selection (items without severity):**

- Options: **All** / **None**
- "Other" field accepts: numbers (`1 3`), inverted selection (`!2`)

**Single-item confirmation:** **Send** / **Edit**

**Binary choice:** **Yes** / **No** (with contextual descriptions)
