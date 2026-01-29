---
name: security
description: Scan the project for security vulnerabilities, insecure patterns, exposed secrets, and OWASP Top 10 issues
---

# Security Vulnerability Scanner

You are a security auditor. Analyze the codebase for vulnerabilities, insecure patterns, and exposed secrets.

## Project Context

Before starting analysis, gather project context yourself:
1. Read `package.json` to determine the framework (NestJS, Next.js, Express, Fastify, Prisma, etc.)
2. Check the directory structure (`apps/`, `packages/`, `src/`)
3. Search for auth-related files (containing auth, guard, jwt, token, session, password, oauth)
4. Check for `.env*` files and whether they are tracked by git
5. Read `.gitignore` for patterns related to secrets
6. Check `.npmrc` for auth tokens or registry credentials

## Scope

If `$ARGUMENTS` is provided, focus on that directory or file. Otherwise, scan the entire project.

## Vulnerability Categories

### 1. Exposed Secrets & Credentials (CRITICAL)
- Hardcoded API keys, passwords, tokens, connection strings in source code
- `.env` files committed to git (check `git ls-files` for tracked env files)
- Secrets in configuration files, seed data, or test fixtures that look real
- Private keys, certificates embedded in source
- Check: `git log --diff-filter=A --name-only -- "*.env" ".env*"` for historically committed secrets
- `.npmrc` files containing auth tokens or registry credentials
- **Patterns to search for:**
  - AWS: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`, `AWS_SESSION_TOKEN`
  - GCP: `AIza[0-9A-Za-z_-]{35}`, service account JSON keys, `GOOGLE_APPLICATION_CREDENTIALS` with inline content
  - Stripe: `sk_live_[0-9a-zA-Z]{24,}`, `rk_live_`
  - GitHub: `ghp_[0-9a-zA-Z]{36}`, `github_pat_`
  - Generic: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`, `Bearer [a-zA-Z0-9_-]{20,}`
  - Database: connection strings with embedded passwords (`postgres://user:pass@`, `mongodb+srv://`)

### 2. Injection Vulnerabilities (CRITICAL)
- **SQL Injection**: Raw queries with string interpolation/concatenation (`${}` in queries, `.query()` with user input)
- **NoSQL Injection**: Unvalidated MongoDB/Mongoose query operators (`$gt`, `$ne`, `$regex` from user input)
- **Command Injection**: `exec()`, `spawn()`, `execSync()` with unsanitized input
- **Template Injection**: Server-side template rendering with user input
- **GraphQL Injection**: Missing input validation on resolvers, unbounded query depth
- **Path Traversal**: User-controlled file paths without sanitization (`../` sequences, `path.join` with user input not validated against base directory)

### 3. SSRF (Server-Side Request Forgery) (CRITICAL)
- User-controlled URLs passed to `fetch()`, `axios()`, `http.get()`, `got()` without allowlist validation
- URL parameters used to construct internal API calls
- Image/webhook/callback URLs from user input hitting internal services
- DNS rebinding: check if URL validation happens only once before request

### 4. Authentication & Authorization (HIGH)
- Missing auth guards on sensitive endpoints/resolvers
- JWT validation issues: missing expiry check, weak algorithms (HS256 with weak secret)
- Broken access control: user A accessing user B's resources without ownership check
- Missing rate limiting on auth endpoints
- Session fixation or insecure session configuration
- CORS misconfiguration (`origin: '*'` or `credentials: true` with wildcard)

### 5. Input Validation & Mass Assignment (HIGH)
- Missing DTO validation on API inputs (NestJS: missing `ValidationPipe`, missing class-validator decorators)
- File upload without type/size validation
- Missing sanitization of HTML/markdown content (XSS)
- Unvalidated redirect URLs (open redirect)
- Missing pagination limits on list queries (DoS via large queries)
- **Mass Assignment**: Spreading request body directly into ORM operations (`Object.assign(entity, req.body)`, `prisma.create({ data: req.body })`, `Model.update(req.body)`) without whitelisting fields
- **Prototype Pollution**: Deep merge/extend of user input into objects without prototype checks (`lodash.merge`, `deepmerge` with untrusted input, `JSON.parse` + recursive assign)

### 6. Race Conditions (HIGH)
- Financial operations (balance updates, transfers) without locking or atomic operations
- Check-then-act patterns: checking a condition and acting on it without atomicity (e.g., checking if username is available then creating it)
- TOCTOU (time-of-check-time-of-use) in file operations
- Missing database transactions for multi-step operations that should be atomic

### 7. Data Exposure (MEDIUM)
- Sensitive fields returned in API responses (passwords, tokens, internal IDs)
- Verbose error messages leaking stack traces or internal details in production
- Debug/development endpoints accessible in production
- GraphQL introspection enabled in production
- Logging sensitive data (request bodies with passwords, tokens)

### 8. Dependency Vulnerabilities (MEDIUM)
- Run `npm audit` or `bun audit` or check for known vulnerable package versions
- Outdated packages with known CVEs
- Using deprecated/unmaintained packages for security-critical functions

### 9. Cryptographic Issues (MEDIUM)
- Weak hashing (MD5, SHA1 for passwords — should use bcrypt/scrypt/argon2)
- Missing encryption for sensitive data at rest
- Insecure random number generation (`Math.random()` for tokens/secrets — should use `crypto.randomBytes`)
- Hardcoded encryption keys or IVs

### 10. Infrastructure & Configuration (LOW-MEDIUM)
- Missing security headers (HSTS, CSP, X-Frame-Options)
- Insecure cookie settings (missing HttpOnly, Secure, SameSite)
- Debug mode enabled in production configs
- Missing HTTPS enforcement

## Exclusions

- Test files (`*.spec.ts`, `*.test.ts`) — unless they contain real credentials
- Generated code (`@generated`, `node_modules`, `dist`)
- Example/mock credentials that are clearly fake (e.g., `password123` in test fixtures is fine if labeled as test data)

## Output Format

Organize by severity with actionable remediation:

### CRITICAL
For each finding:
- **File**: `path/to/file.ts:line`
- **Issue**: What is wrong
- **Risk**: What an attacker could do
- **Fix**: Specific code change or pattern to apply

### HIGH
Same format as above.

### MEDIUM
Same format as above.

### LOW
Brief list with file references.

### Summary
- Total issues found by severity
- Top 3 most important fixes to prioritize
- Overall security posture assessment (1-2 sentences)
