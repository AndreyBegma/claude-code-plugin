# Code Sentinel

AI code guardian — catches security issues, dead code, and style violations. Reviews PRs and learns your team's conventions.

All commands use the `ca-` prefix (code-sentinel) to avoid conflicts with built-in or other plugin commands.

## Structure

```
skills/
  _shared/style-rules.md                — Shared style rules (referenced by code-review and pr-review)
  _shared/confirmation-flow.md          — Shared confirmation UX patterns (AskUserQuestion selectors)
  _shared/seo-references.md             — CTR benchmarks, meta tag patterns, structured data templates
  security/SKILL.md                     — /ca-security
  dead-code/SKILL.md                    — /ca-dead-code
  code-review/SKILL.md                  — /ca-code-review
  pr-review/SKILL.md                    — /ca-pr-review [AUTO]
  pr-review-manual/SKILL.md             — /ca-pr-review-manual [MANUAL]
  pr-prepare-merge/SKILL.md             — /ca-pr-prepare-merge [AUTO]
  pr-prepare-merge-manual/SKILL.md      — /ca-pr-prepare-merge-manual [MANUAL]
  debug/SKILL.md                        — /ca-debug
  issue/SKILL.md                        — /ca-issue
  perf/SKILL.md                         — /ca-perf
  ux-review/SKILL.md                    — /ca-ux-review
  seo-audit/SKILL.md                    — /ca-seo-audit
```

## Skills

| Command                                          | Description                                                                                                                   |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `/ca-security`                                   | Security vulnerability scanner — OWASP Top 10, exposed secrets, injections, auth bypass                                       |
| `/ca-dead-code`                                  | Dead code detector — unused packages, unreferenced files, orphaned exports. **High token usage** — pass a path to limit scope |
| `/ca-code-review`                                | Local code review for style and correctness (no GitHub interaction)                                                           |
| `/ca-pr-review <PR#>`                            | **[AUTO]** Review PR, post all comments automatically — CI-ready, no prompts                                                  |
| `/ca-pr-review-manual <PR#>`                     | **[MANUAL]** Review PR with interactive confirmations — choose what to post, edit before sending                              |
| `/ca-pr-prepare-merge <PR#>`                     | **[AUTO]** Extract rules from PR comments, create CLAUDE.md PR automatically — CI-ready                                       |
| `/ca-pr-prepare-merge-manual <PR#>`              | **[MANUAL]** Extract rules with interactive confirmations                                                                     |
| `/ca-debug <error\|#issue>`                      | Deep debugger — trace root cause from error, stack trace, symptom, or GitHub issue                                            |
| `/ca-issue [description]`                        | Create GitHub issues from analysis findings — with duplicate check and user confirmation                                      |
| `/ca-perf [path\|category]`                      | Performance analyzer — N+1 queries, re-renders, memory leaks, bundle size                                                     |
| `/ca-ux-review [url\|focus]`                     | UX analysis — friction points, redesign proposals with before/after mockups                                                   |
| `/ca-seo-audit <path> [--fix\|--url\|--compare]` | SEO analysis from GSC/GA4 exports — quick wins, problems, meta tag fixes                                                      |

**Auto vs Manual:** Auto modes run without prompts (CI-ready). Manual modes offer interactive confirmations (choose items, edit before posting).

## Configuration

Reads `.code-analyzer-config.json` in the project root for exclusions and per-skill settings. See the file for available options.

## Recommended MCP Servers

| MCP Server     | Install                                                                        | Used By                       |
| -------------- | ------------------------------------------------------------------------------ | ----------------------------- |
| **Puppeteer**  | `claude mcp add puppeteer -- npx -y @modelcontextprotocol/server-puppeteer`    | ux-review, seo-audit          |
| **Biome**      | Not yet available on npm — see [biomejs/biome#6017](https://github.com/biomejs/biome/discussions/6017) | code-review, pr-review, debug |
| **TypeScript** | Not yet available on npm — use VS Code `getDiagnostics` as fallback            | dead-code, perf, debug        |

Skills auto-detect missing MCPs and offer to install via `AskUserQuestion`. If skipped, analysis continues with reduced accuracy.

## Conventions

- Analysis skills are **read-only** — they never modify the target project
- Action skills (`ca-pr-prepare-merge`) may create branches/PRs but only modify instruction files (CLAUDE.md)
- All commands use the `ca-` prefix to avoid naming conflicts
- `node_modules`, `dist`, `.next`, `build` are **always** excluded across all skills
- All exclusions respect `.code-analyzer-config.json`
- Each skill runs **one sequential analysis** (single-agent, not parallel)
- Prioritizes HIGH/CRITICAL findings; lower-severity issues included where appropriate
- Respects `$ARGUMENTS` to analyze specific directories
- All user confirmations use **interactive selectors** (`AskUserQuestion`), not text prompts — see `_shared/confirmation-flow.md`
