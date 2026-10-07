# __TITLE__

Fullstack monorepo — Bun workspaces + Turborepo.

## Structure

```
apps/
  api/        — NestJS 11 API, Prisma 7 (PostgreSQL, pg driver adapter)   :__API_PORT__
  web/        — Next.js 16 (App Router, Turbopack), React 19, Tailwind 4   :__WEB_PORT__
packages/
  shared/     — @__SCOPE__/shared — code shared by api and web
docker/       — docker-compose: PostgreSQL 16                             :__DB_PORT__
scripts/      — db-start-docker.sh (up → migrate → seed)
```

## Commands

| Command | What it does |
|---|---|
| `bun install` | install all workspaces |
| `bun run db:setup` | start PostgreSQL, apply migrations, seed |
| `bun run start:dev` | api + web in watch mode |
| `bun run build` | build everything (turbo, cached) |
| `bun run lint` / `bun run test` | lint (Biome) / tests (Jest in api) |
| `bun run check` | Biome lint + format + import order, no writes |
| `bun run db:migrate` | `prisma migrate dev` — create and apply a migration |
| `bun run db:generate` | regenerate the Prisma client |
| `bun run db:studio` | Prisma Studio |

## Conventions

- **Bun** is the package manager; versions are pinned exactly (`bunfig.toml`). Never `npm install` / `yarn`.
- **Biome** is the only linter and formatter — single quotes, trailing commas, 2 spaces. No ESLint / Prettier.
- **Prisma is imported only by `apps/api`** — through `PrismaService` (`src/database/`). The web app talks to the API over HTTP, never to the database.
- Schema changes go through `prisma migrate dev` with a descriptive name; never edit an applied migration.
- Shared types and pure helpers go in `packages/shared`; it must stay framework-free.
- API: global `ValidationPipe` (`whitelist`, `forbidNonWhitelisted`) — every input is a DTO with `class-validator` decorators. `helmet` and CORS (`WEB_URL`) are on.
- Environment: `docker/.env` and `apps/*/.env` (git-ignored), documented in `.env.example`. The database password lives only in `docker/.env` and `apps/api/.env` — never in a committed file; the two must match. Add a variable to the example in the same change that reads it.
- TypeScript strict everywhere; no `any`.
- Tests: `*.spec.ts` next to the code (api). A bug fix comes with the test that would have caught it.
