#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHART_DIR="$REPO_ROOT/infra/helm/wellbe-local"
NAMESPACE=wellbe
RELEASE_NAME=wellbe-local

# Dev workspace identity — single source of truth is devSeed.patientId in
# values.yaml. We bake the same id into the web image (NEXT_PUBLIC_WELLBE_DEV_*)
# so the browser session and the seeded backend data point at the same patient.
DEV_PATIENT_ID="$(grep -A4 '^devSeed:' "$CHART_DIR/values.yaml" \
  | grep 'patientId:' | head -1 | awk '{print $2}' | tr -d '"')"
if [ -z "$DEV_PATIENT_ID" ]; then
  echo "ERROR: could not read devSeed.patientId from values.yaml" >&2
  exit 1
fi
echo "Dev workspace identity: $DEV_PATIENT_ID"

echo "=== Building Docker images ==="
docker build -t wellbe-postgres:local -f "$REPO_ROOT/infra/local/Dockerfile.postgres" "$REPO_ROOT/infra/local"
docker build -t wellbe-vault-writer:local -f "$REPO_ROOT/backend/apps/vault-writer/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-ingestion-worker:local -f "$REPO_ROOT/backend/apps/ingestion-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-processing-worker:local -f "$REPO_ROOT/backend/apps/processing-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-safety-gate:local -f "$REPO_ROOT/backend/apps/safety-gate/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-api:local -f "$REPO_ROOT/backend/apps/api/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-audit-service:local -f "$REPO_ROOT/backend/apps/audit-service/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-continuity-worker:local -f "$REPO_ROOT/backend/apps/continuity-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-web:local -f "$REPO_ROOT/apps/web/Dockerfile" "$REPO_ROOT" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID=$DEV_PATIENT_ID" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID=$DEV_PATIENT_ID" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE=controller" \
  --build-arg "NEXT_PUBLIC_WELLBE_API_URL=http://api.localhost"
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
  wellbe-api:local
  wellbe-audit-service:local
  wellbe-continuity-worker:local
  wellbe-web:local
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
