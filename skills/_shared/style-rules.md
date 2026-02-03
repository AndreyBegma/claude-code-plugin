# Style Rules

Apply these rules when reviewing code. **CLAUDE.md rules take priority** over these defaults.

## General TypeScript/JavaScript

- Prefer `const` over `let` unless reassignment is necessary
- Always prefer destructuring
- Early returns over deep nesting (invert conditions, return early)
- Braces on all control flow statements — never single-line `if` statements
- No type assertions (`as`, non-null assertion `!`) without justification
- No `any` types without justification
- Import ordering — follow Biome rules (see `biome.json`)
- Avoid optionality/nullability unless necessary
- Avoid empty strings as sentinel values
- Avoid unnecessary aliases (`password` → `pwd` is forbidden)
- Use `camelCase` for constants, not `CAPITAL_CASE`
- Avoid one-letter variable names except loop indexes (`i`, `j`, `k`)
- Respect ESLint, tsconfig, and Biome settings in the project
- Naming conventions — consistency within the project

## React/Next.js

- Never report "Missing React import" — not needed in modern React
- Wrap callbacks in `useCallback`, computed objects in `useMemo`
- Do not memoize simple values (strings, numbers, booleans)
- Mark components with `React.FC`: `const MyComponent: React.FC = () => ...`
- Use explicit strings in JSX: `<>{'text'}</>` not `<>text</>`
- Export directly: `export const X = () => ...` not `const X = ...; export { X }`
- Avoid extra `<div>`s — use fragments `<>...</>` when possible
- Put loaders in parent components instead of passing `isLoading` props
- Extract all components from page files to separate files

## NestJS

- Never add exports/imports to modules unless necessary
- Use typed EntityId (`UserId`, `VesselId`) instead of plain strings
