#!/usr/bin/env bash
# Start all local data services (Postgres, Redis, MinIO, Temporal, ZITADEL).
# Application services run separately via `uv run` in the backend.
set -euo pipefail

cd "$(dirname "$0")/../infra/local"

echo "Starting WellBe local data services..."
docker compose up -d

echo ""
echo "Services:"
echo "  Postgres:      localhost:5432"
echo "  Redis:         localhost:6379"
echo "  MinIO:         localhost:9000  (console: localhost:9001)"
echo "  Temporal:      localhost:7233  (UI: localhost:8080)"
echo "  ZITADEL:       localhost:8090"
echo ""
echo "Run migrations:"
echo "  cd db && DATABASE_URL=postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe uv run alembic upgrade head"
