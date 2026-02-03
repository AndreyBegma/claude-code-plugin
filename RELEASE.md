# Release Notes

## v1.5.1 (2026-02-03)

### New Features

- **PR Review → Issue → Debug pipeline** — `/ca-pr-review` now offers to create GitHub issues for CRITICAL/HIGH findings after posting comments, then offers to run `/ca-debug` for CRITICAL issues

### Improvements

- **Enhanced `/ca-debug` with advanced debugging techniques:**
  - **Git Bisect** — automated binary search to find the commit that introduced a bug
  - **5 Whys Analysis** — root cause analysis by asking "why?" iteratively
  - **Hypothesis-Driven Debugging** — structured approach with CONFIRMED/REFUTED hypotheses
  - **Flaky Bug Detection** — patterns for race conditions, timing issues, environment dependencies
  - **Dependency Debugging** — version conflicts, lock file analysis, peer dependency issues
  - **Logging Injection Points** — suggestions for strategic log placement

- **Updated `/ca-issue`** — added `performance` label for `/ca-perf` findings

- **Token efficiency** — extracted shared style rules to `skills/_shared/style-rules.md`, reduced duplication across skills

- **Marketplace keywords** — added: debug, perf, performance, n+1, memory-leak

---

## v1.5.0 (2026-02-03)

### New Skills

- **`/ca-perf`** — Performance analyzer: N+1 queries, React re-renders, memory leaks, bundle size issues
  - Database analysis: N+1 patterns, missing includes, unbounded queries
  - React performance: unnecessary re-renders, missing memoization, context misuse
  - Memory leaks: uncleared intervals, missing cleanup, dangling subscriptions
  - Bundle size: heavy dependencies, missing tree-shaking, code splitting opportunities
  - Network: sequential requests, missing caching, over/under-fetching

### New Features

- **CI status check in PR review** — `/ca-pr-review` now checks CI status before reviewing. If CI failed, shows errors and offers to view logs
- **Branch protection check in PR prepare merge** — `/ca-pr-prepare-merge` now shows merge readiness checklist:
  - CI status (passed/failed/pending)
  - Review status (approved/changes_requested/required)
  - Conflicts (none/has conflicts)
  - Mergeable state

### Improvements

- Updated CLAUDE.md and README.md with new commands and features
- Now 8 skills total in the plugin

---

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
