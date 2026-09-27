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

KIND_CLUSTER=$(kind get clusters | head -1)
if [ -z "$KIND_CLUSTER" ]; then
  echo "ERROR: No Kind cluster found. Create one first: kind create cluster" >&2
  exit 1
fi
echo "Using Kind cluster: $KIND_CLUSTER"

bash "$SCRIPT_DIR/build-images.sh" "$KIND_CLUSTER"

echo "=== Building + loading web image ==="
docker build -t wellbe-web:local -f "$REPO_ROOT/apps/web/Dockerfile" "$REPO_ROOT" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID=$DEV_PATIENT_ID" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID=$DEV_PATIENT_ID" \
  --build-arg "NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE=controller" \
  --build-arg "NEXT_PUBLIC_WELLBE_API_URL=http://api.localhost"
kind load docker-image wellbe-web:local --name "$KIND_CLUSTER"

echo "=== Deploying via Helm ==="
helm upgrade --install $RELEASE_NAME "$CHART_DIR" \
  --namespace $NAMESPACE \
  --create-namespace \
  --server-side=false \
  --wait \
  --timeout 5m

echo "=== Deployment complete ==="
kubectl get pods -n $NAMESPACE
