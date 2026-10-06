#!/bin/sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting PostgreSQL..."
docker compose -f "$ROOT/docker/docker-compose.yml" up -d

echo "Waiting for PostgreSQL to be ready..."
until docker exec __SCOPE__-postgres pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done

cd "$ROOT/apps/api"

if [ -d prisma/migrations ] && [ -n "$(ls -A prisma/migrations 2>/dev/null)" ]; then
  echo "Applying migrations..."
  bunx prisma migrate deploy
else
  echo "No migrations yet — creating the initial one..."
  bunx prisma migrate dev --name init
fi

echo "Running seed..."
bunx prisma db seed

echo "Done. PostgreSQL is up on port __DB_PORT__"
