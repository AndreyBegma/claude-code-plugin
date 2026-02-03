# Release Notes

## v1.4.3 (2026-02-03)

### New Features

- **Resolved issues detection in PR review** — `/ca-pr-review` now checks existing PR comments and offers to reply "✅ Fixed" when previously reported issues are resolved
- **Auto-close fixed GitHub issues** — `/ca-debug` detects if a bug is already fixed and offers to close the issue with a comment
- **Edit option in confirmations** — all skills now support `edit` option in confirmation prompts (yes / pick / edit / no) to modify lists before proceeding

### Improvements

- Updated documentation in CLAUDE.md and README.md to reflect new features

---

## v1.4.2 (2026-02-03)

### Fixes

- Fixed shell operator parsing issues in SKILL.md files
- Removed backticks from style rules that were being misinterpreted as bash commands

---

## v1.4.1 (2026-02-03)

### Fixes

- Fixed `gh api` command formatting — now single-line with examples
- Fixed base branch detection — checks for `main` before falling back to `develop`
- Fixed label creation commands — uses `--force` flag instead of shell operators

### Improvements

- Added proper installation instructions (clone, submodule, copy)
- Added Requirements section (Claude Code, gh CLI, git)
- Added CLAUDE.md template for `ca-pr-prepare-merge`

---

## v1.4.0 (2026-02-03)

### New Skills

- **`/ca-debug`** — Deep debugging: trace root cause from error message, stack trace, symptom, or GitHub issue number
- **`/ca-issue`** — Create GitHub issues from analysis findings with duplicate check and user confirmation

### Improvements

- All skills now require user confirmation before taking actions (posting comments, creating issues, etc.)
- Added MCP integration documentation (Biome MCP, TypeScript MCP)

---

## v1.3.0 (2026-02-02)

### Improvements

- Enhanced analysis features across all skills
- Better documentation and clarity
- Improved token efficiency

---

## v1.2.0 (2026-02-01)

### Improvements

- Enhanced code review guidelines
- Better style checking rules
- React/NextJS and NestJS specific rules

---

## v1.1.0 (2026-01-31)

### Changes

- Renamed plugin to **Code Sentinel**
- All commands now use `ca-` prefix
- Added `ca-pr-prepare-merge` skill for extracting rules from PR comments

---

## v1.0.0 (2026-01-30)

### Initial Release

- `/ca-security` — Security vulnerability scanner (OWASP Top 10, secrets, injections)
- `/ca-dead-code` — Dead code detector (unused exports, files, dependencies)
- `/ca-code-review` — Local code review for style and correctness
- `/ca-pr-review` — PR review with inline GitHub comments
- Configuration via `.code-analyzer-config.json`
