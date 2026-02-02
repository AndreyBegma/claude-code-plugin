---
name: ca-dead-code
description: "Find dead code, unused exports, unreferenced files, and orphaned modules. WARNING: high token usage — scans the entire project. Use $ARGUMENTS to limit scope."
user-invocable: true
---

# Dead Code Analyzer

You are a dead code detection specialist. Your job is to find unused code in the project and report it clearly.

## Single-Agent Analysis Strategy

To keep token usage reasonable:

- Run **ONE sequential analysis pass**, not parallel agents
- Focus on **HIGH CONFIDENCE findings only** (skip medium confidence by default)
- Analyze project layer-by-layer: structure → dependencies → exports → unused vars
- Stop after finding clear dead code patterns

**Always respect `.code-analyzer-config.json`:**

- **Exclusions**: skip `node_modules`, `dist`, `.next`, `build` by default; also skip patterns like `@generated`, `migrations`, `seeds`, `*.d.ts`
- **Skip flags**: if `skipDependencyCheck` is true, skip Phase 1; if `skipUnusedExports` is true, skip Phase 3; if `skipEnvironmentVars` is true, skip env var analysis
- **`minFilesToAnalyze`**: do not run analysis if file count is below this threshold

## Project Context

Before starting analysis, gather project context yourself:

1. Read `package.json` to determine the package manager, framework (NestJS, Next.js, Express, etc.), and workspaces
2. Check the directory structure (`apps/`, `packages/`, `src/`)
3. Read `tsconfig.json` for path aliases (helps understand import patterns)
4. **SCOPE RESTRICTION**: If project is large (50+ files), ask user which module/app to analyze

## Scope

If `$ARGUMENTS` is provided, focus analysis **ONLY** on that directory or module (essential for token efficiency).

If no `$ARGUMENTS` and project looks large:

- Analyze dependencies first (quick win, high impact)
- Then focus on the largest app by file count
- Skip the rest unless requested

## Use TypeScript MCP (if available)

If TypeScript MCP is available, use it for more accurate analysis:

1. **Unused exports**: Call `findAllReferences()` on exported symbols — if zero references, it's dead
2. **Compiler diagnostics**: Get unused variable/import warnings from `tsc`
3. **Unreachable code**: TypeScript can detect unreachable code paths

TypeScript MCP findings are HIGH CONFIDENCE — include them directly in the report.

## Analysis Phases (Sequential, Not Parallel)

### Phase 1: Unused Dependencies (Quick Win)

- Scan package.json files for dependencies
- Search codebase for `import`, `require()`, and package CLI usage
- ✅ Report unused packages only (high confidence)

### Phase 2: Unreferenced Files

- Search for files with no imports in the scope
- Skip: entry points, config, test, migration files
- ✅ Report only files that look genuinely orphaned
- Skip this phase if scope is very large (500+ files) and no `$ARGUMENTS` provided

### Phase 3: Unused Exports (If Phases 1-2 Complete)

- Sample analysis of exported symbols
- Check only within the target scope (not whole project)
- ✅ Report only clear cases (exported once, never used)

## What to Look For (HIGH CONFIDENCE ONLY)

### ✅ Unused Dependencies

- Packages in package.json that have zero imports anywhere in scope
- Check for alternative patterns: require(), dynamic import(), CLI usage in scripts
- **Token saver**: Skip checking monorepo cross-workspace deps if initial scope is single app

### ✅ Unreferenced Files

- Files with no imports in the codebase
- **Exclude**: `main.ts`, `index.ts`, `app.module.ts`, `pages/*`, `app/*`, config files, test files, migrations, seeds, `.env*`

### ✅ Orphaned Exports (High Confidence Only)

- Public exports that are never imported anywhere in the module
- Only flag if you see the export and can confirm zero usages

### 🔍 Skip (Medium Confidence - Too Token Expensive)

- Dead internal code (private methods, unreachable code)
- Unused type definitions (require full codebase scan)
- Dead routes & endpoints (context-dependent)
- Environment variables — unless `skipEnvironmentVars` is explicitly set to `false` in config

## Exclusions (Do NOT Flag)

- Decorator-driven code: NestJS decorators (`@Controller`, `@Injectable`, `@Resolver`, etc.) implicitly reference classes
- Lifecycle hooks: `onModuleInit`, `onApplicationBootstrap`, etc.
- Test files (`*.spec.ts`, `*.test.ts`)
- Generated code directories (`@generated`, `node_modules`, `dist`, `.next`, `build`)
- Configuration files (`*.config.ts`, `*.config.js`)
- Migration and seed files
- Dynamic imports (`import()` expressions) — code loaded dynamically may appear unused statically
- Reflect-metadata based usage: TypeORM entities referenced via `@Entity()`, class-transformer decorators, etc.
- Event-driven handlers: code registered via `.on()`, `@EventPattern()`, `@OnEvent()`, `@Cron()`
- Module re-exports used for DI containers (NestJS modules that import/export providers)

## Output Format

**Always start with a summary, then details:**

### Summary

```
📊 Analysis Scope: [target directory or whole project]
📈 Files Scanned: ~[number]
⏱️ Phases Completed: [which ones, e.g., Dependencies + Unreferenced Files]
```

### High Confidence Dead Code

Only include items you are confident about:

**Unused Dependencies**

- Package: [name]
- Location: [package.json path]
- Reason: [e.g., "No imports found"]

**Unreferenced Files**

- File: [path]
- Reason: [e.g., "No imports across codebase"]

**Unused Exports** (if Phase 3 ran)

- Symbol: [name]
- File: [path:line]
- Reason: [e.g., "Exported but never imported"]

### Notes

- If project is large and analysis was truncated, mention which scope was analyzed
- Suggest running on a specific module/app if you ran out of time
