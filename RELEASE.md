# Release Notes

## v1.6.1 (2026-02-04)

### Improvements

- **UX Review: Browser MCP required** — `/ca-ux-review` now requires browser MCP (Puppeteer/Playwright) instead of optional fallback. Prompts to install if missing, cancels if declined — UX review without visual inspection is incomplete
- **UX Review: Enhanced capture** — screenshots at 3 viewports (1440px, 768px, 375px), keyboard navigation testing, interactive state checks (hover, focus, active, disabled)
- **UX Review: Accessibility audit** — full WCAG 2.1 AA checklist as dedicated step: keyboard navigation, screen readers (aria, labels, alt), visual (contrast 4.5:1, touch targets 44px), motion (prefers-reduced-motion). Findings with CRITICAL/HIGH/MEDIUM/LOW severity
- **UX Review: Loading & transition states** — dedicated step evaluating all async states (initial load, data fetching, form submit, navigation, empty/error/partial failure). Checks for Suspense boundaries, skeleton components, error boundaries in code
- **UX Review: Universal app types** — 8 app types instead of 4: added Landing/Marketing, Documentation/Content, Marketplace, Developer Tool. Patterns tagged with applicable app types
- **UX Review: New patterns** — added Skeleton Loading (#7), Micro-interactions (#11), Trust & Conversion Signals (#12). New Common Problem Areas: Loading & Async, Accessibility
- **UX Review: i18n awareness** — checks for i18n setup and layout breakage with longer translations

---

## v1.6.0 (2026-02-04)

### New Skills

- **`/ca-ux-review`** — UX analysis and redesign proposals: identifies friction points (step bloat, cognitive load, keyboard hostility), proposes redesigns with before/after ASCII mockups, measures impact in clicks/time saved. Includes a design patterns library (inline editing, command palette, progressive disclosure, bulk actions, etc.)

### New Features

- **MCP install prompts** — all skills that use MCP servers (Biome, TypeScript, Puppeteer) now offer to install them if not available, via interactive selector. No more silent fallback — users are guided to enhance their setup

### Improvements

- **PR prepare merge targets source PR branch** — `/ca-pr-prepare-merge` now creates the rules PR against the source PR's branch (`headRefName`) instead of `main`, so extracted rules merge together with the PR
- **Per-rule editing in PR prepare merge** — after bulk-selecting rules, each rule is shown individually with **Send / Edit** options, allowing you to modify the rule text before it's added to CLAUDE.md
- **Selector UX fixes** — item lists are shown as plain text before `AskUserQuestion`, not inside option descriptions. "Other" input always means item numbers, never option numbers
- Removed 200-line limit on SKILL.md files

---

## v1.5.3 (2026-02-03)

### Improvements

- **Interactive selectors instead of text prompts** — all confirmations now use `AskUserQuestion` interactive selectors instead of typing `yes / no / numbers`. Users pick from a clickable list, with "Other" for custom input
- **Severity shortcuts** — bulk selection for findings with severity now offers **Critical only** and **High+** options. No need to manually pick numbers for all CRITICAL items — just select "Critical only" or "High+" from the selector
- **Inverted selection** — type `!3 5` in "Other" to select all items EXCEPT #3 and #5. Useful when you want most findings but need to skip a few
- **Shared confirmation flow** — added `_shared/confirmation-flow.md` as a single reference for all confirmation patterns across skills

### Updated Skills

- `/ca-pr-review` — 6 confirmation points converted to selectors (CI check, resolved comments, post comments, create issues, run debug, send/edit)
- `/ca-issue` — bulk selection and send/edit converted to selectors
- `/ca-pr-prepare-merge` — rule selection and PR preview converted to selectors
- `/ca-debug` — close issue confirmation converted to selector

---

## v1.5.2 (2026-02-03)

### Improvements

- **PR Review issue creation for all severities** — `/ca-pr-review` now offers to create GitHub issues for **all** findings (any severity), not just CRITICAL/HIGH
- **Unified confirmation UX** — replaced `yes / pick / edit / no` with `yes / <numbers> / no` across all skills. User types specific numbers (e.g. `1 3` or `1, 3`) to select individual items instead of going through them one by one
- **Send/edit step before posting** — all skills now show the full body (comment, issue, PR, reply) and ask `send / edit` before each submission to GitHub

---

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
