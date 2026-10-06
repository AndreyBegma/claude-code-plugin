# Release Notes

## v1.24.0 (2026-10-06)

### New Skills

- **`/cs-orchestrator`** — unattended fleet runner for any GitHub repository
  - Queue = open issues labelled `cs:ready`; `Depends on #N`, `cs:needs-person` and `Gate:` lines respected
  - Dispatches one `claude` session per issue into its own git worktree (`tmux` `cs-<slot>`, Remote Control on), with a per-slot model choice (Opus decides, Sonnet executes)
  - Merges green PRs itself, resumes dead workers in place, refills every free slot in the same pass, wakes on events via `watch.sh` under `Monitor`
  - Bundled scripts in `skills/orchestrator/scripts/`: `dispatch.sh` (worktree + pre-flight + launch), `watch.sh` (event stream), `fence.py` (`PreToolUse` ownership fence, passed via `--settings` — nothing committed into the target repo), trust / bypass-permission pre-flight helpers, `fence_test.py`
- **`/cs-worker`** — what a dispatched session runs: one brief, one issue, checkpoint reports through `.orchestrator-reply.md`, stops before merge
- **`/cs-init`** — fullstack monorepo scaffold (Bun + Turborepo, NestJS 11 + Prisma 7 + PostgreSQL 16, Next.js 16 + React 19 + Tailwind 4, shared package, Biome 2, Jest)
  - Interview: name, title, location, API / web / DB ports — recommendations computed from listening sockets and published container ports, validated free and distinct
  - `scaffold.sh` + `template/`; verified end to end: install, `biome check`, tests, build, initial migration, seed, `/health`
  - Fixes over the reference layout: Biome 2 config, Prisma 7 `prisma.config.ts` (datasource, seed, dotenv), seed with the pg adapter, missing `class-validator` / `class-transformer` (ValidationPipe exits without them), jest types + `tsconfig.build.json`, first-run `init` migration, compose `name:` so projects do not share the `docker` project and its volumes, web port in scripts
- **`/cs-spec`** — specification interview: discovery from evidence, design-tree questions in rounds with recommended defaults, decision-record check, contention map and `## Parallel plan` (one writer per file, serialize by table, model per slot); lands as a GitHub issue (+ optional spec file via docs PR) and optionally queues it with `cs:ready`
- **`/cs-feature`** — feature or bug fix from request to PR: study, plan, approval (interactive / `--auto` / `--worker`), issue, branch, step-by-step implementation with checks, PR with `Closes #N`

### Improvements

- **`/cs-issue`** — `--auto` (no confirmation), `--ready` (queue for the orchestrator), `--depends-on`; feature-request body with acceptance criteria; kind labels

### Configuration

- `.code-analyzer-config.json` → new `orchestrator` section (`base`, `maxSlots`, `readyLabel`, `install`, `checks`, `mergeMethod`, `autoMerge`, …) — all optional

### Files Changed

- `skills/orchestrator/**`, `skills/worker/SKILL.md`, `skills/feature/SKILL.md`, `skills/spec/SKILL.md`, `skills/init/**` — new
- `skills/issue/SKILL.md` — autonomous and queue modes
- `CLAUDE.md`, `README.md`, `.code-analyzer-config.json` — docs and config
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bump to 1.24.0

---

## v1.23.0 (2026-04-07)

### Improvements

- **`/cs-conflict` — base branch detection fixed**
  - When no PR number is given, skill now looks up the open PR for the current branch via `gh pr list --head` and uses its `baseRefName` as the base — instead of always falling back to the remote default branch (which caused it to always target `develop`)
  - Fallback to `git remote show origin` only happens when no open PR is found

- **`/cs-conflict` — no longer commits automatically**
  - Removed `git commit` from Step 7.4 — skill now outputs the suggested commit command for the user to run manually
  - Final output shows `### Next step` with the ready-to-copy `git commit` command

### Files Changed

- `skills/conflict/SKILL.md` — base branch detection rewritten; Step 7.4 commit → suggest only; Step 7.5 push removed; Step 8 output updated
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bump to 1.23.0

---

## v1.22.0 (2026-03-05)

### Breaking Changes

- **Removed `/cs-pr-review-manual` and `/cs-pr-merge-manual`**
  - Manual variants removed — use `/cs-pr-review` and `/cs-pr-merge` directly
  - `README.md` and `CLAUDE.md` updated accordingly; `Mode` column removed from commands table

### Improvements

- **Continued cleanup of things Claude already knows**
  - `skills/conflict/SKILL.md` — replaced explicit lock file → install command table with a one-liner; Claude knows `bun install`, `npm install`, etc.
  - `skills/perf/SKILL.md` — compressed alternatives table (`moment→dayjs`, `uuid→crypto.randomUUID`, `axios→fetch`, `lodash→lodash-es`) into a single hint line
  - Removed `Read-only — never modify code` from `Important` sections in `debug`, `perf`, `arch`, `ux-review`, `ux-test` — redundant where Edit/Write are absent from allowed-tools or behavior is obvious from context

- **`CLAUDE.md` — minor wording fix**
  - `_shared/severity-levels.md` description: "inlined into pr-review skills" → "inlined into pr-review" (manual skill no longer exists)

### Files Changed

- `skills/pr-review-manual/SKILL.md` — **deleted**
- `skills/pr-merge-manual/SKILL.md` — **deleted**
- `skills/conflict/SKILL.md` — Step 7.7 lock file table replaced with one-liner
- `skills/perf/SKILL.md` — alternatives table compressed, Read-only removed
- `skills/debug/SKILL.md` — Read-only removed from Important
- `skills/arch/SKILL.md` — Read-only removed from Important
- `skills/ux-review/SKILL.md` — Read-only removed from Important
- `skills/ux-test/SKILL.md` — Read-only removed from Important
- `CLAUDE.md` — manual skills removed from Structure, severity-levels description updated
- `README.md` — manual commands removed from table/usage/structure; Mode column dropped
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bump to 1.22.0

---

## v1.21.0 (2026-03-05)

### Improvements

- **Skill Authoring Rules applied across all skills — reduced verbosity and ceremony**
  - Removed `## Token Efficiency` sections from all 7 skills that had them (`debug`, `perf`, `arch`, `test`, `review`, `dead-code`, `security`) — these repeated things Claude already knows
  - Removed `## Design Patterns Library` (12 patterns) and `## Common Problem Areas` (6 sections) from `/cs-ux-review` — ~315 lines of enumerated patterns Claude knows by default
  - Collapsed Step 4b Design Analysis in `/cs-ux-test` from ~45 bullet lines to 7 one-liner checks per category
  - Trimmed `## Important` sections across all skills — removed bullets that restated things already in the flow
  - Removed severity `Examples` column from `/cs-pr-review` and `/cs-pr-review-manual` tables
  - Removed "Replace OWNER and REPO" instruction from `/cs-pr-merge-manual` (redundant with Step 1)
  - Replaced unbounded `"re-fetch until all PRs are captured"` in `/cs-history` with one-retry-then-report
  - Replaced emoji triage summary `📊 🔴 🟡 ⚪` in `/cs-pr-review` with plain text
  - Removed `Use --- horizontal rules` formatting rule from `/cs-history` (ceremony)
  - Removed `"essential for token efficiency"` phrasing from `/cs-dead-code` and `/cs-security` scope descriptions

- **`/cs-unit-test` — frontmatter name fixed**
  - `name: unit-test` → `name: cs-unit-test` — now consistent with all other skills

### Files Changed

- `skills/review/SKILL.md`, `skills/security/SKILL.md`, `skills/repo/SKILL.md`, `skills/pr-review/SKILL.md`, `skills/pr-merge/SKILL.md` — Token Efficiency removed, Important trimmed, various cleanup
- `skills/perf/SKILL.md`, `skills/issue/SKILL.md`, `skills/debug/SKILL.md`, `skills/dead-code/SKILL.md`, `skills/conflict/SKILL.md`, `skills/arch/SKILL.md` — Token Efficiency removed, Important trimmed
- `skills/pr-review-manual/SKILL.md`, `skills/pr-merge-manual/SKILL.md` — severity table, Important trimmed
- `skills/seo/SKILL.md`, `skills/analytics/SKILL.md`, `skills/ux-scenario/SKILL.md` — Important trimmed
- `skills/ux-review/SKILL.md` — Design Patterns Library and Common Problem Areas removed, Important trimmed
- `skills/ux-test/SKILL.md` — Step 4b collapsed, Important trimmed
- `skills/unit-test/SKILL.md` — frontmatter name fixed
- `skills/test/SKILL.md` — Important trimmed
- `skills/history/SKILL.md` — retry logic bounded, formatting ceremony removed
- `README.md` — added `/cs-unit-test` and `/cs-test` to commands table, project structure, and usage examples
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bump to 1.21.0

---

## v1.20.1 (2026-03-04)

### Improvements

- **`/cs-test` — now covers all testable units, not just "best candidates"**
  - Added explicit processing order: all 🔵 units go through Unit Pipeline, all 🟡 units go through Integration Pipeline — no skipping
  - "Best candidate" selection is now explicitly forbidden in skill instructions
  - Added `requires live external service` to the ❌ NOT TESTABLE table (live Azure, external OAuth, third-party APIs) — these are now reclassified with explicit reasoning instead of silently ignored
  - 🟡 units that cannot be isolated due to external infrastructure are explicitly ❌ with suggested alternative (contract test, manual E2E)

- **`/cs-test` — PR labels**
  - `tests-added` (green) applied to the source PR when tests are written locally — signals that regression tests exist for this fix
  - `regression-tests` (blue) applied to the new test PR when a separate branch is created — signals this PR is tests-only
  - Labels are created with `--force` so they never fail if already present

- **`/cs-test` — PR cross-linking when creating a new test branch**
  - Reads the source PR description and extracts a Discord thread link (`discord.com/channels/...`) if present — includes it in the new test PR body
  - New test PR body always includes `**Fix PR:** #N` linking back to the source
  - Source PR description is updated after the test PR is created, appending `**Regression tests:** #N` — replaces existing line if already present, no duplicates
  - No attribution line (`🤖 Generated with Claude Code`) added to any PR body or commit message

### Files Changed

- `skills/test/SKILL.md` — processing order enforcement, new ❌ case, labels, PR cross-linking, no-attribution rule
- `.claude-plugin/plugin.json` — version bump to 1.20.1
- `.claude-plugin/marketplace.json` — version bump to 1.20.1

---

## v1.20.0 (2026-03-04)

### New Skill

- **`/cs-test [PR#|branch|commit]` — Retrospective TDD test writer (unit + integration)**
  - Supersedes `/cs-unit-test` with expanded scope — automatically classifies each changed unit as 🔵 Unit, 🟡 Integration, or ❌ Not testable
  - **Unit test pipeline**: pure logic, injectable deps, conditional branches, data normalization — same TDD regression approach as before
  - **Integration test pipeline**: HTTP routes, middleware, DB query logic, framework wiring — detects Supertest, Fastify inject, Hono testClient, NestJS testing automatically
  - Detects ORM/DB (Prisma, TypeORM, Drizzle, Sequelize, raw SQL) and existing test DB setup; adds NOTE comments if infrastructure is missing instead of inventing it
  - Destination choice: write locally on current branch, or create a new branch + PR targeting the current branch
  - Branch naming derived from fix source: `test/pr-42`, `test/fix-user-auth`, `test/abc1234`
  - Interactive: preview each test, edit before writing, confirm destination once for all tests in the session

### Files Changed

- `skills/test/SKILL.md` — new skill
- `CLAUDE.md` — registered `/cs-test` in structure, skills table, and conventions
- `.claude-plugin/plugin.json` — version bump to 1.20.0
- `.claude-plugin/marketplace.json` — version bump to 1.20.0, added `integration-testing` keyword

---

## v1.19.0 (2026-02-25)

### New Skill

- **`/cs-unit-test [PR#|branch|commit]` — Retrospective TDD unit test writer**
  - Analyzes a fix (PR number, branch name, commit SHA, or current diff) against the source branch
  - Determines whether the changed logic is unit-testable: pure logic, class with injectable deps, error handling paths, conditional branches
  - If testable: writes a regression test framed in TDD — the test would have **failed before the fix** and **passes after**
  - If not testable: explains why (migration, config-only, framework coupling, pure structural refactor) and suggests the right alternative (integration test, E2E, visual regression)
  - Detects test framework (Jest/Vitest/Mocha) and existing conventions (co-located specs, `__tests__/`, naming, mock patterns) automatically
  - Adds tests to existing spec files or creates new ones following project conventions
  - Interactive: previews each test before writing, supports edit-before-write
  - Runs the test after writing to confirm it passes; reports errors if it doesn't

### Files Changed

- `skills/unit-test/SKILL.md` — new skill
- `CLAUDE.md` — registered `/cs-unit-test` in structure, skills table, and conventions
- `.claude-plugin/plugin.json` — version bump to 1.19.0
- `.claude-plugin/marketplace.json` — version bump to 1.19.0, added `unit-testing`, `tdd`, `test-coverage`, `regression-tests` keywords

---

## v1.18.1 (2026-02-20)

### Improvements

- **`/cs-analytics` — Step 0 and report accuracy improvements**
  - **Step 0 — 4 questions instead of 2**: now uses a single `AskUserQuestion` call with valid options for all questions. Added two new questions: average conversion value (used in all revenue impact formulas instead of assumed `$X`) and data period anomalies (campaigns, redesigns, seasonal events — prevents misreading traffic spikes as patterns)
  - **Revenue impact formulas use real data**: if `avg_conversion_value` is provided in Step 0, all revenue calculations use it; otherwise the report explicitly states the assumption. Eliminates fabricated revenue estimates.
  - **Step 3 (User Journey Map) shows external platform steps**: journey flows no longer stop at the last tracked event. If Step 0 identified external platforms, they appear in the flow: `→ app.example.com/checkout (external — untracked) → booking confirmed (unknown)`
  - **Step 3 exit point classification**: pages with zero key events are cross-referenced with `external_platforms` before being labeled dead ends — redirect pages with expected off-site continuation are not flagged
  - **Client report — "What We Couldn't Measure" moved before findings**: section now appears after Key Numbers and before "What's Costing You Money" — clients see measurement limitations before reading conclusions, not after
  - **Traffic anomaly context**: `period_anomalies` from Step 0 is referenced when explaining traffic spikes or dips throughout the analysis

### Files Changed

- `skills/analytics/SKILL.md` — Step 0 expanded to 4 questions with valid options, Step 3 updated for external platform flows, client report section order fixed, revenue formulas use `avg_conversion_value`
- `.claude-plugin/plugin.json` — version bump to 1.18.1
- `.claude-plugin/marketplace.json` — version bump to 1.18.1

---

## v1.18.0 (2026-02-20)

### Improvements

- **`/cs-analytics` — false positive prevention and accuracy fixes**
  - **Step 0 (new) — context gathering**: before any analysis, asks the user to describe the intended conversion flow and list external platforms (checkout portal, payment processor, separate subdomain). Prevents treating untracked off-site steps as broken features
  - **Tracking gap classification** (Step 9): gaps are now classified into three types — **A (External platform)**: flow continues on a different domain, expected zero events; **B (Missing tracking)**: feature exists but tracking was never set up; **C (Confirmed drop-off)**: upstream event fires, downstream doesn't. Each type has distinct language rules and recommended actions
  - **Confirmed vs untracked tone rule**: aggressive language ("broken", "failing", "100% failure rate") is now reserved for Type C confirmed drop-offs only. Type A/B gaps use neutral language: "we can't measure this from the available data"
  - **Architectural recommendations require confirmed data**: skill no longer recommends removing auth, rewriting checkout, or changing business logic based on missing GA4 events alone. If auth is required by product design (bookings need a user in the DB), that is a design constraint — not a bug
  - **Client report — "What We Couldn't Measure" promoted**: section now leads with a warning to read before acting, explicitly explains when findings may be inaccurate due to external platforms or missing tracking
  - **Action Items table** — added Type column (✅ Confirmed | ⚠️ Needs verification | 📊 Add tracking first) to both technical and client reports

- **`/cs-analytics` — 37% size reduction (643 → 408 lines)**
  - Report templates condensed from full markdown examples to section-header lists with one-line descriptions
  - Step 8 (Browser MCP): three subsections replaced with 3 core rules + one summary line
  - Step 9 (Tracking Gaps): prose Type A/B/C descriptions replaced with a classification table
  - Step 7 (Code analysis): four verbose subsections condensed to four bullet categories with search patterns
  - Step 4b (Behavioral correlations): inline examples removed, structure preserved

### Files Changed

- `skills/analytics/SKILL.md` — added Step 0, Type A/B/C classification, confirmed vs untracked tone rules, condensed templates and steps
- `.claude-plugin/plugin.json` — version bump to 1.18.0
- `.claude-plugin/marketplace.json` — version bump to 1.18.0

---

## v1.17.1 (2026-02-19)

### Improvements

- **`/cs-conflict` — smarter lint detection after conflict resolution**
  - **Reads `package.json` scripts** — no longer guesses the lint tool; finds all scripts whose keys contain `lint` or `biome` (e.g. `lint`, `biome:lint`, `biome:check`, `lint:fix`, `biome:fix`)
  - **Respects package manager** — detects `bun run` / `pnpm run` / `yarn` / `npm run` from lock file presence instead of hardcoding `npx`
  - **Runs project scripts directly** — `npm run lint`, `npm run biome:lint`, etc. in order; skips fix-only scripts (`lint:fix`, `biome:fix`) for the check pass
  - **Auto-fix uses project scripts** — prefers explicit fix scripts from `package.json` (`lint:fix`, `biome:fix`) over appending `--fix` flag to check commands

### Files Changed

- `skills/conflict/SKILL.md` — rewrote Step 7.2 lint detection logic
- `.claude-plugin/plugin.json` — version bump to 1.17.1
- `.claude-plugin/marketplace.json` — version bump to 1.17.1

---

## v1.17.0 (2026-02-19)

### New Skills

- **`/cs-arch [path|--audit]`** — Architecture consistency checker
  - **Check mode** (`/cs-arch src/features/payments/`): scans the existing codebase to extract the dominant architectural patterns, then compares new code against them across 8 dimensions — flags deviations with `file:line` and concrete fix instructions
  - **Audit mode** (`/cs-arch` or `/cs-arch --audit`): scans the entire project, calculates a **Consistency Score (X/10)** per dimension, identifies architectural drift (pattern used by < 60% of the codebase), and generates a **Unification Plan** with phased migration steps when score < 7
  - **8 architectural dimensions**: folder structure (feature-sliced / layer-based / DDD / flat), data access (Repository / direct ORM / Active Record), API responses (DTOs / raw entity / response wrapper), dependency injection (framework DI / manual / direct instantiation), error handling (custom exceptions / Result type / ad-hoc), module exports (barrel index.ts / direct imports), test organization (co-located / `__tests__` / separate tree), naming conventions (suffixes, casing, interface prefixes)
  - **CLAUDE.md overrides majority**: if a pattern is declared in CLAUDE.md, it is the standard regardless of what exists in code
  - **Drift detection**: if no pattern dominates (< 60%), reports an unresolved architectural split and recommends one to adopt
  - **Unification Plan**: when audit score < 7, generates a phased migration plan ordered by risk (Phase 1: mechanical renames, Phase 2: data layer, Phase 3: error handling)
  - **Read-only**: never modifies code — analysis only

### Files Changed

- `skills/arch/SKILL.md` — new skill
- `CLAUDE.md` — added arch to structure and skills table
- `.claude-plugin/plugin.json` — version bump to 1.17.0
- `.claude-plugin/marketplace.json` — version bump to 1.17.0, added keywords: architecture, architectural-drift, code-consistency

---

## v1.16.1 (2026-02-17)

### Improvements

- **`/cs-conflict` — hardened conflict resolution**
  - **Dirty working tree safe**: auto-stashes uncommitted changes before merge, restores after completion or abort
  - **Lint check before commit** (Step 7.2): auto-detects ESLint/Biome, runs on resolved files, offers auto-fix (`--fix`) if errors found — three options: Auto-fix / Commit anyway / Abort
  - **Skipped conflicts handled correctly**: git requires all conflicts resolved for merge commit — now offers Accept ours / Accept theirs / Abort for remaining files instead of silently failing
  - **Lock files no longer block commit**: uses `git checkout --theirs` + `git add` to clear conflict state, then flags for regeneration
  - **Per-file staging**: `git add` only after ALL regions in a file are resolved — prevents staging files with remaining conflict markers in other regions
  - **Error handling**: validates `gh pr view`, branch checkout, detached HEAD, base branch detection — stops with clear error on failure

### Files Changed

- `skills/conflict/SKILL.md` — added Steps 1.2 (working tree check), 7.2 (lint), fixed lock file handling, per-file staging, skip resolution, error handling

---

## v1.16.0 (2026-02-17)

### New Skills

- **`/cs-conflict [PR#]`** — PR merge conflict resolver
  - **Auto-resolve obvious conflicts**: import ordering (merge + deduplicate + sort), formatting-only (accept ours), non-overlapping additions (keep both), deleted vs unchanged (accept deletion)
  - **Interactive resolution for ambiguous conflicts**: overlapping logic, structural conflicts, same insertion point — user chooses Ours / Theirs / Merge both / Skip per conflict
  - **Lock file handling**: never merges lock files textually — flags `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lockb`, `Gemfile.lock`, `poetry.lock`, `composer.lock` for regeneration
  - **Conflict analysis summary**: categorizes all conflicts before resolution, shows AUTO vs MANUAL breakdown
  - **Three resolution modes**: Proceed (auto + manual), Review each (all manual), Abort
  - **Restore point**: saves SHA before merge attempt — abort recovers branch at any stage via `git merge --abort` or `git reset --hard`
  - **Merge both with editing**: proposes merged code for combined changes, allows editing before accepting
  - **Push confirmation**: never force-pushes, always asks before pushing
  - **Two input modes**: PR number (fetches branch info via `gh`) or empty (uses current branch + auto-detected base)

### Files Changed

- `skills/conflict/SKILL.md` — new skill (8 steps + abort procedure)
- `CLAUDE.md` — added conflict to structure, skills table, conventions
- `README.md` — added conflict to commands, usage examples, project structure
- `.claude-plugin/plugin.json` — version bump to 1.16.0
- `.claude-plugin/marketplace.json` — version bump to 1.16.0

---

## v1.15.0 (2026-02-17)

### Improvements

- **`/cs-pr-review` and `/cs-pr-review-manual` — expanded review categories**
  - **Simplification checks**: detects unnecessary variables/wrappers, overly complex conditions, duplicated logic within the PR, over-engineering (single-use abstractions), verbose patterns with simpler idiomatic alternatives
  - **Performance checks expanded**: multiple array passes (`.filter().map()` → single loop), O(n²) where O(n) is possible (Map/Set lookups), redundant API calls / DB queries that could be batched

- **All skills — zero external file dependencies**
  - Inlined `_shared/confirmation-flow.md` patterns into cs-debug, cs-issue, cs-pr-merge-manual, cs-ux-scenario
  - Inlined `_shared/seo-references.md` benchmarks into cs-seo (CTR table, file patterns, structured data, meta tags) and cs-analytics (file patterns, analytics benchmarks)
  - Inlined `_shared/style-rules.md` into cs-review
  - Every SKILL.md is now fully self-contained — no Read turns wasted on shared files

### Files Changed

- `skills/pr-review/SKILL.md` — added Simplification + expanded Performance categories
- `skills/pr-review-manual/SKILL.md` — added Simplification + expanded Performance categories
- `skills/review/SKILL.md` — inlined style rules
- `skills/seo/SKILL.md` — inlined CTR benchmarks, file patterns, structured data templates, meta tag patterns
- `skills/analytics/SKILL.md` — inlined GA4/GSC file patterns, analytics benchmarks, engagement/mobile stats
- `skills/debug/SKILL.md` — removed external confirmation-flow reference
- `skills/issue/SKILL.md` — inlined confirmation-flow "Other" parsing rules
- `skills/pr-merge-manual/SKILL.md` — removed external confirmation-flow references
- `skills/ux-scenario/SKILL.md` — inlined confirmation-flow "Other" parsing rules
- `.claude-plugin/plugin.json` — version bump to 1.15.0
- `.claude-plugin/marketplace.json` — version bump to 1.15.0

---

## v1.14.0 (2026-02-17)

### Improvements

- **`/cs-pr-review` and `/cs-pr-review-manual` — major overhaul**
  - **GitHub Suggestions**: every review comment now includes a ` ```suggestion ` block with a concrete fix — PR authors can apply with one click
  - **Source context reading** (new Step 4): reads full source files for findings, checks related files for CRITICAL/HIGH — re-evaluates severity with full context instead of diff-only analysis
  - **Comment deduplication**: builds a dedup set from all existing PR comments (including own previous runs) — never posts the same issue twice on re-review
  - **Large diff strategy** (new Step 1.1): three tiers (Small ≤500 lines / Medium ≤2000 / Large 2000+) with risk-based file triage (HIGH/MEDIUM/LOW risk categories) — marks partial reviews explicitly
  - **`--repo` support in manual mode**: `pr-review-manual` now supports `--repo owner/repo` flag (parity with auto mode)
  - **Severity levels formalized**: CRITICAL/HIGH/MEDIUM/LOW criteria with decision shortcuts inlined — no more ambiguous classification
  - **Style rules inlined**: TypeScript, React/Next.js, and NestJS rules embedded directly — no external file reads needed
  - **Token efficiency**: skills are now fully self-contained (zero external file dependencies). Auto: ~5,500 → ~1,800 tokens (-68%). Manual: ~8,100 → ~2,300 tokens (-72%). Eliminated 3 Read tool turns per run

### New Files

- `skills/_shared/severity-levels.md` — standalone severity classification reference (used by other skills)

### Files Changed

- `skills/pr-review/SKILL.md` — rewritten: self-contained, compressed, all features inlined (476 → 182 lines)
- `skills/pr-review-manual/SKILL.md` — rewritten: self-contained, compressed, all features inlined (615 → 230 lines)
- `skills/_shared/severity-levels.md` — new file
- `.claude-plugin/plugin.json` — version bump to 1.14.0
- `.claude-plugin/marketplace.json` — version bump to 1.14.0

---

## v1.13.0 (2026-02-13)

### Improvements

- **`/cs-analytics` — critical tone, code analysis, dual reports**
  - **Critical tone**: findings are now blunt and direct — "This page is losing $66K/month" instead of "There may be an opportunity to improve." Uses "broken", "failing", "losing money" language. Every metric quantified in money/users lost, not just percentages
  - **Code-Level Root Cause Analysis** (new Step 7): cross-references analytics data with actual source code to find WHY problems exist:
    - Form & conversion code: field counts, submission handlers, validation rules, loading states, success/error flows
    - Tracking implementation: GA4/GTM setup, event firing, revenue parameters, conditional tracking
    - Performance & rendering: SSR/SSG checks, data fetching patterns, bundle imports, meta tag accuracy
    - Navigation & CTA code: click handlers, routing, broken links, conditional rendering
    - Each finding includes file:line, code snippet, data connection, and fix suggestion
  - **Dual report output**: generates two separate reports per run:
    - `technical-report.md` — full technical report for developers with code references, formulas, raw data, action items with file:line locations
    - `client-report.md` — executive report for stakeholders in business language — no code, no jargon, focused on money lost and clear actions with difficulty/timeline
  - **Local save**: results saved to `.claude/analytics-result/YYYY-MM-DD_HH-MM/` — each run gets its own timestamped folder with both reports
  - **Critical Verdict**: both reports include overall health assessment (CRITICAL / WARNING / HEALTHY)
  - **Steps renumbered**: 7→Code Analysis, 8→Browser MCP, 9→Tracking Gaps, 10→Recommendations, 11→Reports & Save (was 10 steps, now 11)

### Files Changed

- `skills/analytics/SKILL.md` — expanded from 10 to 11 steps, added Step 7 (Code-Level Root Cause Analysis), replaced Step 10 with dual-report generation and local save, added critical tone instructions throughout
- `CLAUDE.md` — updated analytics description, added report skills convention
- `.claude-plugin/plugin.json` — version bump to 1.13.0
- `.claude-plugin/marketplace.json` — version bump to 1.13.0

---

## v1.12.0 (2026-02-11)

### Breaking Changes

- **All commands renamed from `ca-` to `cs-` prefix** — `ca-` (code-analyzer) was a legacy name. New `cs-` prefix matches the project name (Code Sentinel). All 17 skills updated.
- **6 commands shortened** for better ergonomics:

| Old | New | Why |
|---|---|---|
| `ca-code-review` | **`cs-review`** | "code" redundant in "Code Sentinel" |
| `ca-pr-prepare-merge` | **`cs-pr-merge`** | "prepare" unnecessary |
| `ca-pr-prepare-merge-manual` | **`cs-pr-merge-manual`** | "prepare" unnecessary |
| `ca-seo-audit` | **`cs-seo`** | "audit" is what all skills do |
| `ca-project-history` | **`cs-history`** | "project" redundant |
| `ca-repo-analysis` | **`cs-repo`** | "analysis" redundant |

- **Skill folders renamed** to match shortened names: `code-review/` → `review/`, `pr-prepare-merge/` → `pr-merge/`, `seo-audit/` → `seo/`, `project-history/` → `history/`, `repo-analysis/` → `repo/`

### New Skills

- **`/cs-ux-scenario [PR#|description]`** — Generate UX test scenarios automatically for `/cs-ux-test`
  - **Three input modes**: PR number (analyzes diff), empty (current branch diff), text description (searches codebase for relevant code)
  - **Smart UI filtering**: only analyzes UI-relevant files (components, pages, routes, styles, layouts) — ignores backend, config, and tests
  - **Project-aware generation**: detects framework, routing, UI library, dev server URL, and existing scenarios to avoid duplicates
  - **Real values from code**: extracts actual URLs, button texts, field labels, selectors from source — no generic placeholders
  - **Scenario proposals with selection**: presents numbered list of proposed scenarios, user picks which to generate via `AskUserQuestion` (All / None / specific numbers)
  - **Per-scenario preview**: shows full scenario content before saving with Save / Edit / Skip options
  - **Standard format output**: generates `.md` files in `.claude/ux-tests/` matching `scenario-template.md` format — directly runnable by `/cs-ux-test`
  - **Auto-numbering**: files saved as `{N}-{name}.md` (e.g., `4-checkout-promo.md`) — run by number: `/cs-ux-test 4`
  - **Checkpoint generation**: includes relevant accessibility, loading UX, error handling, and responsive checks per scenario

### Changes

- **`/cs-ux-test` now accepts scenario number** — `/cs-ux-test 1` finds `1-login-flow.md`. Still supports name lookup (`/cs-ux-test login-flow`)
- **Scenario files now use `{N}-{name}.md` naming** — numbered prefix enables quick reference by number instead of typing full names

### Workflow

`/cs-ux-scenario` generates scenarios → `/cs-ux-test` executes them. Together they provide a complete scenario-based UX testing pipeline: auto-generate from PR/branch changes, then run by number with browser automation.

### Files Changed

- All 17 `skills/*/SKILL.md` — renamed `ca-` → `cs-` in frontmatter, updated all cross-references
- `skills/_shared/seo-references.md` — updated command references
- `skills/ux-scenario/SKILL.md` — new skill (7 steps)
- `skills/ux-test/SKILL.md` — updated Step 1 to support number-based lookup
- `skills/ux-test/scenario-template.md` — updated naming convention to `{N}-{name}.md`
- 6 skill folders renamed to shorter names
- `CLAUDE.md` — full rewrite with new command names and folder structure
- `README.md` — full rewrite with new command names, usage examples, project structure
- `.claude-plugin/plugin.json` — version bump to 1.12.0
- `.claude-plugin/marketplace.json` — version bump to 1.12.0, added keywords

---

## v1.11.1 (2026-02-11)

### Improvements

- **`/ca-ux-test` enhanced with designer's perspective** — skill now evaluates every screen as a product designer, not just a QA engineer:
  - **Design Analysis per step** (new Step 4b): visual hierarchy, spacing & alignment consistency, typography (sizes, hierarchy, line length), color & contrast (WCAG AA), feedback responsiveness (100ms/300ms thresholds, CLS detection), cognitive load assessment
  - **Emotional State tracking**: rates user feeling at each step — Confident / Neutral / Uncertain / Frustrated — to map the emotional journey through the flow
  - **Mobile pass** (new Step 5): re-runs entire scenario at mobile viewport (375x812), reports only differences from desktop — touch targets, overflow, truncation, fold issues
  - **Design tokens awareness**: Step 2 now reads `tailwind.config`, `theme.ts`, CSS variables to calibrate spacing/color expectations against project's actual design system
  - **Transitions & animation review**: code review now checks animation durations (150-300ms micro, 300-500ms page), `prefers-reduced-motion` support
  - **Enhanced report**: "Design Quality" section (visual consistency, feedback & microinteractions, information architecture, mobile experience), "Design notes" per step, "Quick wins" vs "Bigger bets" in recommendations
  - **Scenario config**: added `mobile` field (default `375x812`, set `skip` to skip mobile pass)

- **MCP install commands now use `--scope user`** — Puppeteer MCP installs globally in `~/.claude.json` instead of per-project `.mcp.json`. One install works across all projects. Updated in 6 files: CLAUDE.md, README.md, skills (analytics, seo-audit, ux-review, ux-test)

---

## v1.11.0 (2026-02-11)

### New Skills

- **`/ca-ux-test <scenario>`** — Scenario-based UI/UX testing via browser automation
  - **User-defined scenarios**: stores test scenarios as `.md` files in `.claude/ux-tests/` — version-controlled, team-shareable, human-readable
  - **Step-by-step execution**: navigates, clicks, types, scrolls — follows the scenario like a real user would
  - **Before/after screenshots**: captures visual state before and after every action for evidence and comparison
  - **Expected result verification**: checks element visibility, URL changes, text content, visual states — marks each step as PASS / ISSUE / FAIL
  - **Timing measurement**: records execution time per step, flags slow responses (> 2s) as UX issues
  - **Checkpoint verification**: evaluates quality checklist items (accessibility, loading UX, error handling) after scenario completes
  - **Code review per step**: maps each UI step to source components, checks accessibility (aria, labels), error handling, loading states, responsive design
  - **Structured report**: summary with pass/issue/fail counts, step-by-step results with screenshots and code references, UX issues by severity (CRITICAL/HIGH/MEDIUM/LOW), prioritized recommendations
  - **Browser MCP required**: unlike `/ca-ux-review` (which can fall back to code-only), `/ca-ux-test` requires a browser MCP — prompts to install if missing, aborts if declined
  - **Scenario template included**: `skills/ux-test/scenario-template.md` with login flow example and full format reference (action types, config fields, checkpoint patterns)

### Difference from `/ca-ux-review`

|              | `/ca-ux-review`                        | `/ca-ux-test`                           |
| ------------ | -------------------------------------- | --------------------------------------- |
| **Purpose**  | General UX audit of a page             | Execute a specific user scenario        |
| **Input**    | URL or focus area                      | Scenario file name                      |
| **Browser**  | Optional (code-only fallback)          | Required (no fallback)                  |
| **Output**   | Friction analysis + redesign proposals | Step-by-step test report with PASS/FAIL |
| **Use case** | "How good is my UX?"                   | "Does this flow work correctly?"        |

### Files Changed

- `skills/ux-test/SKILL.md` — new skill (7 steps)
- `skills/ux-test/scenario-template.md` — scenario format template with login flow example
- `CLAUDE.md` — added ux-test to structure, skills table, Puppeteer MCP "Used By"
- `.claude-plugin/plugin.json` — version bump to 1.11.0
- `.claude-plugin/marketplace.json` — version bump to 1.11.0, added keywords: ux-testing, scenario-testing, browser-testing

---

## v1.10.0 (2026-02-10)

### New Skills

- **`/ca-project-history`** — Project retrospective from PR history + product status report
  - **PR data collection**: fetches all merged AND closed-not-merged PRs via `gh` CLI with pagination and completeness verification
  - **Role portal mapping**: 4-layer classification (folder match → import tracing → PR context → shared/platform) with sanity checks
  - **Weighted effort estimation**: formula using log2(lines), sqrt(files), days open, commit count, and complexity multiplier (feature 1.0x, refactor 0.3x, bump 0.1x, etc.)
  - **Consistency checks**: 5 mandatory assertions (role totals, monthly sub-totals, category totals, no duplicates, appendix counts) — must all pass before output
  - **Abandoned work analysis**: closed-not-merged PRs tracked separately with closed-to-merged ratio per role
  - **Product timeline**: monthly narrative of what was delivered per role in product terms
  - **Status report synthesis**: cross-references effort with completion from `docs/project-status.md`
  - **Output**: saves to `docs/project-history.md` with executive summary, effort tables, per-role deep dives, key insights, and condensed PR appendix

- **`/ca-repo-analysis`** — Product completeness audit per user role portal
  - **Page inventory**: enumerates every page/screen per role from routing config
  - **5-level classification**: Empty → Visual Only → Partially Wired → Functional MVP → Production Ready
  - **End-to-end data flow tracing**: traces UI → API hook → controller → service → data source (DB or hardcode file) — does NOT stop at the frontend layer
  - **3-type hardcode detection**: frontend hardcode (inline static data), backend hardcode (mock data files, hardcoded entity IDs, fallback values), hybrid hardcode (real API mixing DB data with hardcoded fields)
  - **Backend hardcode inventory**: lists all mock/hardcode data files across the codebase
  - **Completion % calculation**: weighted ratio per role (Visual Only = 20%, Partially Wired = 50%, Functional MVP = 80%, Production Ready = 100%)
  - **Output**: saves to `docs/project-status.md` — prerequisite for `/ca-project-history`

### Files Changed

- `skills/project-history/SKILL.md` — new skill (8 steps)
- `skills/repo-analysis/SKILL.md` — new skill (6 steps)
- `CLAUDE.md` — added project-history and repo-analysis to structure, skills table, conventions
- `README.md` — added both skills to commands, usage examples, project structure
- `.claude-plugin/plugin.json` — version bump to 1.10.0
- `.claude-plugin/marketplace.json` — version bump to 1.10.0, added keywords

---

## v1.9.1 (2026-02-10)

### Improvements

- **`/ca-analytics` enhanced** — 7 improvements based on real-world usage:
  - **Device segmentation**: breaks down key metrics by mobile/desktop/tablet, flags significant mobile conversion gaps (Step 4)
  - **Mobile viewport replay**: Browser MCP now replays critical flows at both desktop (1280x800) and mobile (390x844) when mobile traffic > 50% (Step 7)
  - **Temporal trends**: analyzes traffic direction, seasonality, and weekly patterns from GSC Chart/GA4 date data (Step 5)
  - **Tracking Gaps audit** (new Step 8): identifies missing revenue tracking, untracked conversion pages, and attribution gaps as CRITICAL findings
  - **Revenue proximity scoring**: recommendations now include DIRECT/INDIRECT/BRAND proximity — checkout fixes get priority over newsletter at equal effort (Step 9)
  - **Honest flow reconstruction**: Step 3 now explicitly states that user journeys are reconstructed from CSV aggregates (not user-level paths) with confidence levels (HIGH/MEDIUM/LOW)
  - **Load performance checks**: Browser MCP replay now measures perceived load time and flags pages where load time consumes the engagement budget (Step 7)
  - **Funnel prioritization**: checkout/booking/payment funnels are analyzed first as closest-to-revenue (Step 6)
  - **Benchmark comparisons**: form completion, newsletter signup, engagement time benchmarks added to shared references

### Files Changed

- `skills/analytics/SKILL.md` — expanded from 9 to 10 steps, enhanced Steps 3-7, new Step 8 (Tracking Gaps)
- `skills/_shared/seo-references.md` — added Analytics Benchmarks section (conversion rates, engagement time, mobile vs desktop)

---

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
