# Code Sentinel

**A Claude Code plugin that reviews your code, files the issues, and runs a fleet of agents that turns those issues into merged pull requests.**

[![Discord](https://img.shields.io/badge/Discord-join%20the%20community-5865F2?logo=discord&logoColor=white)](https://discord.gg/mkQARkBs4C)

Code Sentinel adds 25 `/cs-*` skills to [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Some are
analysis skills: security, dead code, performance, architecture drift, UX and SEO. Others work with GitHub: they
review pull requests and post the comments, extract team rules from review threads into `CLAUDE.md`, and resolve
merge conflicts. The last group runs delivery: `/cs-spec` turns an idea into an issue a machine can execute, and
`/cs-orchestrator` dispatches parallel Claude Code workers, each in its own git worktree, then merges the pull
requests that come back green.

**Who it is for:** developers who already use Claude Code and want repeatable review, audits and unattended issue
delivery on their own GitHub repositories, without a hosted service.

[AgentDock](https://github.com/AndreyBegma/AgentDock) is a web control plane for fleets that this orchestrator
drives.

## Install

The repository is a Claude Code plugin marketplace (`.claude-plugin/marketplace.json`). In Claude Code:

```text
/plugin marketplace add AndreyBegma/code-sentinel-skills
/plugin install code-sentinel@code-sentinel
```

Skills are then invoked as `/code-sentinel:cs-<name>`, for example `/code-sentinel:cs-security`. This README uses
the short `/cs-<name>` form, which is what a copied skill (below) is called.
The plugin also installs one `PreToolUse` hook ([`hooks/kill_guard.py`](hooks/kill_guard.py)). It refuses
`pkill`, `killall` and `kill` calls that do not name literal PIDs, so an agent cannot stop processes that belong to
other projects.

Without the plugin system, copy `skills/` into a project's `.claude/skills/` (or `~/.claude/skills/`).

Requirements:

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [GitHub CLI](https://cli.github.com/) (`gh`), authenticated: needed by the PR and issue skills
- a git repository in the target project
- for `/cs-orchestrator`: `git` 2.31+, `tmux` 3.2+, `python3`, and `claude` on `PATH`

## Skills

**Analyse**

| Command | What it does |
|---|---|
| `/cs-security [path]` | Scan for vulnerabilities: OWASP Top 10, exposed secrets, injections, auth bypass |
| `/cs-dead-code [path]` | Find unused packages, orphaned files and dead exports. **High token usage**, so pass a path to limit scope |
| `/cs-perf [path\|category]` | N+1 queries, React re-renders, memory leaks, bundle size |
| `/cs-arch [path\|--audit]` | Check that new code follows the project's patterns, or audit the project for drift |
| `/cs-repo [roles]` | Product completeness audit: pages per role, functional or mockup, hard-coded data |
| `/cs-history [status-report]` | Project retrospective: PR history mapped to role portals, weighted effort, timeline |

**Review and fix**

| Command | What it does |
|---|---|
| `/cs-review [path]` | Quick local review of staged and unstaged changes; no GitHub interaction |
| `/cs-pr-review <PR#>` | Review a pull request and post every comment; CI-ready, no prompts |
| `/cs-pr-merge <PR#>` | Extract rules from PR comments and open a pull request that updates `CLAUDE.md`; CI-ready |
| `/cs-conflict [PR#]` | Resolve merge conflicts: obvious ones automatically, ambiguous ones interactively |
| `/cs-debug <error\|#issue>` | Trace a root cause from an error, stack trace, symptom or issue; closes the issue if it is already fixed |
| `/cs-unit-test [PR#\|branch\|commit]` | Write the unit test that would have caught a fixed bug |
| `/cs-test [PR#\|branch\|commit]` | Classify a fix (unit, integration, not testable) and write the matching test |

**UX, SEO and analytics**

| Command | What it does |
|---|---|
| `/cs-ux-review [url\|focus]` | Friction points and redesign proposals with before and after mockups |
| `/cs-ux-scenario [PR#\|desc]` | Generate UX test scenarios from a PR, a branch diff or a description |
| `/cs-ux-test <N\|name>` | Run a scenario step by step in a browser, with screenshots and a report |
| `/cs-seo <path>` | SEO audit from Google Search Console exports; `--fix` applies meta tag fixes |
| `/cs-analytics [path]` | User flows, funnels and anomalies from GA4 and GSC exports, traced to code |

**Plan and deliver**

| Command | What it does |
|---|---|
| `/cs-issue [desc] [--auto] [--ready]` | Create GitHub issues from findings or requests, with a duplicate check; `--ready` queues them for the orchestrator |
| `/cs-spec [what\|#issue]` | Specification interview in rounds: design tree, decision check, contention map and parallel plan; lands as a dispatchable issue |
| `/cs-estimate <desc\|#issue\|--queue>` | Evidence-based estimate for the agent fleet, a team, or both compared; PERT ranges, split-or-spike, calibration from merged PRs; `--post` adds a comment and a `size:` label |
| `/cs-feature <#issue\|desc> [--auto]` | From request to pull request: study, plan, approval (or `--auto`), issue, branch, implementation, checks, PR |
| `/cs-orchestrator [start\|status\|next\|stop]` | Unattended fleet: parallel worker sessions in git worktrees for ready issues, merges green PRs, refills slots |
| `/cs-worker <brief>` | What a dispatched session runs: one issue, one worktree, an ownership fence; stops before merge |
| `/cs-init [name] [dir]` | Scaffold a fullstack monorepo (Bun + Turborepo, NestJS + Prisma + PostgreSQL, Next.js + Tailwind, Biome), verified end to end |

## Usage

```bash
# Audits, scoped to a path to save tokens
/cs-security src/auth
/cs-dead-code apps/api
/cs-perf queries                     # also: react, memory, bundle
/cs-arch src/features/payments

# Review and fix
/cs-review
/cs-pr-review 42                     # posts the comments
/cs-pr-merge 42                      # opens a CLAUDE.md pull request
/cs-conflict 42
/cs-debug "TypeError: Cannot read property 'id' of undefined at UserService.ts:45"
/cs-debug #123
/cs-test 42

# UX and SEO
/cs-ux-review http://localhost:3000/users
/cs-ux-scenario "checkout with promo code"
/cs-ux-test 1
/cs-seo ~/Downloads/gsc-export --url https://example.com
/cs-seo --compare ~/Downloads/jan-2026 ~/Downloads/feb-2026
/cs-analytics ~/Downloads/ga4-export ~/Downloads/gsc-export

# Plan and deliver
/cs-spec "Users can export their data"
/cs-estimate #57 --post
/cs-estimate --queue
/cs-feature "Add CSV export to the reports page"
/cs-feature #57 --auto
/cs-issue "Rate-limit the login endpoint" --auto --ready

# Run the fleet unattended
/cs-orchestrator start
/cs-orchestrator status
/cs-orchestrator stop i57

# New project
/cs-init acme ~/dev/acme
```

## Autonomous fleet

`/cs-orchestrator` turns a GitHub issue queue into merged pull requests without supervision:

1. **Queue** — open issues labelled `cs:ready` (specify them with `/cs-spec`, or file them with `/cs-issue --auto --ready`). A `## Parallel plan` table in the issue splits it into a wave of slots. `Depends on #N` lines order them; `cs:needs-person` or a `Gate:` line holds them.
2. **Dispatch** — one `claude` session per issue (`tmux` session `cs-<slot>`, Remote Control on), each in its own git worktree next to the repository, on its own branch, with a model chosen per slot (Opus for decisions, Sonnet for execution).
3. **Fence** — each brief carries `owns:` / `never:` globs; `fence.py` runs as a `PreToolUse` hook (passed with `--settings`, nothing committed) and refuses writes outside them, including shell writes it can parse.
4. **Channel** — workers report through `.orchestrator-reply.md`; `watch.sh` under `Monitor` wakes the orchestrator on PR, reply, idle, dead-session and quota events.
5. **Merge & refill** — green, mergeable PRs are merged by the orchestrator, worktrees removed, and the next ready issue dispatched in the same pass. Dead workers are resumed in their worktree.

Requirements: `git` ≥ 2.31, `gh` (authenticated), `tmux` ≥ 3.2, `python3`, `claude` on `PATH`.

The orchestrator also writes a machine-readable event log and state snapshot (`events.jsonl`, `state.json`)
inside `.git`; the contract is in [skills/orchestrator/EVENTS.md](skills/orchestrator/EVENTS.md). With
`OTEL_EXPORTER_OTLP_ENDPOINT` set, every worker sends OpenTelemetry tagged with its slot and issue. The full
behaviour, including the `specDir` option for specifications kept in another repository, is in
[skills/orchestrator/SKILL.md](skills/orchestrator/SKILL.md).

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

## How it works

Each skill is a standalone `SKILL.md` with frontmatter metadata and instructions for a Claude Code agent:

- **Single-agent design** — each skill runs one sequential analysis, not parallel (the exception is `/cs-orchestrator`, whose whole job is parallel worker sessions)
- **Token efficient** — prioritizes HIGH/CRITICAL findings; lower-severity issues are included where appropriate
- **Scope-aware** — pass a path as argument to analyze a specific directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Self-contained** — every skill has all rules, benchmarks, and patterns inlined — no external file reads at runtime
- **Read-only** — analysis skills never modify the target project
- **MCP-aware** — offers to install missing MCP servers when they would enhance the analysis

### Confirmations

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

## Recommended MCP servers

For enhanced analysis accuracy, install these optional MCP servers:

| MCP Server     | Install Command                                                                                     | Used By                                      |
| -------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **Puppeteer**  | `claude mcp add puppeteer --scope user -- npx -y @modelcontextprotocol/server-puppeteer`    | `/cs-ux-review`, `/cs-ux-test`, `/cs-seo`, `/cs-analytics`  |
| **Biome**      | Not yet available on npm — see [biomejs/biome#6017](https://github.com/biomejs/biome/discussions/6017) | `/cs-review`, `/cs-pr-review`, `/cs-debug`  |
| **TypeScript** | Not yet available on npm — use VS Code `getDiagnostics` as fallback            | `/cs-dead-code`, `/cs-perf`, `/cs-debug`     |

Skills will offer to install missing MCPs when they would improve analysis quality.

## Repository layout

```
.claude-plugin/        plugin and marketplace manifests
hooks/                 kill_guard.py, the PreToolUse guard installed with the plugin
skills/<name>/SKILL.md one directory per skill
skills/_shared/        style, severity, confirmation and SEO references (inlined into skills)
skills/init/           scaffold.sh and the monorepo template
skills/orchestrator/   SKILL.md, EVENTS.md, and scripts/ (dispatch.sh, watch.sh, fence.py, emit.py, spec_dir.py, tests)
```

Contributor conventions are in [CLAUDE.md](CLAUDE.md). Version history is in [RELEASE.md](RELEASE.md).

## License

MIT — see [LICENSE](LICENSE).
