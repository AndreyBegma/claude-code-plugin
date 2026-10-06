# Code Sentinel

AI code guardian — catches security issues, dead code, and style violations. Reviews PRs and learns your team's conventions.

All commands use the `cs-` prefix (code-sentinel) to avoid conflicts with built-in or other plugin commands.

## Structure

```
skills/
  _shared/style-rules.md                — Style rules reference (inlined into each skill)
  _shared/confirmation-flow.md          — Confirmation UX patterns reference (inlined into each skill)
  _shared/seo-references.md             — CTR benchmarks, meta tag patterns reference (inlined into each skill)
  _shared/severity-levels.md            — Severity classification reference (inlined into pr-review)
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
  ux-test/scenario-template.md          — Scenario file template for users
  ux-scenario/SKILL.md                  — /cs-ux-scenario
  arch/SKILL.md                         — /cs-arch
  unit-test/SKILL.md                    — /cs-unit-test
  test/SKILL.md                         — /cs-test
  spec/SKILL.md                         — /cs-spec
  feature/SKILL.md                      — /cs-feature
  worker/SKILL.md                       — /cs-worker
  orchestrator/SKILL.md                 — /cs-orchestrator
  orchestrator/scripts/                 — dispatch.sh, watch.sh, fence.py, fence_test.py, launch pre-flight helpers
```

## Skills

| Command                                         | Description                                                                                                                   |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `/cs-security`                                  | Security vulnerability scanner — OWASP Top 10, exposed secrets, injections, auth bypass                                       |
| `/cs-dead-code`                                 | Dead code detector — unused packages, unreferenced files, orphaned exports. **High token usage** — pass a path to limit scope |
| `/cs-review`                                    | Local code review for style and correctness (no GitHub interaction)                                                           |
| `/cs-pr-review <PR#>`                           | Review PR, post all comments automatically — CI-ready, no prompts                                                             |
| `/cs-pr-merge <PR#>`                            | Extract rules from PR comments, create CLAUDE.md PR automatically — CI-ready                                                  |
| `/cs-conflict [PR#]`                            | Resolve merge conflicts — auto-resolves obvious conflicts (imports, formatting), interactive resolution for ambiguous ones     |
| `/cs-debug <error\|#issue>`                     | Deep debugger — trace root cause from error, stack trace, symptom, or GitHub issue                                            |
| `/cs-issue [description] [--auto] [--ready]`    | Create GitHub issues from findings or requests — duplicate check, user confirmation or `--auto`; `--ready` queues for `/cs-orchestrator` |
| `/cs-spec [what\|#issue]`                        | Specification interview — design tree in rounds, decision check, contention map, parallel plan; lands as an issue for `/cs-orchestrator` |
| `/cs-feature <#issue\|desc> [--auto] [--worker]` | Feature or bug fix from request to PR — study, plan, approval (or `--auto`), issue, branch, implement, checks, PR              |
| `/cs-orchestrator [start\|status\|next\|stop]`   | Autonomous fleet — parallel worker sessions in git worktrees for `cs:ready` issues, auto-merge green PRs, refill slots        |
| `/cs-worker <brief>`                             | Worker session launched by `/cs-orchestrator` — one issue, one worktree, ownership fence, never merges                        |
| `/cs-perf [path\|category]`                     | Performance analyzer — N+1 queries, re-renders, memory leaks, bundle size                                                     |
| `/cs-ux-review [url\|focus]`                    | UX analysis — friction points, redesign proposals with before/after mockups                                                   |
| `/cs-seo <path> [--fix\|--url\|--compare]`      | SEO analysis from GSC exports — quick wins, problems, meta tag fixes                                                          |
| `/cs-analytics [path]`                          | Critical data-driven UX & code analysis from GA4/GSC — saves technical + client reports to `.claude/analytics-result/`        |
| `/cs-history`                                   | Project retrospective — PR history mapped to role portals, weighted effort distribution, product timeline                     |
| `/cs-repo`                                      | Product completeness audit — per-role page inventory, functional vs visual, end-to-end data flow tracing                     |
| `/cs-ux-test <N\|name>`                          | Scenario-based UI/UX testing — execute user scenarios via browser, capture screenshots, verify results, report issues         |
| `/cs-ux-scenario [PR#\|description]`            | Generate UX test scenarios from PR, branch diff, or description — saves ready files for `/cs-ux-test`                        |
| `/cs-arch [path\|--audit]`                      | Architecture consistency — checks if new code follows project patterns, or audits whole project for drift and proposes unification |
| `/cs-unit-test [PR#\|branch\|commit]`           | Retrospective TDD unit test writer — analyzes a fix and writes a unit test that would have caught the bug, or explains why it's not possible |
| `/cs-test [PR#\|branch\|commit]`                | Retrospective TDD test writer — classifies the fix (unit/integration/not testable) and writes the appropriate test that would have caught the bug |

## Configuration

Reads `.code-analyzer-config.json` in the project root for exclusions and per-skill settings. See the file for available options.

## Recommended MCP Servers

| MCP Server     | Install                                                                        | Used By                    |
| -------------- | ------------------------------------------------------------------------------ | -------------------------- |
| **Puppeteer**  | `claude mcp add puppeteer --scope user -- npx -y @modelcontextprotocol/server-puppeteer`    | ux-review, ux-test, seo, analytics |
| **Biome**      | Not yet available on npm — see [biomejs/biome#6017](https://github.com/biomejs/biome/discussions/6017) | review, pr-review, debug |
| **TypeScript** | Not yet available on npm — use VS Code `getDiagnostics` as fallback            | dead-code, perf, debug     |

Skills auto-detect missing MCPs and offer to install via `AskUserQuestion`. If skipped, analysis continues with reduced accuracy.

## Conventions

- Analysis skills are **read-only** — they never modify the target project
- Output skills (`cs-history`) write to `docs/` but never modify source code
- Report skills (`cs-analytics`) write to `.claude/analytics-result/` — timestamped folders with technical + client reports
- Action skills (`cs-pr-merge`) may create branches/PRs but only modify instruction files (CLAUDE.md)
- Conflict resolution (`cs-conflict`) modifies conflicted files to resolve merge conflicts — interactive only, no auto-only variant
- Unit test writer (`cs-unit-test`) writes test files only — never modifies source code; interactive with preview before writing
- Test writer (`cs-test`) writes unit or integration test files only — never modifies source code; classifies fix type automatically; interactive with preview before writing
- All commands use the `cs-` prefix to avoid naming conflicts
- `node_modules`, `dist`, `.next`, `build` are **always** excluded across all skills
- All exclusions respect `.code-analyzer-config.json`
- Each skill runs **one sequential analysis** (single-agent, not parallel) — except `cs-orchestrator`, which dispatches parallel worker sessions by design
- Spec skill (`cs-spec`) writes documents only (issue body, optional spec file / decision record via a docs PR) — never product code, never dispatches; asks before publishing
- Feature skill (`cs-feature`) modifies source code — only after an approved plan (or a posted plan under `--auto`), always on a feature branch, never merges
- Orchestrator (`cs-orchestrator`) never writes product code; it creates worktrees/branches, labels issues, and merges green PRs (unless `orchestrator.autoMerge` is `false`). Workers (`cs-worker`) are fenced by `orchestrator/scripts/fence.py` and never merge
- Skill-bundled scripts are referenced as `${CLAUDE_SKILL_DIR}/scripts/...`; run `python3 skills/orchestrator/scripts/fence_test.py` after changing `fence.py`
- Prioritizes HIGH/CRITICAL findings; lower-severity issues included where appropriate
- Respects `$ARGUMENTS` to analyze specific directories
- All user confirmations use **interactive selectors** (`AskUserQuestion`), not text prompts — patterns inlined into each skill
- All skills are **self-contained** — no external `_shared/` file reads needed at runtime. `_shared/` files exist as reference only
