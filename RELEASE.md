# Release Notes

## v1.9.0 (2026-02-10)

### New Skills

- **`/ca-analytics`** — Data-driven UX analysis from GA4/GSC exports
  - **User Journey Map**: traces top navigation flows with completion rates and drop-off points
  - **Event Analysis**: ghost button detection, conversion rates per event, engagement anomalies, event sequence gaps
  - **Traffic × Behavior cross-reference**: high-traffic/low-engagement pages, high-converting/low-traffic SEO priorities, intent mismatch detection (requires GSC data)
  - **Conversion Funnel Analysis**: auto-detects funnels from event chains, calculates drop-off rates per step, estimates revenue impact
  - **Browser MCP Flow Replay**: replays top user funnels step-by-step through Browser MCP — navigates, clicks, screenshots at each stage. Focuses on drop-off points to find visual root causes (hidden CTAs, long forms, layout issues)
  - **Multiple modes**: Local (GA4 + project), Remote (`--url` for sites without code access), Data-only (GA4 metrics only), all with optional GSC cross-reference
  - **Data-only principle**: every finding must cite specific numbers and formulas — no opinions

### Changes

- **`/ca-seo-audit` simplified** — removed GA4 cross-reference (Step 7) and internal linking analysis (Step 7.5). SEO audit is now pure GSC/search-focused. If GA4 files are detected, suggests running `/ca-analytics` instead
- **Steps renumbered** in seo-audit: Technical SEO is now Step 7, SERP Analysis Step 8, Generate Fixes Step 9, Apply Fixes Step 10, Generate Report Step 11

### Files Changed

- `skills/analytics/SKILL.md` — new skill (9 steps)
- `skills/seo-audit/SKILL.md` — removed GA4 sections, renumbered steps, added `/ca-analytics` hint
- `CLAUDE.md` — added analytics to structure, skills table, MCP table
- `README.md` — added analytics to commands, usage examples, project structure, MCP table
- `.claude-plugin/plugin.json` — version bump to 1.9.0
- `.claude-plugin/marketplace.json` — version bump to 1.9.0, added keywords: analytics, user-flows, conversion-funnels

---

## v1.8.2 (2026-02-09)

### Fixes

- **Fixed MCP install commands** — removed non-existent packages (`@anthropic-ai/mcp-install`, `@anthropic-ai/mcp-server-biome`, `@anthropic-ai/mcp-server-typescript`) that returned 404 from npm. Puppeteer MCP now uses the correct package `@modelcontextprotocol/server-puppeteer` with the proper `claude mcp add` command. Biome and TypeScript MCP marked as not yet available on npm with links to tracking issues.

### Improvements

- **SEO audit: estimated gains now require math** — Quick Wins must show the formula `impressions × (benchmark_CTR - actual_CTR)` instead of unexplained ranges
- **SEO audit: Health Score with scoring rubric** — each factor now has concrete thresholds (e.g., "25 if avg pos < 5, 20 if < 8...") and the report must show per-factor breakdown with reasoning
- **SEO audit: deep GA4 correlation** — expanded from basic table listing to 5 specific analyses: traffic-to-conversion mapping, high-converting low-traffic pages, engagement quality, funnel drop-off rate, revenue opportunity estimates
- **SEO audit: internal linking analysis** (new step 7.5) — orphan page detection, high-traffic→high-converting link recommendations, hub page analysis
- **SEO audit: expanded problem detection** — added HTTP/WWW/param duplicate detection, meta tag length validation, content-intent mismatch flagging
- **SEO audit: Technical SEO expanded** — added Core Web Vitals check (with PageSpeed Insights link fallback) and HTTP/HTTPS/WWW variant detection from GSC data
- **SEO audit: improved report structure** — defined exact section order with required content per section
- **SEO references: 3 new structured data templates** — added TouristTrip (tours/adventures), LocalBusiness (service companies), HowTo (guides/tutorials)

### Files Changed

- `CLAUDE.md`, `README.md`, `RELEASE.md` — updated MCP install commands
- `skills/seo-audit/SKILL.md` — enhanced steps 4, 5, 6, 7, 8, 12; added step 7.5
- `skills/_shared/seo-references.md` — added TouristTrip, LocalBusiness, HowTo templates
- 8 skill files — fixed MCP install references (code-review, dead-code, debug, pr-review, pr-review-manual, perf, ux-review, seo-audit)

---

## v1.8.1 (2026-02-06)

### Improvements

- **CLAUDE.md optimized** — reduced from 405 to 71 lines (~4× less tokens per session). Removed duplicated content that already exists in SKILL.md files (workflows, examples, usage, configuration). All skill behavior unchanged — execution logic lives in SKILL.md, not CLAUDE.md
- **`allowed-tools` added to all 12 skills** — each skill now declares an explicit tool whitelist in frontmatter. Read-only skills (security, dead-code, perf) can no longer accidentally modify files. Auto-mode skills (pr-review) cannot trigger user prompts. Ensures safe, predictable execution

---

## v1.8.0 (2026-02-06)

### New Features

- **CI-ready auto mode for PR skills** — `/ca-pr-review` and `/ca-pr-prepare-merge` now run fully automatically without any user prompts, ready for GitHub Actions and other CI pipelines
- **Manual mode variants** — added `/ca-pr-review-manual` and `/ca-pr-prepare-merge-manual` with full interactive confirmations (choose what to post, edit before sending, pick specific rules)

### Changes

- **`/ca-pr-review` (auto mode):**
  - Posts ALL review comments automatically — no bulk selection prompt
  - Auto-views failed CI logs and continues (no "view logs / skip / cancel" prompt)
  - Auto-replies "✅ Fixed" to all resolved comments from previous reviews
  - Proceeds without waiting when CI is still running
  - Skips Biome MCP install prompt — shows warning and continues
  - Removed issue creation step (use `/ca-issue` separately if needed)

- **`/ca-pr-prepare-merge` (auto mode):**
  - Includes ALL extracted rules automatically — no bulk selection prompt
  - No per-rule send/edit confirmation
  - Creates PR without preview confirmation

- **`/ca-pr-review-manual`** — preserves original interactive behavior: bulk selection with severity shortcuts, per-comment send/edit, issue creation offers, debug pipeline for CRITICAL issues

- **`/ca-pr-prepare-merge-manual`** — preserves original interactive behavior: rule selection (All/None/specific), per-rule editing, PR preview with send/edit

### Updated

- CLAUDE.md — updated structure and skill descriptions with Auto/Manual labels
- README.md — commands table with Mode column, usage examples for both modes, updated project structure
- Marketplace keywords — added: ci, automation, github-actions

---

## v1.7.1 (2026-02-05)

### Fixes

- **PR Review comment feedback** — now shows URL and status after each posted comment:
  ```
  ✅ Posted: user.service.ts:45 — Missing null check
     https://github.com/owner/repo/pull/18#discussion_r1234567890
  ```
- **PR Review output format** — improved final summary with clickable table of posted comments, separate sections for PR and local review modes
- **PR Review reply feedback** — shows URL after replying "✅ Fixed" to resolved comments
- **Fixed markdown formatting** — corrected 4-backtick code blocks and truncated text in style rules
- **Unified MCP install prompts** — `/ca-seo-audit` now uses the same `AskUserQuestion` format as other skills for Browser MCP installation

---

## v1.7.0 (2026-02-04)

### New Skills

- **`/ca-seo-audit`** — SEO analysis from Google Search Console and GA4 CSV exports
  - **Quick wins detection**: pages at position 4-10 (almost top 3), high impressions with low CTR, zero-click pages
  - **Problem detection**: keyword cannibalization, mobile vs desktop gap, declining traffic
  - **GA4 correlation**: bounce rate, engagement time, conversion rate by landing page
  - **Code integration**: maps URLs to project files (Next.js, Astro, Remix, Nuxt, SvelteKit, React)
  - **Auto-fix meta tags**: `--fix` flag proposes optimized title, description, Open Graph with diffs
  - **Structured data suggestions**: Article, Product, FAQ, Breadcrumb schemas
  - **SEO Health Score**: 0-100 based on position, CTR, mobile parity, cannibalization, rich results
  - **CTR benchmarks**: compares actual CTR to expected by position (identifies underperformers)
  - **Multi-language support**: parses both English and Russian GSC exports (UTF-8 and Windows-1251)
  - **Branded/Non-branded split**: auto-detects brand name, shows separate metrics (avoids brand inflation)
  - **Period comparison**: `--compare` flag to compare two periods and find gainers/losers
  - **Technical SEO audit**: robots.txt, sitemap, canonical tags, hreflang validation
  - **SERP analysis (Browser MCP)**: screenshots Google SERP, analyzes competitor titles/descriptions
  - **Browser MCP prompt**: offers to install Puppeteer MCP for enhanced analysis

---

## v1.6.2 (2026-02-04)

### Fixes

- **Fixed MCP install commands** — corrected install command format (later updated again in v1.8.2 to `claude mcp add` with real npm packages)
- **Updated MCP documentation** — CLAUDE.md and README.md now show correct install commands with table format showing which skills use which MCPs
- **MCP skill mapping updated** — Biome MCP now lists `/ca-pr-review`, TypeScript MCP now lists `/ca-perf`

---

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
