# Severity Levels

Use these criteria to classify findings. When in doubt, prefer the **higher** severity.

## CRITICAL

**Must fix before merge.** The code will cause harm in production.

- **Security exploits**: SQL/NoSQL/command injection, XSS, SSRF, auth bypass, exposed secrets/credentials
- **Data loss or corruption**: missing transactions, race conditions that destroy data, incorrect CASCADE deletes
- **Service outage**: unhandled promise rejection that crashes the process, infinite loops, OOM-guaranteed patterns
- **Privacy violations**: PII leaks in logs, missing access control on sensitive endpoints

**Rule of thumb:** an attacker or unlucky user triggers real damage without any unusual conditions.

## HIGH

**Should fix before merge.** The code will break under realistic conditions.

- **Logic errors with user impact**: wrong calculation, missing edge case that affects real users (null user, empty array, 0 values)
- **Missing auth/authz guards**: endpoints accessible without required role or permission check
- **Missing error handling on I/O**: unhandled DB/API/file errors that surface as 500 or crash
- **Incorrect async**: missing `await`, fire-and-forget on operations that must complete, unhandled promise chains
- **Breaking API contracts**: response shape doesn't match types/docs, missing required fields

**Rule of thumb:** happens in normal usage, not just contrived scenarios.

## MEDIUM

**Improve before or after merge.** Code works but is fragile, slow, or hard to maintain.

- **Performance**: N+1 queries, missing DB indexes for queried fields, unnecessary re-renders on every keystroke, large bundle imports (`import _ from 'lodash'`)
- **Dead code introduced by the change**: unused imports, unreachable branches, variables written but never read
- **Type safety holes**: `any` without justification, unsafe type assertions (`as`), non-null assertions (`!`) on nullable values
- **Missing validation**: no input validation on user-facing endpoints (not a security exploit, but returns confusing errors)
- **Error swallowing**: empty catch blocks, `catch(() => {})`, errors logged but not re-thrown where needed

**Rule of thumb:** won't break today, but will cause pain at scale or during the next change.

## LOW

**Nice to fix.** Style and consistency improvements.

- **Naming**: inconsistent casing, unclear abbreviations, single-letter vars outside loops
- **Style**: missing destructuring, `let` that should be `const`, deep nesting instead of early return
- **Import ordering**: not matching project conventions
- **Minor duplication**: small repeated pattern that could be a helper (but isn't blocking)
- **Missing braces**: single-line `if` without braces (if project style requires them)

**Rule of thumb:** doesn't affect behavior or performance — only readability and consistency.

---

## Severity Decision Shortcuts

| Signal | Severity |
|--------|----------|
| Exploitable by attacker | CRITICAL |
| Data loss possible | CRITICAL |
| Crashes process | CRITICAL |
| Wrong result for user | HIGH |
| Missing auth check | HIGH |
| Unhandled error on I/O | HIGH |
| Slow but correct | MEDIUM |
| `any` / type assertion | MEDIUM |
| Dead code / unused import | MEDIUM |
| Naming / style only | LOW |
