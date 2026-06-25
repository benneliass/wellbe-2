#!/usr/bin/env bash
set -euo pipefail

# Repeatable web deploy + smoke gate (Track 0.6, WEL-156).
#
# Builds the web image, loads it into the kind cluster, deploys via Helm
# (Helm-managed only — no raw `kubectl apply`, per infra-constraints.mdc),
# actively monitors the web rollout (per infra-live-monitoring.mdc), waits for
# ingress reachability, then runs the Playwright Home smoke against the LIVE
# cluster ingress. Read-only kubectl (rollout status / get) is monitoring, not
# mutation. This is the gate the build-out plan's "deploy to local kind when all
# checks pass" refers to for the web surface.
#
# Usage: bash infra/k8s/deploy-and-smoke.sh
# Env overrides: WEB_HOST (default app.localhost), NAMESPACE, RELEASE_NAME.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHART_DIR="$REPO_ROOT/infra/helm/wellbe-local"
NAMESPACE="${NAMESPACE:-wellbe}"
RELEASE_NAME="${RELEASE_NAME:-wellbe-local}"
WEB_HOST="${WEB_HOST:-app.localhost}"
BASE_URL="http://${WEB_HOST}"

echo "=== Building web image (wellbe-web:local) ==="
docker build -t wellbe-web:local -f "$REPO_ROOT/apps/web/Dockerfile" "$REPO_ROOT"

echo "=== Loading web image into kind ==="
KIND_CLUSTER="$(kubectl config current-context | sed 's/^kind-//')"
if [ -z "$KIND_CLUSTER" ]; then
  echo "ERROR: could not derive kind cluster from current kube-context" >&2
  exit 1
fi
echo "Using kind cluster: $KIND_CLUSTER"
kind load docker-image wellbe-web:local --name "$KIND_CLUSTER"

echo "=== Deploying via Helm ==="
# No --wait here: we monitor the web rollout explicitly so the gate fails fast on
# web instead of blocking on the whole stack. Helm still blocks on chart hooks
# (e.g. the alembic-migrate Job); a fresh kind runner must pull the heavy custom
# Postgres image (AGE + Timescale) before that hook can run, which can exceed the
# default 5m hook timeout — so give hooks a longer window.
helm upgrade --install "$RELEASE_NAME" "$CHART_DIR" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --timeout 12m

# The web image uses the immutable tag wellbe-web:local. Helm sees no spec change
# across rebuilds, so it would keep the old pod running even though a fresh image
# was just loaded into the node. Force a rollout so the gate always verifies the
# code we just built — not a stale image. The `|| true` tolerates the first-ever
# install where helm has only just created the deployment; `rollout status` then
# covers the resulting rollout either way.
echo "=== Forcing web rollout (immutable :local tag) ==="
kubectl rollout restart deployment/web -n "$NAMESPACE" 2>/dev/null || true

echo "=== Monitoring web rollout ==="
kubectl rollout status deployment/web -n "$NAMESPACE" --timeout=180s

echo "=== Waiting for ingress at ${BASE_URL} ==="
ingress_up=""
for _ in $(seq 1 40); do
  if curl -fsS -o /dev/null --max-time 5 "${BASE_URL}/"; then
    ingress_up=1
    echo "ingress reachable"
    break
  fi
  sleep 3
done
if [ -z "$ingress_up" ]; then
  echo "ERROR: ingress at ${BASE_URL} did not become reachable" >&2
  kubectl get pods -n "$NAMESPACE"
  kubectl get ingress -n "$NAMESPACE"
  exit 1
fi

echo "=== Running Playwright Home smoke against ${BASE_URL} ==="
cd "$REPO_ROOT"
E2E_BASE_URL="$BASE_URL" npm run e2e --workspace=apps/web

echo "=== Deploy + smoke complete ==="
