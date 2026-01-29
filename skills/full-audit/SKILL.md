---
name: full-audit
description: Run a comprehensive project audit combining dead code detection, security scanning, and code style analysis
---

# Full Project Audit

You are a senior code auditor. Run a comprehensive analysis of the project by delegating to specialized agents.

## Project Context

- Project name: !`cat package.json 2>/dev/null | jq -r '.name // "unknown"'`
- Framework: !`cat package.json 2>/dev/null | jq -r '.dependencies // {} | keys[]' 2>/dev/null | grep -iE 'nest|next|express|fastify|react|angular|vue|prisma' | head -10 || echo "unknown"`
- Structure: !`ls -d apps/* packages/* src/* 2>/dev/null | head -20`
- Monorepo: !`cat package.json 2>/dev/null | jq -r '.workspaces // empty' 2>/dev/null; ls pnpm-workspace.yaml lerna.json nx.json turbo.json 2>/dev/null`

## Scope

If `$ARGUMENTS` is provided, focus all analyses on that directory. Otherwise, analyze the entire project.

## Execution Plan

First, read the SKILL.md files for each specialized skill to get their full analysis instructions:

1. Read `skills/security/SKILL.md`
2. Read `skills/dead-code/SKILL.md`
3. Read `skills/code-style/SKILL.md`

Then run three analyses **in parallel** using the Task tool. For each task, pass the full content of the corresponding SKILL.md as the agent's instructions (everything after the frontmatter). Include the scope from `$ARGUMENTS` if provided.

### 1. Security Scan
Launch a Task with `subagent_type=Explore`. Pass the full instructions from `skills/security/SKILL.md` as the prompt. Prepend the scope: "Analyze the project at the current directory. Focus on: `$ARGUMENTS`" (or "entire project" if no arguments).

### 2. Dead Code Analysis
Launch a Task with `subagent_type=Explore`. Pass the full instructions from `skills/dead-code/SKILL.md` as the prompt. Prepend the same scope directive.

### 3. Code Style Analysis
Launch a Task with `subagent_type=Explore`. Pass the full instructions from `skills/code-style/SKILL.md` as the prompt. Prepend the same scope directive.

## Cross-Cutting Analysis

After all three analyses complete, perform a cross-cutting review yourself — look for issues that span categories:

- **Dead code + Security**: Unused auth guards or middleware that were supposed to protect endpoints. Abandoned security checks. Old validation logic that was bypassed but not removed.
- **Dead code + Style**: Unused imports/types that also violate naming conventions. Barrel files re-exporting dead code.
- **Security + Style**: Inconsistent error handling that sometimes leaks stack traces. Inconsistent input validation — some endpoints validated, others not.
- **Architecture concerns**: Circular dependencies, layering violations (controllers calling repositories directly), feature envy between modules.

## Output Format

Compile a unified report from all three analyses plus cross-cutting findings:

---

# Project Audit Report

## Executive Summary
2-3 sentence overview of project health.

## Critical Issues (fix immediately)
Combined CRITICAL findings from security + dead code that pose immediate risk.

## High Priority
Combined HIGH findings across all three analyses.

## Medium Priority
Grouped by category (security, dead code, style).

## Low Priority
Brief list.

## Cross-Cutting Concerns
Issues found at the intersection of categories (see Cross-Cutting Analysis above).

## Metrics
| Category | Score (1-10) | Items Found |
|----------|-------------|-------------|
| Security | X/10 | N issues |
| Dead Code | X/10 | N items |
| Code Style | X/10 | N inconsistencies |
| **Overall** | **X/10** | |

## Top 5 Recommended Actions
Prioritized list of the most impactful improvements to make, combining insights from all analyses.

---
