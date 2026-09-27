#!/usr/bin/env bash
set -euo pipefail

# Build the WellBe backend/data images and load them into a kind cluster.
#
# The chart runs these as `:local` tags with imagePullPolicy: Never, so every
# one of them must be present on the kind node before `helm install`, or the
# pods (and the alembic-migrate / dev-seed hooks) sit in ErrImageNeverPull.
# The web image is built separately by the callers (deploy.sh bakes dev build
# args into it; deploy-and-smoke.sh rebuilds it for the smoke gate).
#
# Usage: bash infra/k8s/build-images.sh [kind-cluster-name]
# Defaults to the first cluster from `kind get clusters`.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

KIND_CLUSTER="${1:-$(kind get clusters | head -1)}"
if [ -z "$KIND_CLUSTER" ]; then
  echo "ERROR: No Kind cluster found. Create one first: kind create cluster" >&2
  exit 1
fi

# image tag | Dockerfile | build context
IMAGES=(
  "wellbe-postgres:local|infra/local/Dockerfile.postgres|infra/local"
  "wellbe-vault-writer:local|backend/apps/vault-writer/Dockerfile|."
  "wellbe-ingestion-worker:local|backend/apps/ingestion-worker/Dockerfile|."
  "wellbe-processing-worker:local|backend/apps/processing-worker/Dockerfile|."
  "wellbe-safety-gate:local|backend/apps/safety-gate/Dockerfile|."
  "wellbe-api:local|backend/apps/api/Dockerfile|."
  "wellbe-audit-service:local|backend/apps/audit-service/Dockerfile|."
  "wellbe-continuity-worker:local|backend/apps/continuity-worker/Dockerfile|."
  "wellbe-notification-worker:local|backend/apps/notification-worker/Dockerfile|."
  "wellbe-migrations:local|db/Dockerfile.migrations|."
)

echo "=== Building Docker images ==="
for entry in "${IMAGES[@]}"; do
  IFS='|' read -r tag dockerfile context <<<"$entry"
  echo "  Building $tag ..."
  docker build -t "$tag" -f "$REPO_ROOT/$dockerfile" "$REPO_ROOT/$context"
done

echo "=== Loading images into Kind cluster: $KIND_CLUSTER ==="
for entry in "${IMAGES[@]}"; do
  tag="${entry%%|*}"
  echo "  Loading $tag ..."
  kind load docker-image "$tag" --name "$KIND_CLUSTER"
done
