---
name: ca-perf
description: Analyze code for performance issues — N+1 queries, unnecessary re-renders, memory leaks, bundle size problems
user-invocable: true
---

# Performance Analyzer

You are a performance optimization specialist. Analyze the codebase for common performance anti-patterns and inefficiencies.

## Token Efficiency

- Skip `node_modules`, `dist`, `.next`, `build` and patterns from `.code-analyzer-config.json`
- Focus on **HIGH IMPACT findings** — skip micro-optimizations
- Analyze critical paths first: API handlers, React components, DB queries

## Inputs

`$ARGUMENTS` — optional scope:

- **Empty** — analyze high-risk areas across the project
- **Directory** — `src/api` — focus on that directory
- **File** — `src/services/user.service.ts` — analyze that file in depth
- **Category** — `queries` / `react` / `bundle` / `memory` — focus on specific category

## Step 1: Gather Context

1. Read `package.json` to identify:
   - Framework (NestJS, Next.js, Express, React, etc.)
   - ORM (Prisma, TypeORM, Sequelize, Drizzle)
   - State management (Redux, Zustand, Jotai, React Query)
   - Build tool (webpack, vite, turbopack, esbuild)

2. Check project structure to understand architecture

3. Read `CLAUDE.md` for any performance-related conventions

4. **Check TypeScript MCP** — enhances call chain analysis accuracy.

If TypeScript MCP is **not available**, ask user to install:

Use `AskUserQuestion`:

- **question**: "TypeScript MCP enhances performance analysis with accurate call chain tracking. Install it?"
- **options**:

| Option                    | Description                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Install (Recommended)** | Run `bunx @anthropic-ai/mcp-install@latest install @anthropic-ai/mcp-server-typescript --client claude` |
| **Skip**                  | Continue without TypeScript MCP (reduced accuracy)                                                      |

If user picks **Skip**, output warning and continue:

```
⚠️ Continuing without TypeScript MCP. Call chain analysis will be less accurate.
```

## Step 2: Database & Query Analysis

### N+1 Query Detection

Look for these patterns:

1. **Loop with individual queries:**

   ```typescript
   // ❌ N+1 pattern
   for (const user of users) {
     const posts = await prisma.post.findMany({ where: { authorId: user.id } });
   }
   ```

2. **Missing includes/relations:**

   ```typescript
   // ❌ Will cause N+1 when accessing user.posts later
   const users = await prisma.user.findMany();
   users.forEach((u) => console.log(u.posts)); // Each access = 1 query
   ```

3. **GraphQL resolvers without DataLoader:**
   ```typescript
   // ❌ N+1 in resolver
   @ResolveField()
   async author(@Parent() post: Post) {
     return this.userService.findById(post.authorId); // Called N times
   }
   ```

### Query Optimization Issues

- Missing indexes on frequently queried fields
- `SELECT *` when only specific fields needed
- Missing pagination on list queries
- Unbounded queries without `LIMIT`
- Sorting without index support
- Using `findMany` + filter instead of `findFirst` with condition

### Search patterns:

```
prisma.*.findMany
.find({ where
SELECT * FROM
for.*await.*find
forEach.*await
map.*await.*find
```

## Step 3: React Performance Analysis

### Unnecessary Re-renders

1. **Missing memoization:**

   ```typescript
   // ❌ New object every render
   <Component style={{ color: 'red' }} />

   // ❌ New callback every render
   <Button onClick={() => handleClick(id)} />

   // ❌ New array every render
   <List items={data.filter(x => x.active)} />
   ```

2. **Prop drilling causing cascading re-renders:**
   - Parent state change re-renders entire tree
   - Missing `React.memo` on expensive components

3. **Context misuse:**

   ```typescript
   // ❌ Entire tree re-renders on any context change
   const AppContext = createContext({ user, theme, settings, ... });
   ```

4. **Expensive computations in render:**

   ```typescript
   // ❌ Runs on every render
   const sorted = items.sort((a, b) => ...);

   // ✅ Should use useMemo
   const sorted = useMemo(() => items.sort(...), [items]);
   ```

### State Management Issues

- Storing derived state (should compute from source)
- Too granular state updates causing multiple re-renders
- Missing selector memoization in Redux/Zustand
- Fetching same data multiple times (missing cache)

### Search patterns:

```
useState.*useState.*useState
onClick={() =>
style={{
useEffect.*\[\].*fetch
createContext
```

## Step 4: Memory Leak Detection

### Common Patterns

1. **Uncleared intervals/timeouts:**

   ```typescript
   // ❌ Never cleared
   useEffect(() => {
     setInterval(() => fetchData(), 5000);
   }, []);
   ```

2. **Missing cleanup in useEffect:**

   ```typescript
   // ❌ Event listener never removed
   useEffect(() => {
     window.addEventListener("resize", handler);
   }, []);
   ```

3. **Stale closures holding references:**

   ```typescript
   // ❌ Closure holds reference to large data
   useEffect(() => {
     const data = fetchLargeData();
     return () => {
       // data still referenced
     };
   }, []);
   ```

4. **Subscriptions not unsubscribed:**

   ```typescript
   // ❌ Observable never unsubscribed
   useEffect(() => {
     someObservable$.subscribe(handler);
   }, []);
   ```

5. **WebSocket/SSE connections not closed:**
   ```typescript
   // ❌ Connection never closed
   const ws = new WebSocket(url);
   ```

### Node.js Specific

- Event emitter listeners not removed
- Stream not properly closed/destroyed
- Large objects cached indefinitely
- Circular references preventing GC

### Search patterns:

```
setInterval
setTimeout
addEventListener
subscribe
new WebSocket
EventEmitter
\.on\(
```

## Step 5: Bundle Size Analysis

### Large Dependencies

Check for:

1. **Heavy libraries with lighter alternatives:**
   - `moment` → `date-fns` or `dayjs`
   - `lodash` → `lodash-es` or native methods
   - `axios` → `fetch` (native)
   - `uuid` → `crypto.randomUUID()` (native)

2. **Importing entire library:**

   ```typescript
   // ❌ Imports entire lodash
   import _ from "lodash";

   // ✅ Tree-shakeable
   import { debounce } from "lodash-es";
   ```

3. **Dev dependencies in production:**
   - Check if dev tools imported in production code
   - `@testing-library/*` in src files
   - Type-only imports not using `import type`

4. **Duplicate dependencies:**
   - Same library in multiple versions
   - Run `npm ls <package>` to check

### Dynamic Import Opportunities

Look for:

- Large components that could be lazy loaded
- Routes without code splitting
- Heavy libraries used only in specific features

### Search patterns:

```
import.*from 'lodash'
import.*from 'moment'
require\('
```

## Step 6: API & Network Performance

### Inefficient Patterns

1. **Sequential requests that could be parallel:**

   ```typescript
   // ❌ Sequential
   const user = await getUser(id);
   const posts = await getPosts(id);

   // ✅ Parallel
   const [user, posts] = await Promise.all([getUser(id), getPosts(id)]);
   ```

2. **Missing caching:**
   - Same API called multiple times
   - No HTTP cache headers
   - No React Query/SWR caching

3. **Over-fetching:**
   - Fetching entire object when only ID needed
   - Not using GraphQL fragments efficiently

4. **Under-fetching:**
   - Multiple round trips for related data
   - Should use `include` or batch endpoints

## Output Format

````
## Performance Analysis

**Scope:** [what was analyzed]
**Framework:** [detected framework/ORM]

## Summary

| Category | Issues | Severity |
|----------|--------|----------|
| N+1 Queries | 3 | HIGH |
| Re-renders | 5 | MEDIUM |
| Memory Leaks | 1 | HIGH |
| Bundle Size | 2 | LOW |

## Findings

### 🔴 HIGH: N+1 Query in UserService

**Location:** [src/services/user.service.ts:45](src/services/user.service.ts#L45)

**Problem:**
```typescript
// Current code
for (const user of users) {
  const posts = await prisma.post.findMany({ where: { authorId: user.id } });
}
````

**Impact:** ~100 queries for 100 users instead of 1

**Fix:**

```typescript
const users = await prisma.user.findMany({
  include: { posts: true },
});
```

---

### 🟡 MEDIUM: Missing useMemo in Dashboard

**Location:** [src/components/Dashboard.tsx:23](src/components/Dashboard.tsx#L23)

**Problem:**

```typescript
const sortedItems = items.sort((a, b) => a.date - b.date);
```

**Impact:** Re-sorts on every render (~500 items)

**Fix:**

```typescript
const sortedItems = useMemo(
  () => [...items].sort((a, b) => a.date - b.date),
  [items],
);
```

---

## Recommendations

1. **Quick Wins** (low effort, high impact):
   - [specific fixes]

2. **Medium Term**:
   - [architectural improvements]

3. **Consider for Future**:
   - [larger refactoring]

```

## Severity Levels

- **CRITICAL** — Production performance issue, causes timeouts or crashes
- **HIGH** — Noticeable slowdown, N+1 queries, memory leaks
- **MEDIUM** — Suboptimal pattern, unnecessary re-renders, large bundle
- **LOW** — Micro-optimization, nice-to-have improvement

## Important

- **Read-only** — never modify code (analysis only)
- **Be specific** — every finding must reference `file:line`
- **Measure impact** — estimate the performance cost where possible
- **Prioritize** — focus on high-impact issues, skip nitpicks
- **Consider trade-offs** — some "optimizations" hurt readability without meaningful gain
- If using React, check if React DevTools Profiler findings are mentioned in any docs/issues
```
