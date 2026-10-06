# Code Sentinel

AI code guardian for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — catches security issues, dead code, and style violations before they reach production. Reviews PRs and learns your team's conventions.

## Installation

### Option 1: Clone to your Claude Code skills directory

```bash
git clone https://github.com/Hatkom-io/code-sentinel.git ~/.claude/skills/code-sentinel
```

### Option 2: Add as a submodule in your project

```bash
git submodule add https://github.com/Hatkom-io/code-sentinel.git .claude/skills/code-sentinel
```

### Option 3: Copy skills directly

Copy the `skills/` folder contents into your project's `.claude/skills/` directory.

After installation, the `/cs-*` commands will be available in Claude Code.

## Commands

| Command                            | Description                                                                                           |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `/cs-security`                     | Scan for security vulnerabilities (OWASP Top 10, secrets, injections)                                 |
| `/cs-dead-code`                    | Find unused packages, orphaned files, dead exports. **High token usage** — pass a path to limit scope |
| `/cs-review`                       | Quick local code review (staged/unstaged changes, no GitHub interaction)                              |
| `/cs-pr-review <PR#>`             | Review a PR, post all comments automatically — CI-ready, no prompts                                   |
| `/cs-pr-merge <PR#>`              | Extract rules from PR comments, create CLAUDE.md PR automatically — CI-ready                          |
| `/cs-conflict [PR#]`              | Resolve merge conflicts — auto-resolves obvious conflicts, interactive for ambiguous ones              |
| `/cs-debug <error\|#issue>`        | Deep debugging — trace root cause; close issue if already fixed                                       |
| `/cs-issue [description] [--auto] [--ready]` | Create GitHub issues from findings or requests — duplicate check, user confirmation or `--auto`; `--ready` queues for the orchestrator |
| `/cs-init [name] [dir]`            | Scaffold a fullstack monorepo (Bun + Turborepo, NestJS + Prisma + PostgreSQL, Next.js + Tailwind, Biome) — asks name, location and ports (checked free), installs, migrates, verifies |
| `/cs-spec [what \| #issue]`         | Specification interview in rounds — design tree, decision check, contention map and parallel plan; lands as an issue the orchestrator can dispatch |
| `/cs-feature <#issue\|desc> [--auto]` | Feature or bug fix from request to pull request — study, plan, approval (or `--auto`), issue, branch, implement, checks, PR |
| `/cs-orchestrator [start\|status\|next\|stop]` | Autonomous fleet — dispatches parallel worker sessions in git worktrees for ready issues, merges green PRs, refills slots |
| `/cs-worker <brief>`               | Worker session started by `/cs-orchestrator` — one issue, one worktree, ownership fence, stops before merge |
| `/cs-perf [path]`                  | Performance analysis: N+1 queries, React re-renders, memory leaks, bundle size                        |
| `/cs-ux-review [url\|focus]`       | UX analysis: friction points, redesign proposals with before/after mockups                            |
| `/cs-seo <path>`                   | SEO analysis from GSC exports — quick wins, problems, meta tag fixes with `--fix` flag                |
| `/cs-analytics [path]`             | Data-driven UX from GA4/GSC — user flows, funnels, behavioral anomalies, Browser MCP flow replay      |
| `/cs-history`                      | Project retrospective — PR history mapped to role portals, weighted effort, product timeline           |
| `/cs-repo`                         | Product completeness audit — page inventory per role, functional vs visual, hardcode detection         |
| `/cs-ux-test <N\|name>`            | Scenario-based UI/UX testing — execute user scenarios via browser, capture screenshots, report issues  |
| `/cs-ux-scenario [PR#\|desc]`      | Generate UX test scenarios from PR, branch diff, or description — saves files for `/cs-ux-test`       |
| `/cs-arch [path\|--audit]`         | Architecture consistency — checks if new code follows project patterns, or audits whole project for drift and proposes unification |
| `/cs-unit-test [PR#\|branch\|commit]` | Retrospective TDD unit test writer — analyzes a fix and writes a unit test that would have caught the bug |
| `/cs-test [PR#\|branch\|commit]`   | Retrospective TDD test writer — classifies the fix (unit/integration/not testable) and writes the appropriate test |

All commands use the `cs-` prefix (code-sentinel) to avoid conflicts with built-in or other plugin commands.

## Usage

```bash
# Security scan (full project)
/cs-security

# Security scan (specific directory)
/cs-security src/auth

# Dead code detection (scoped to reduce token usage)
/cs-dead-code apps/api

# Review local changes
/cs-review

# Review a specific file
/cs-review src/services/user.service.ts

# Review PR #42 (posts all comments automatically, CI-ready)
/cs-pr-review 42

# Extract rules from PR #42 comments into CLAUDE.md (creates PR automatically, CI-ready)
/cs-pr-merge 42

# Resolve merge conflicts for a PR
/cs-conflict 42

# Resolve merge conflicts on current branch
/cs-conflict

# Debug from error message
/cs-debug "TypeError: Cannot read property 'id' of undefined at UserService.ts:45"

# Debug from GitHub issue
/cs-debug #123

# Debug from symptom
/cs-debug "login fails when email contains +"

# Create issues from last analysis
/cs-issue

# Create issue from description
/cs-issue "Login fails when email contains special characters"

# Inspect file and create issues
/cs-issue src/api/handler.ts

# Performance analysis (full project)
/cs-perf

# Performance analysis (specific directory)
/cs-perf src/services

# Performance analysis by category
/cs-perf queries      # N+1 and database issues
/cs-perf react        # React re-renders and hooks
/cs-perf memory       # Memory leaks
/cs-perf bundle       # Bundle size issues

# UX review of a specific page
/cs-ux-review http://localhost:3000/users

# UX review focused on forms
/cs-ux-review forms

# Full UX audit
/cs-ux-review full

# SEO audit from GSC export (local project)
/cs-seo ~/Downloads/sawback.com-Performance-2026-02

# SEO audit with GA4 data
/cs-seo ~/Downloads/gsc-export ~/Downloads/ga4-export

# SEO audit without local project (remote mode)
/cs-seo ~/Downloads/gsc-export --url https://sawback.com

# SEO audit: compare two periods
/cs-seo --compare ~/Downloads/jan-2026 ~/Downloads/feb-2026

# SEO audit with automatic fixes
/cs-seo ~/Downloads/metrics --fix

# Analytics from GA4 export (local project)
/cs-analytics ~/Downloads/ga4-export

# Analytics with GA4 + GSC data
/cs-analytics ~/Downloads/ga4-export ~/Downloads/gsc-export

# Analytics without local project (remote mode — replays flows on live site)
/cs-analytics ~/Downloads/ga4-export --url https://example.com

# Analytics: scan current directory for CSV files
/cs-analytics

# Project history — generate retrospective from PR data + status report
/cs-history

# Project history — specify custom status report path
/cs-history docs/custom-status.md

# Repo analysis — audit product completeness per role portal
/cs-repo

# Repo analysis — specify roles to analyze
/cs-repo owner banker charter

# Run a UX test scenario by number
/cs-ux-test 1

# Generate UX scenarios from a PR
/cs-ux-scenario 42

# Generate UX scenarios from current branch changes
/cs-ux-scenario

# Generate UX scenarios from a description
/cs-ux-scenario "checkout with promo code"

# Check if new code follows project architecture
/cs-arch src/features/payments

# Audit entire project for architectural drift
/cs-arch

# Write a unit test for a fix in PR #42
/cs-unit-test 42

# Scaffold a new fullstack project (asks name, location, api/web/db ports)
/cs-init
/cs-init acme ~/dev/acme

# Specify a feature (interview → parallel plan → issue), or discover what to specify
/cs-spec "Users can export their data"
/cs-spec

# Implement a feature: plan → approval → issue → branch → PR
/cs-feature "Add CSV export to the reports page"

# Implement an existing issue fully autonomously
/cs-feature #57 --auto

# Queue work for the orchestrator
/cs-issue "Rate-limit the login endpoint" --auto --ready

# Run the fleet unattended (needs tmux, gh, python3; start it on Remote Control)
/cs-orchestrator start
/cs-orchestrator status
/cs-orchestrator stop i57

# Write a test (unit or integration) for a fix in PR #42
/cs-test 42

# Write a test for current branch changes
/cs-test
```

## Configuration

Create `.code-analyzer-config.json` in the project root to customize analysis:

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
  },
  "orchestrator": {
    "base": "develop",
    "maxSlots": 5,
    "readyLabel": "cs:ready",
    "install": "bun install",
    "checks": ["bun run lint", "bun run test", "bun run build"],
    "mergeMethod": "merge",
    "autoMerge": true
  }
}
```

Every `orchestrator` key is optional — base defaults to origin's default branch, install and checks are detected from the project.

## Autonomous fleet

`/cs-orchestrator` turns a GitHub issue queue into merged pull requests without supervision:

1. **Queue** — open issues labelled `cs:ready` (specify them with `/cs-spec`, or file them with `/cs-issue --auto --ready`). A `## Parallel plan` table in the issue splits it into a wave of slots. `Depends on #N` lines order them; `cs:needs-person` or a `Gate:` line holds them.
2. **Dispatch** — one `claude` session per issue (`tmux` session `cs-<slot>`, Remote Control on), each in its own git worktree next to the repository, on its own branch, with a model chosen per slot (Opus for decisions, Sonnet for execution).
3. **Fence** — each brief carries `owns:` / `never:` globs; `fence.py` runs as a `PreToolUse` hook (passed with `--settings`, nothing committed) and refuses writes outside them, including shell writes it can parse.
4. **Channel** — workers report through `.orchestrator-reply.md`; `watch.sh` under `Monitor` wakes the orchestrator on PR, reply, idle, dead-session and quota events.
5. **Merge & refill** — green, mergeable PRs are merged by the orchestrator, worktrees removed, and the next ready issue dispatched in the same pass. Dead workers are resumed in their worktree.

Requirements: `git` ≥ 2.31, `gh` (authenticated), `tmux` ≥ 3.2, `python3`, `claude` on `PATH`.

## Confirmation UX

All user confirmations use **interactive selectors** — no typing `yes` or `no`, just pick from a list.

**Bulk selection (findings with severity):**

| Option            | What it does           |
| ----------------- | ---------------------- |
| **All**           | Process every item     |
| **Critical only** | Only CRITICAL severity |
| **High+**         | CRITICAL + HIGH        |
| **None**          | Skip                   |

In "Other" you can type:

- `1 3` — only items #1 and #3
- `!2 4` — all EXCEPT #2 and #4

**Single items:** **Send** / **Edit** selector before each GitHub post.

## How it works

Each skill is a standalone `SKILL.md` with frontmatter metadata and instructions for a Claude Code agent:

- **Single-agent design** — each skill runs one sequential analysis, not parallel (the exception is `/cs-orchestrator`, whose whole job is parallel worker sessions)
- **Token efficient** — prioritizes HIGH/CRITICAL findings; lower-severity issues are included where appropriate
- **Scope-aware** — pass a path as argument to analyze a specific directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Self-contained** — every skill has all rules, benchmarks, and patterns inlined — no external file reads at runtime
- **Read-only** — analysis skills never modify the target project
- **MCP-aware** — offers to install missing MCP servers when they would enhance the analysis

## Project structure

```
skills/
  _shared/style-rules.md                — style rules reference (inlined into each skill)
  _shared/confirmation-flow.md          — confirmation UX patterns reference (inlined into each skill)
  _shared/seo-references.md             — CTR benchmarks, meta tag patterns reference (inlined into each skill)
  _shared/severity-levels.md            — severity classification reference (inlined into pr-review skills)
  security/SKILL.md                     — /cs-security
  dead-code/SKILL.md                    — /cs-dead-code
  review/SKILL.md                       — /cs-review
  pr-review/SKILL.md                    — /cs-pr-review
  pr-merge/SKILL.md                     — /cs-pr-merge
  conflict/SKILL.md                     — /cs-conflict
  debug/SKILL.md                        — /cs-debug
  issue/SKILL.md                        — /cs-issue
  perf/SKILL.md                         — /cs-perf
  ux-review/SKILL.md                    — /cs-ux-review
  seo/SKILL.md                          — /cs-seo
  analytics/SKILL.md                    — /cs-analytics
  history/SKILL.md                      — /cs-history
  repo/SKILL.md                         — /cs-repo
  ux-test/SKILL.md                      — /cs-ux-test
  ux-test/scenario-template.md          — scenario format template
  ux-scenario/SKILL.md                  — /cs-ux-scenario
  arch/SKILL.md                         — /cs-arch
  unit-test/SKILL.md                    — /cs-unit-test
  test/SKILL.md                         — /cs-test
  init/SKILL.md                         — /cs-init
  init/scaffold.sh                      — generator (placeholder substitution, refuses non-empty targets)
  init/template/                        — the fullstack monorepo template
  spec/SKILL.md                         — /cs-spec
  feature/SKILL.md                      — /cs-feature
  worker/SKILL.md                       — /cs-worker
  orchestrator/SKILL.md                 — /cs-orchestrator
  orchestrator/scripts/                 — dispatch.sh, watch.sh, fence.py (+ fence_test.py) and launch pre-flight helpers
CLAUDE.md                              — internal project instructions
README.md                              — this file
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated (for PR/issue commands)
- Git repository initialized in the target project

## Recommended MCP Servers

For enhanced analysis accuracy, install these optional MCP servers:

| MCP Server     | Install Command                                                                                     | Used By                                      |
| -------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **Puppeteer**  | `claude mcp add puppeteer --scope user -- npx -y @modelcontextprotocol/server-puppeteer`    | `/cs-ux-review`, `/cs-ux-test`, `/cs-seo`, `/cs-analytics`  |
| **Biome**      | Not yet available on npm — see [biomejs/biome#6017](https://github.com/biomejs/biome/discussions/6017) | `/cs-review`, `/cs-pr-review`, `/cs-debug`  |
| **TypeScript** | Not yet available on npm — use VS Code `getDiagnostics` as fallback            | `/cs-dead-code`, `/cs-perf`, `/cs-debug`     |

Skills will offer to install missing MCPs when they would improve analysis quality.

## License

MIT

## Release Notes

See [RELEASE.md](RELEASE.md) for version history and changelog.
