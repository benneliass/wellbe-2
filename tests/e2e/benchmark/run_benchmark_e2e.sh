#!/usr/bin/env bash
# Run the benchmark E2E validation against the live kind cluster.
#
# It port-forwards the ingestion-worker and Postgres, then runs the benchmark
# pytest suite, which RESETS the pipeline tables, seeds all five cases in blind mode,
# waits for processing to settle, and asserts the deterministic "should-be" results
# from docs/analysis/benchmark-expected-results.md.
#
# Usage:
#   tests/e2e/benchmark/run_benchmark_e2e.sh [extra pytest args]
set -euo pipefail

NAMESPACE=wellbe

echo "=== Port-forwarding ingestion-worker (8003) and Postgres (5432) ==="
kubectl port-forward svc/ingestion-worker 8003:8003 -n "$NAMESPACE" >/dev/null 2>&1 &
PF_INGEST=$!
kubectl port-forward svc/wellbe-postgres 5432:5432 -n "$NAMESPACE" >/dev/null 2>&1 &
PF_PG=$!

cleanup() {
  kill "$PF_INGEST" "$PF_PG" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for the forwards to accept connections.
sleep 4

export INGESTION_WORKER_URL="${INGESTION_WORKER_URL:-http://localhost:8003}"
export WELLBE_PG_DSN="${WELLBE_PG_DSN:-postgresql://wellbe:wellbe_dev@localhost:5432/wellbe}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

# Prefer the dedicated E2E venv (created via: uv venv tests/e2e/.venv &&
# VIRTUAL_ENV=tests/e2e/.venv uv pip install -r tests/e2e/requirements.txt).
if [[ -x "tests/e2e/.venv/bin/python" ]]; then
  PY="tests/e2e/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

echo "=== Running benchmark E2E (reset -> seed -> settle -> assert) ==="
"$PY" -m pytest tests/e2e/benchmark/ -v --tb=short "$@"
