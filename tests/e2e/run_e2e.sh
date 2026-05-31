#!/usr/bin/env bash
set -euo pipefail

NAMESPACE=wellbe

echo "=== Setting up port-forwards ==="
kubectl port-forward svc/vault-writer 8002:8002 -n $NAMESPACE &
PF_VAULT=$!
kubectl port-forward svc/ingestion-worker 8003:8003 -n $NAMESPACE &
PF_INGESTION=$!
kubectl port-forward svc/processing-worker 8004:8004 -n $NAMESPACE &
PF_PROCESSING=$!

sleep 3

cleanup() {
    kill $PF_VAULT $PF_INGESTION $PF_PROCESSING 2>/dev/null || true
}
trap cleanup EXIT

echo "=== Running E2E tests ==="
export VAULT_WRITER_URL=http://localhost:8002
export INGESTION_WORKER_URL=http://localhost:8003
export PROCESSING_WORKER_URL=http://localhost:8004

cd "$(dirname "$0")/../.."
python -m pytest tests/e2e/ -v --tb=short "$@"
