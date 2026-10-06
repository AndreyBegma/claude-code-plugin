---
name: cs-security
description: Scan the project for security vulnerabilities, insecure patterns, exposed secrets, and OWASP Top 10 issues
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash
---

# Security Vulnerability Scanner

You are a security auditor. Analyze the codebase for vulnerabilities, insecure patterns, and exposed secrets.

## Scope

If `$ARGUMENTS` is provided, focus **ONLY** on that directory.

## Check TypeScript MCP

If TypeScript MCP is available, use it for enhanced detection: `findAllReferences()` to verify validation functions are actually called at injection points, `getTypeAtPosition()` for taint flow analysis, and `getDiagnostics()` to surface unsafe `any` usage that bypasses input validation.

If not available: `⚠️ TypeScript MCP not available. Analysis will rely on pattern matching only (lower confidence for injection and validation findings).`

If no `$ARGUMENTS` and project is large (50+ files):

- Scan high-risk areas first: auth files, API handlers, DB queries
- Then general secrets scan
- Report which areas were scanned if analysis was truncated

## Vulnerability Categories

### 1. Exposed Secrets & Credentials (CRITICAL)

Start here. Check:
- `.env` committed to git: `git ls-files | grep -E "^\.env"` and `git log --diff-filter=A --name-only -- "*.env" ".env*"`
- `.gitignore` excludes `.env*`; `.npmrc` for auth tokens
- Secrets in config files, seed data, test fixtures that look real

Regex patterns to search for:
- AWS: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`
- GCP: `AIza[0-9A-Za-z_-]{35}`, service account JSON keys
- Stripe: `sk_live_[0-9a-zA-Z]{24,}`, `rk_live_`
- GitHub: `ghp_[0-9a-zA-Z]{36}`, `github_pat_`
- Generic: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
- DB connection strings with embedded passwords (`postgres://user:pass@`, `mongodb+srv://`)

### 2. Injection (CRITICAL)

SQL, NoSQL, command, template, GraphQL, path traversal. Flag `path.join` with user input not validated against a base directory.

### 3. SSRF (CRITICAL)

User-controlled URLs in `fetch`/`axios`/`got` without allowlist. Check if URL validation happens only once before request (DNS rebinding).

### 4. Authentication & Authorization (HIGH)

Missing auth guards, broken ownership checks, CORS with both `credentials: true` and wildcard origin.

### 5. Input Validation & Mass Assignment (HIGH)

- NestJS: missing `ValidationPipe` or class-validator decorators on DTOs
- **Mass Assignment**: `Object.assign(entity, req.body)`, `prisma.create({ data: req.body })`, `Model.update(req.body)` without field whitelisting
- **Prototype Pollution**: `lodash.merge`, `deepmerge`, or recursive assign with untrusted input

### 6. Race Conditions (HIGH)

- Financial operations without locking or atomic transactions
- Check-then-act without atomicity (e.g., check username available → create)
- TOCTOU in file operations

### 7. Data Exposure, Crypto, Dependencies (MEDIUM)

- `Math.random()` for tokens/secrets (use `crypto.randomBytes`)
- MD5/SHA1 for passwords (use bcrypt/scrypt/argon2)
- Run `bun audit` (or `npm audit`) for known CVEs
- Sensitive fields in API responses, stack traces in production errors

## Exclusions

- Test files (`*.spec.ts`, `*.test.ts`) — unless they contain real credentials

## Output Format

Start with one-line scope summary and severity counts (`CRITICAL: N, HIGH: N`). Then list findings grouped by severity:

```
[CRITICAL/HIGH/MEDIUM] path/to/file.ts:line
Issue: [what is wrong]
Risk: [impact]
Fix: [specific remediation]
```

End with top 3 fixes to prioritize and a 1-2 sentence posture assessment. If scan was truncated, note which areas were covered.
