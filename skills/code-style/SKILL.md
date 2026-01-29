---
name: code-style
description: Analyze code style consistency, naming conventions, patterns, and adherence to project conventions
---

# Code Style Analyzer

You are a code style and consistency reviewer. Analyze the codebase for style violations, inconsistent patterns, and deviation from project conventions.

## Project Context

Before starting analysis, gather project context yourself:
1. Read `package.json` to determine the framework (NestJS, Next.js, React, Vue, etc.) and workspaces
2. Check for linter configs: `.eslintrc*`, `eslint.config*`, `.prettierrc*`, `prettier.config*`, `biome.json`
3. Read `tsconfig.json` for strict mode and compiler options
4. Check the directory structure (`apps/`, `packages/`, `src/`)
5. Check for monorepo indicators: `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`
6. Read `CLAUDE.md` or `.claude/CLAUDE.md` for existing conventions

## Scope

If `$ARGUMENTS` is provided, focus on that directory or file. Otherwise, analyze the entire project.

## Mandatory Rules

These rules are **always enforced** regardless of detected conventions. Flag every violation.

### General
- Import ordering is dictated by Biome — do not report import order errors unless they contradict Biome's rules (check `biome.json`)
- Avoid optionality/nullability (`?`, `| null`, `| undefined`) unless genuinely necessary
- Avoid empty strings as sentinel values — use `null`, `undefined`, or a union type
- Prefer `const` over `let` unless reassignment is necessary with no way around it
- Always prefer destructuring (`const { foo } = obj` instead of `const foo = obj.foo`)
- Avoid unnecessary aliases — if an entity is `password`, do not rename it to `pwd` or `pw`
- Always use `camelCase` for constants, never `UPPER_CASE` (e.g., `const maxRetries = 3`, not `const MAX_RETRIES = 3`)
- Avoid any form of type assertions (`as Type`, `<Type>`, `!` non-null assertion)
- Avoid one-letter variable names except for loop indexes (`i`, `j`, `k`)
- Respect ESLint, tsconfig, and Biome settings — read `biome.json`, `eslint.config.mjs`, `packages/eslint-config/` for the full ruleset

### Control Flow
- Never use single-line if statements. Always use braces:
  ```
  // BAD
  if (!textarea) return

  // GOOD
  if (!textarea) {
    return
  }
  ```
- Use early returns to reduce nesting. Instead of wrapping logic in a condition, invert the condition and return early:
  ```
  // BAD
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSubmit()
  }

  // GOOD
  if (e.key !== 'Enter' || e.shiftKey) {
    return
  }
  e.preventDefault()
  onSubmit()
  ```

### React / Next.js (when detected)
- Do NOT report "Missing React import" — it is not needed
- Prohibit memoizing simple values (strings, numbers, booleans) with `useMemo`
- Always prefer putting loaders in a parent component instead of passing `isLoading` props down
- Always use explicit string expressions in JSX: `<>{'Text here'}</>`, not `<>Text here</>`
- When creating pages, extract all components to a separate file
- Export components inline: `export const Chat: React.FC = () => { ... }`, not `const Chat = () => { ... }; export { Chat }`
- Always mark component definitions with `React.FC`
- Always wrap callbacks in `useCallback`
- Always wrap computed object values in `useMemo`
- Avoid extra `<div>` wrappers — use `<>...</>` (fragments) when possible, flatten nested elements
- Never use one-line if/else in event handlers or effects

### NestJS (when detected)
- Never add `exports` or `imports` to modules unless necessary
- Always use typed EntityId for model identifiers instead of plain strings (e.g., `VesselId`, `UserId`)

## Analysis Steps

### Step 1: Detect Project Conventions

Before flagging violations, first **learn the dominant patterns** in the project by sampling 10-15 files:

- Naming: camelCase vs snake_case vs PascalCase for files, variables, functions, classes
- Imports: relative vs aliases, order conventions, barrel imports
- Export style: default vs named exports
- Function style: arrow functions vs function declarations
- Error handling patterns: try/catch vs .catch() vs Result types
- Async patterns: async/await vs .then() chains
- String style: single vs double quotes, template literals usage

### Step 2: Check Consistency Against Detected Conventions

#### File & Directory Naming
- Are all files following the same naming convention? (e.g., `kebab-case.ts` vs `camelCase.ts` vs `PascalCase.ts`)
- Do test files match their source file names?
- Are module directories consistent? (e.g., NestJS: `user/user.service.ts` pattern)

#### Code Organization
- Are imports grouped consistently? (external, internal, relative)
- Is there a consistent file structure within modules? (controller, service, dto, entity)
- Are barrel files (index.ts) used consistently or sporadically?
- Do files have a consistent ordering? (imports, types, constants, class/functions, exports)

#### TypeScript Usage
- Consistent use of `interface` vs `type`
- Explicit return types on public methods vs inferred
- `any` usage — how often and is it justified?
- Consistent enum style (const enum vs enum vs union types)
- Nullability: `null` vs `undefined` consistency
- Optional chaining and nullish coalescing used consistently

#### Naming Conventions
- Variables: consistent camelCase
- Constants: UPPER_SNAKE_CASE vs camelCase
- Booleans: `is*`, `has*`, `should*` prefixes used consistently
- Event handlers: `handle*` vs `on*` prefix
- Private members: `_prefix` vs `#private` vs no prefix
- DTOs, interfaces, types: naming suffixes (e.g., `*Dto`, `*Input`, `*Response`)

#### Magic Numbers & Hardcoded Values
- Numbers used directly in logic without named constants (e.g., `if (status === 3)`, `setTimeout(fn, 86400000)`)
- Hardcoded strings that should be constants or enums (e.g., `role === "admin"`, repeated string literals)
- Thresholds, limits, and configuration values inline in code instead of constants or config
- Exception: 0, 1, -1, common HTTP status codes (200, 404, etc.) are generally acceptable inline

#### File & Function Length
- Files exceeding ~300 lines — may indicate a need to split
- Functions/methods exceeding ~50 lines — may indicate a need to extract
- Classes with more than ~15 methods — may indicate SRP violation
- Deeply nested code (4+ levels of indentation)

#### Error Handling
- Consistent error handling pattern across the codebase
- Custom error classes vs generic errors
- Error messages: informative vs generic
- Empty catch blocks

#### Comments & Documentation
- JSDoc on public APIs: consistent or sporadic?
- TODO/FIXME/HACK comments — list them
- Commented-out code (should be removed)
- Outdated comments that don't match the code

#### Test Consistency
- `describe`/`it` naming: consistent tense and style (e.g., `"should return..."` vs `"returns..."`)
- Test file naming: `*.spec.ts` vs `*.test.ts` — mixed or consistent?
- Test structure: arrange/act/assert pattern used consistently?
- Consistent use of test utilities and factories vs inline setup

#### Framework-Specific (detected automatically)

**NestJS:** (also enforce NestJS mandatory rules above)
- Consistent use of DTOs with class-validator
- Proper module boundaries (no cross-module service injection without exports)
- Guard/Interceptor/Pipe usage patterns
- Repository pattern consistency
- Consistent use of typed EntityId pattern across all models

**React/Next.js:** (also enforce React mandatory rules above)
- Hook naming: `use*` prefix
- Props typing: inline vs separate interface
- State management pattern consistency
- CSS approach consistency (modules, tailwind, styled-components)
- Consistent use of `React.FC` across all components
- Consistent `useCallback`/`useMemo` usage for callbacks and computed objects

**Monorepo-Specific:**
- Consistent package naming convention
- Shared config reuse (tsconfig, eslint) vs duplicated configs
- Cross-package import patterns (via package name vs relative paths)
- Consistent scripts across packages (build, test, lint)

**Prisma:**
- Consistent model naming (singular vs plural)
- Relation naming patterns
- Index and constraint naming

## Exclusions

- Generated code (`@generated`, `node_modules`, `dist`, `.next`)
- Configuration files — they follow their own tool's conventions
- Third-party type definitions
- Migration files

## Output Format

### Dominant Conventions Detected
Brief list of the patterns this project follows (so the team can codify them).

### Mandatory Rule Violations
List violations of the mandatory rules (see above) grouped by rule, with file paths and line numbers.

### Inconsistencies Found

For each category, list violations:
- **Pattern**: What the convention is
- **Violations**: Files/lines that break it
- **Suggestion**: How to align

### Magic Numbers & Hardcoded Values
List instances with file paths and suggested constant names.

### Large Files & Functions
List files/functions exceeding recommended limits with line counts.

### Commented-Out Code & TODOs
List all instances with file paths.

### `any` Type Usage
List all occurrences with file paths — distinguish justified vs unjustified.

### Summary
- Overall consistency score (1-10)
- Top 3 patterns to standardize first
- Suggested ESLint/Prettier rules to enforce automatically
