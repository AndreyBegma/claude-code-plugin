---
name: cs-init
description: Scaffold a new fullstack monorepo — Bun workspaces + Turborepo, NestJS 11 + Prisma 7 + PostgreSQL (docker), Next.js 16 + React 19 + Tailwind 4, a shared package, Biome, Jest. Asks for the project name, location and the API / web / database ports (checked free), then generates, installs, creates the initial migration, verifies the build and health check, and optionally commits and creates the GitHub repository
argument-hint: "[project-name] [target-dir]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
---

# Init — fullstack project scaffold

You create a new project from the template bundled with this skill and leave it
**verified working**: installed, linted, tested, built, database migrated and
seeded, API answering `/health`. A scaffold that was never run is a guess.

## What it generates

```
<project>/
  apps/api/          NestJS 11 · Prisma 7 (pg adapter) · helmet · CORS · ValidationPipe · Jest
  apps/web/          Next.js 16 (App Router, Turbopack) · React 19 · Tailwind CSS 4
  packages/shared/   @<scope>/shared — TypeScript shared by api and web
  docker/            docker-compose: PostgreSQL 16 (compose project named after the scope)
  scripts/           db-start-docker.sh — up → wait → migrate (creates `init` on first run) → seed
  biome.json · turbo.json · tsconfig.json · bunfig.toml (exact versions) · .npmrc
  CLAUDE.md · README.md · .code-analyzer-config.json (orchestrator settings prefilled)
```

The template is `${CLAUDE_SKILL_DIR}/template/` and the generator is
`${CLAUDE_SKILL_DIR}/scaffold.sh`. **Never hand-copy template files** — the
script substitutes every placeholder and refuses to finish if one is left.

## Step 1 — Preflight

Run, in one `Bash` call each where useful:

```sh
bun --version; node --version; docker --version; docker compose version; git --version; gh auth status
```

| Missing | Do |
|---|---|
| `bun` | stop — `curl -fsSL https://bun.sh/install \| bash` |
| `node` (< 20) | stop — Next.js 16 and Prisma 7 need a current Node; suggest `fnm install --lts` |
| `docker` / compose | continue; the database steps become optional and are reported as skipped |
| `gh` not authenticated | continue; the GitHub step is not offered |

## Step 2 — The interview

Facts first, questions second: before asking, compute the defaults so every
question carries a recommended answer.

### 2.1 Find free ports

A port is taken if anything listens on it **or** a container publishes it:

```sh
ss -ltnH 2>/dev/null | awk '{print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | sort -un
docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE ':[0-9]+->' | tr -d ':->' | sort -un
```

For each role, the recommendation is the first free port at or above its
conventional default:

| Role | Conventional default |
|---|---|
| API | 8080 |
| Web | 3000 |
| PostgreSQL | 5433 (5432 is left for a local server) |

Three ports must also differ from each other.

### 2.2 Ask

Parse `$ARGUMENTS` first: a first token that looks like a slug is the project
name; a path is the target directory. Do not ask what was given.

**Round 1** — one `AskUserQuestion` call with up to four questions. Each port
question offers the computed free port as **(Recommended)**, the conventional
default (with "busy" in its description if it is), and one more free alternative;
the person can type any port in "Other".

| Header | Question | Options |
|---|---|---|
| `Name` | What is the project called? (package scope `@name/*`, database name, container name) | the target directory's basename as a slug (Recommended) · "Other" to type one |
| `API port` | Which port should the NestJS API listen on? | `<free>` (Recommended) · `8080` · `<next free>` |
| `Web port` | Which port should the Next.js app run on? | `<free>` (Recommended) · `3000` · `<next free>` |
| `DB port` | Which host port should PostgreSQL be published on? | `<free>` (Recommended) · `5433` · `<next free>` |

**Round 2** — one `AskUserQuestion` call:

| Header | Question | Options |
|---|---|---|
| `Location` | Where should it be created? | `./<name>` (Recommended) · the current directory (only if it is empty) · "Other" for a path |
| `Title` | Display name for the UI and docs? | `<Name in Title Case>` (Recommended) · "Other" |
| `Setup` (multiSelect) | What should I run after generating? | **Install dependencies** · **Start PostgreSQL, create the initial migration and seed** (only with docker) · **git init + initial commit** · **Create a private GitHub repository and push** (only with `gh`) |
| `Example` | Keep the example `User` model, seed and health endpoint? | Keep (Recommended) — the migration and the smoke test use them · Remove the `User` model and seed (health endpoint stays) |

Then **validate the answers** and re-ask only what failed:

- name: lowercase letters, digits, `-`; not starting with `-`. Offer the
  slugified version of whatever was typed.
- every port: a number 1024–65535, free (re-run 2.1 if the person typed one),
  and different from the other two.
- location: does not exist, or is an empty directory. Never write into a
  non-empty directory, never overwrite.
- a GitHub repository with that name must not already exist
  (`gh repo view <owner>/<name>` fails).

**Round 3 — confirm.** Print the summary — name, title, path, the three ports,
the database name and container name, the setup steps — and `AskUserQuestion`:
**Create (Recommended)** · **Change something** · **Cancel**.

## Step 3 — Generate

```sh
${CLAUDE_SKILL_DIR}/scaffold.sh <path> <name> "<Title>" <api-port> <web-port> <db-port>
```

It copies the template, substitutes every placeholder, renames the dotfiles,
creates `apps/api/.env` and `apps/web/.env.local` from the examples (with a
random local database password), and fails if any placeholder remains. Show its
output.

If the person chose to remove the example: delete the `User` model from
`apps/api/prisma/schema.prisma` and replace the body of `main()` in
`apps/api/prisma/seed.ts` with a comment saying where seed data goes — with
`Edit`, after generation.

## Step 4 — Set up, in order, each step only if chosen

Run from the project root. Stop at the first failure, show the real output, and
say what was done and what was not.

1. **Install** — `timeout 300 bun install || timeout 300 bun install` (the retry
   is for a stalled connection, not a hidden error), then `bun run db:generate`.
2. **Database** — `bun run db:setup`. On the first run the script creates the
   `init` migration with `prisma migrate dev`, then seeds. If the port turns out
   to be taken after all (`address already in use`), say so and offer to change
   it: edit `docker/docker-compose.yml`, `apps/api/.env`, `apps/api/.env.example`,
   `CLAUDE.md`, `README.md`, `scripts/db-start-docker.sh`.
3. **Verify** — always, when dependencies are installed:
   ```sh
   bun run check
   bun run test
   bun run build
   ```
   With the database up, also start the built API, probe it, and stop it by the
   PID you captured — never by name:
   ```sh
   (cd apps/api && node dist/src/main > /tmp/<name>-api.log 2>&1 & echo $!)
   curl -sf http://localhost:<api-port>/health
   kill <pid>
   ```
4. **Git** — `git init -b main`, `git add -A`, `git commit -m "chore: initial
   project setup"`. Before committing, confirm `.env` files are ignored
   (`git check-ignore apps/api/.env`). Respect the person's commit rules — no
   attribution trailer if their instructions forbid it.
5. **GitHub** — only if chosen, and only after the commit:
   `gh repo create <name> --private --source . --push`. This publishes code; it
   was confirmed in Round 3, do not do it otherwise.

## Step 5 — Report

```
✅ <Title> created at <path>

  api   http://localhost:<api-port>   (/health ✓)
  web   http://localhost:<web-port>
  db    postgres://localhost:<db-port>/<db name>  (container <name>-postgres)

  check ✓ · test ✓ (1) · build ✓ · migration init ✓ · seed ✓
  git: <commit sha> · GitHub: <url | not created>

Next:
  cd <path> && bun run start:dev
  /code-sentinel:spec   — specify the first feature
```

Mark anything skipped as skipped, and anything failed as failed with its output.
Never report a step as done that was not run.

## Never

- Write into a directory that is not empty, or overwrite an existing project.
- Pick a port that is in use, or the same port for two roles.
- Commit `.env` files or print the database password into chat beyond the
  location it was written to.
- Create a GitHub repository or push without the person choosing it.
- Leave containers or processes you started for verification running, except
  the database container (that is the point of `db:setup`).
- Hand-edit template files in the plugin; changes to the template are made in
  `${CLAUDE_SKILL_DIR}/template/` and verified by generating a throwaway project.
