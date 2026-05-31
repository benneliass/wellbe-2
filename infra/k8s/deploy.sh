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
docker build -t wellbe-processing-worker:local -f "$REPO_ROOT/backend/apps/processing-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-safety-gate:local -f "$REPO_ROOT/backend/apps/safety-gate/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-migrations:local -f "$REPO_ROOT/db/Dockerfile.migrations" "$REPO_ROOT"

echo "=== Loading images into Kind cluster ==="
KIND_CLUSTER=$(kind get clusters | head -1)
if [ -z "$KIND_CLUSTER" ]; then
  echo "ERROR: No Kind cluster found. Create one first: kind create cluster" >&2
  exit 1
fi
echo "Using Kind cluster: $KIND_CLUSTER"

LOCAL_IMAGES=(
  wellbe-postgres:local
  wellbe-vault-writer:local
  wellbe-ingestion-worker:local
  wellbe-processing-worker:local
  wellbe-safety-gate:local
  wellbe-migrations:local
)

for img in "${LOCAL_IMAGES[@]}"; do
  echo "  Loading $img ..."
  kind load docker-image "$img" --name "$KIND_CLUSTER"
done

echo "=== Deploying via Helm ==="
helm upgrade --install $RELEASE_NAME "$CHART_DIR" \
  --namespace $NAMESPACE \
  --create-namespace \
  --server-side=false \
  --wait \
  --timeout 5m

echo "=== Deployment complete ==="
kubectl get pods -n $NAMESPACE
