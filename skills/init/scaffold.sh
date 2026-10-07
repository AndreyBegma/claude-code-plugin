#!/usr/bin/env bash
#
# Generate a fullstack monorepo (Bun + Turborepo, NestJS + Prisma + PostgreSQL,
# Next.js + Tailwind, shared package, Biome) from ./template.
#
#   scaffold.sh <target-dir> <scope> <title> [api-port] [web-port] [db-port]
#
#   target-dir  must not exist, or be empty
#   scope       lowercase package scope / project slug: acme -> @acme/api
#   title       display name: "Acme"
#
# Prints the generated values (including the random local database password).
set -euo pipefail

TARGET=${1:?target directory required}
SCOPE=${2:?scope required, e.g. acme}
TITLE=${3:?title required, e.g. Acme}
API_PORT=${4:-8080}
WEB_PORT=${5:-3000}
DB_PORT=${6:-5433}

case "$SCOPE" in
  *[!a-z0-9-]*|-*|'') echo "scaffold: scope must be lowercase letters, digits and '-', got '$SCOPE'" >&2; exit 1 ;;
esac
for p in "$API_PORT" "$WEB_PORT" "$DB_PORT"; do
  case "$p" in ''|*[!0-9]*) echo "scaffold: ports must be numbers, got '$p'" >&2; exit 1 ;; esac
done
case "$TITLE" in
  *[\|\&\\]*) echo "scaffold: title must not contain | & or \\" >&2; exit 1 ;;
esac

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "scaffold: $TARGET exists and is not empty — refusing to write into it" >&2
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="${SCOPE//-/_}"
DB_PASSWORD="$(head -c 18 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 20)"
BUN_VERSION="$(bun --version 2>/dev/null || echo 1.3.11)"
NODE_MAJOR="$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)"
NODE_MAJOR="${NODE_MAJOR:-24}"

mkdir -p "$TARGET"
cp -R "$HERE/template/." "$TARGET/"
cd "$TARGET"

# Dotfiles travel as _name so the plugin repository does not treat them as its own.
mv _gitignore .gitignore
mv _npmrc .npmrc
mv _code-analyzer-config.json .code-analyzer-config.json
mv _CLAUDE.md CLAUDE.md
mv apps/api/_env.example apps/api/.env.example
mv apps/web/_env.example apps/web/.env.example
mv docker/_env.example docker/.env.example

grep -rlE '__(SCOPE|TITLE|DB_NAME|DB_PORT|API_PORT|WEB_PORT|BUN_VERSION|NODE_MAJOR)__' . | while read -r f; do
  sed -i.bak \
    -e "s|__SCOPE__|$SCOPE|g" \
    -e "s|__TITLE__|$TITLE|g" \
    -e "s|__DB_NAME__|$DB_NAME|g" \
    -e "s|__DB_PORT__|$DB_PORT|g" \
    -e "s|__API_PORT__|$API_PORT|g" \
    -e "s|__WEB_PORT__|$WEB_PORT|g" \
    -e "s|__BUN_VERSION__|$BUN_VERSION|g" \
    -e "s|__NODE_MAJOR__|$NODE_MAJOR|g" \
    "$f"
  rm -f "$f.bak"
done

# The random password lives only in these two git-ignored files; the committed
# examples keep "change-me".
sed "s|change-me|$DB_PASSWORD|g" docker/.env.example > docker/.env
sed "s|change-me|$DB_PASSWORD|g" apps/api/.env.example > apps/api/.env
cp apps/web/.env.example apps/web/.env.local
chmod +x scripts/db-start-docker.sh

if grep -rqE '__[A-Z_]+__' . ; then
  echo "scaffold: unreplaced placeholders remain:" >&2
  grep -rnE '__[A-Z_]+__' . >&2
  exit 1
fi

echo "scaffolded $TITLE (@$SCOPE) in $(pwd)"
echo "  api :$API_PORT · web :$WEB_PORT · postgres :$DB_PORT (db $DB_NAME, container $SCOPE-postgres)"
echo "  local db password written to docker/.env and apps/api/.env (both git-ignored)"
