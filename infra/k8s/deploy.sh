#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHART_DIR="$REPO_ROOT/infra/helm/wellbe-local"
NAMESPACE=wellbe
RELEASE_NAME=wellbe-local

echo "=== Building Docker images ==="
docker build -t wellbe-postgres:local -f "$REPO_ROOT/infra/local/Dockerfile.postgres" "$REPO_ROOT/infra/local"
docker build -t wellbe-vault-writer:local -f "$REPO_ROOT/backend/apps/vault-writer/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-ingestion-worker:local -f "$REPO_ROOT/backend/apps/ingestion-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-migrations:local -f "$REPO_ROOT/db/Dockerfile.migrations" "$REPO_ROOT"

echo "=== Deploying via Helm ==="
helm upgrade --install $RELEASE_NAME "$CHART_DIR" \
  --namespace $NAMESPACE \
  --create-namespace \
  --wait \
  --timeout 5m

echo "=== Deployment complete ==="
kubectl get pods -n $NAMESPACE
