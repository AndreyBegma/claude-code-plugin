# Code Sentinel

AI code guardian for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — catches security issues, dead code, and style violations before they reach production. Reviews PRs and learns your team's conventions.

## Installation

```bash
claude plugin add claude-code-analyzer-plugin
```

## Commands

| Command                      | Description                                                                                           |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| `/ca-security`               | Scan for security vulnerabilities (OWASP Top 10, secrets, injections)                                 |
| `/ca-dead-code`              | Find unused packages, orphaned files, dead exports. **High token usage** — pass a path to limit scope |
| `/ca-code-review`            | Quick local code review (staged/unstaged changes, no GitHub interaction)                              |
| `/ca-pr-review <PR#>`        | Review a PR and post inline comments on GitHub                                                        |
| `/ca-pr-prepare-merge <PR#>` | Extract generalizable rules from PR comments and open a PR updating CLAUDE.md                         |

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

## How it works

Each skill is a standalone `SKILL.md` with frontmatter metadata and instructions for a Claude Code agent:

- **Single-agent design** — each skill runs one sequential analysis, not parallel
- **Token efficient** — prioritizes HIGH/CRITICAL findings; lower-severity issues are included where appropriate
- **Scope-aware** — pass a path as argument to analyze a specific directory
- **Exclusion-aware** — reads `.code-analyzer-config.json` to skip files/folders
- **Read-only** — analysis skills never modify the target project

## Project structure

```
skills/
  security/SKILL.md          — /ca-security
  dead-code/SKILL.md         — /ca-dead-code
  code-review/SKILL.md       — /ca-code-review
  pr-review/SKILL.md         — /ca-pr-review
  pr-prepare-merge/SKILL.md  — /ca-pr-prepare-merge
.code-analyzer-config.json   — default configuration
.claude-plugin/
  plugin.json                — plugin manifest
  marketplace.json           — marketplace metadata
CLAUDE.md                    — internal project instructions
```

## License

MIT
