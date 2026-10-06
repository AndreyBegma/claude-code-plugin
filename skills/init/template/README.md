# __TITLE__

## Requirements

- [Bun](https://bun.sh) __BUN_VERSION__+
- Node.js __NODE_MAJOR__+
- Docker (for PostgreSQL)

## Getting started

```bash
bun install
bun run db:setup     # PostgreSQL on :__DB_PORT__, migrations, seed
bun run start:dev    # api → http://localhost:__API_PORT__  ·  web → http://localhost:__WEB_PORT__
```

Health check: `curl http://localhost:__API_PORT__/health`

## Workspaces

| Path | Package | Stack |
|---|---|---|
| `apps/api` | `@__SCOPE__/api` | NestJS 11, Prisma 7, PostgreSQL |
| `apps/web` | `@__SCOPE__/web` | Next.js 16, React 19, Tailwind CSS 4 |
| `packages/shared` | `@__SCOPE__/shared` | shared TypeScript |

See `CLAUDE.md` for all commands and conventions.
