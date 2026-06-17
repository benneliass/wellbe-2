#!/usr/bin/env bash
# Combined port-forward + pytest runner for the pattern read e2e (WEL-79).
# Keeps the API port-forward alive for the duration of the test in one session.
set -euo pipefail

NAMESPACE=wellbe
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

kubectl port-forward -n "$NAMESPACE" svc/api 8000:8001 >/tmp/pf-api.log 2>&1 &
PF_API=$!
cleanup() { kill "$PF_API" 2>/dev/null || true; }
trap cleanup EXIT

# Wait for the forward to accept connections.
for _ in $(seq 1 20); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 0.5
done

cd "$REPO_ROOT/backend"
PKGS=$(ls -d packages/*/src | tr '\n' ':')
export PYTHONPATH="apps/api/src:${PKGS}"
export API_URL="http://localhost:8000"
uv run --no-project pytest "$REPO_ROOT/tests/e2e/test_patterns_roundtrip.py" -v --tb=short "$@"
