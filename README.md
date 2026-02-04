# Code Sentinel

AI code guardian for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — catches security issues, dead code, and style violations before they reach production. Reviews PRs and learns your team's conventions.

## Installation

### Option 1: Clone to your Claude Code skills directory

```bash
git clone https://github.com/your-org/claude-code-analyzer-plugin.git ~/.claude/skills/code-sentinel
```

### Option 2: Add as a submodule in your project

```bash
git submodule add https://github.com/your-org/claude-code-analyzer-plugin.git .claude/skills/code-sentinel
```

### Option 3: Copy skills directly

Copy the `skills/` folder contents into your project's `.claude/skills/` directory.

After installation, the `/ca-*` commands will be available in Claude Code.

## Commands

| Command                      | Description                                                                                           |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| `/ca-security`               | Scan for security vulnerabilities (OWASP Top 10, secrets, injections)                                 |
| `/ca-dead-code`              | Find unused packages, orphaned files, dead exports. **High token usage** — pass a path to limit scope |
| `/ca-code-review`            | Quick local code review (staged/unstaged changes, no GitHub interaction)                              |
| `/ca-pr-review <PR#>`        | Review a PR with CI check, post inline comments, create issues for critical findings, trigger debug   |
| `/ca-pr-prepare-merge <PR#>` | Extract rules from PR comments, check merge readiness, open PR updating CLAUDE.md                     |
| `/ca-debug <error\|#issue>`  | Deep debugging — trace root cause; close issue if already fixed                                       |
| `/ca-issue [description]`    | Create GitHub issues from analysis findings — with duplicate check and user confirmation              |
| `/ca-perf [path]`            | Performance analysis: N+1 queries, React re-renders, memory leaks, bundle size                        |
| `/ca-ux-review [url\|focus]` | UX analysis: friction points, redesign proposals with before/after mockups                            |

All commands use the `ca-` prefix (code-sentinel) to avoid conflicts with built-in or other plugin commands.

## Usage

```bash
# Security scan (full project)
/ca-security

# Security scan (specific directory)
/ca-security src/auth

# Dead code detection (scoped to reduce token usage)
/ca-dead-code apps/api

# Review local changes
/ca-code-review

# Review a specific file
/ca-code-review src/services/user.service.ts

# Review PR #42 and post inline comments on GitHub
/ca-pr-review 42

# Extract rules from PR #42 comments into CLAUDE.md
/ca-pr-prepare-merge 42

# Debug from error message
/ca-debug "TypeError: Cannot read property 'id' of undefined at UserService.ts:45"

# Debug from GitHub issue
/ca-debug #123

# Debug from symptom
/ca-debug "login fails when email contains +"

# Create issues from last analysis
/ca-issue

# Create issue from description
/ca-issue "Login fails when email contains special characters"

# Inspect file and create issues
/ca-issue src/api/handler.ts

# Performance analysis (full project)
/ca-perf

# Performance analysis (specific directory)
/ca-perf src/services

# Performance analysis by category
/ca-perf queries      # N+1 and database issues
/ca-perf react        # React re-renders and hooks
/ca-perf memory       # Memory leaks
/ca-perf bundle       # Bundle size issues

# UX review of a specific page
/ca-ux-review http://localhost:3000/users

# UX review focused on forms
/ca-ux-review forms

# Full UX audit
/ca-ux-review full
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
  }
}
```

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

- **Single-agent design** — each skill runs one sequential analysis, not parallel
- **Token efficient** — prioritizes HIGH/CRITICAL findings; lower-severity issues are included where appropriate
- **Scope-aware** — pass a path as argument to analyze a specific directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Read-only** — analysis skills never modify the target project
- **MCP-aware** — offers to install missing MCP servers when they would enhance the analysis

## Project structure

```
skills/
  _shared/style-rules.md          — shared style rules (referenced by review skills)
  _shared/confirmation-flow.md    — shared confirmation UX patterns (interactive selectors)
  security/SKILL.md               — /ca-security
  dead-code/SKILL.md         — /ca-dead-code
  code-review/SKILL.md       — /ca-code-review
  pr-review/SKILL.md         — /ca-pr-review
  pr-prepare-merge/SKILL.md  — /ca-pr-prepare-merge
  debug/SKILL.md             — /ca-debug
  issue/SKILL.md             — /ca-issue
  perf/SKILL.md              — /ca-perf
  ux-review/SKILL.md         — /ca-ux-review
CLAUDE.md                    — internal project instructions
README.md                    — this file
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated (for PR/issue commands)
- Git repository initialized in the target project

## Recommended MCP Servers

For enhanced analysis accuracy, install these optional MCP servers:

| MCP Server     | Install Command                                                                                     | Used By                                         |
| -------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Biome**      | `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-biome --client claude`      | `/ca-code-review`, `/ca-pr-review`, `/ca-debug` |
| **TypeScript** | `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-typescript --client claude` | `/ca-dead-code`, `/ca-perf`, `/ca-debug`        |
| **Puppeteer**  | `bunx @anthropic-ai/mcp-install@latest install puppeteer --client claude`                           | `/ca-ux-review`                                 |

Skills will offer to install missing MCPs when they would improve analysis quality.

## License

MIT

## Release Notes

See [RELEASE.md](RELEASE.md) for version history and changelog.
