#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NAMESPACE=wellbe

echo "=== Building Docker images ==="
docker build -t wellbe-postgres:local -f "$REPO_ROOT/infra/local/Dockerfile.postgres" "$REPO_ROOT/infra/local"
docker build -t wellbe-vault-writer:local -f "$REPO_ROOT/backend/apps/vault-writer/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-ingestion-worker:local -f "$REPO_ROOT/backend/apps/ingestion-worker/Dockerfile" "$REPO_ROOT"
docker build -t wellbe-migrations:local -f "$REPO_ROOT/db/Dockerfile.migrations" "$REPO_ROOT"

echo "=== Applying K8s manifests ==="
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
kubectl apply -f "$SCRIPT_DIR/configmaps.yaml" -n $NAMESPACE
kubectl apply -f "$SCRIPT_DIR/postgres.yaml" -n $NAMESPACE
kubectl apply -f "$SCRIPT_DIR/redis.yaml" -n $NAMESPACE
kubectl apply -f "$SCRIPT_DIR/minio.yaml" -n $NAMESPACE

echo "=== Waiting for infrastructure ==="
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=60s
kubectl wait --for=condition=ready pod -l app=minio -n $NAMESPACE --timeout=60s

echo "=== Running MinIO bucket init ==="
kubectl delete job minio-init -n $NAMESPACE --ignore-not-found
kubectl apply -f "$SCRIPT_DIR/minio.yaml" -n $NAMESPACE

echo "=== Deploying ZITADEL ==="
kubectl apply -f "$SCRIPT_DIR/zitadel.yaml" -n $NAMESPACE

echo "=== Running migrations ==="
kubectl delete job alembic-migrate -n $NAMESPACE --ignore-not-found
kubectl apply -f "$SCRIPT_DIR/migration-job.yaml" -n $NAMESPACE
kubectl wait --for=condition=complete job/alembic-migrate -n $NAMESPACE --timeout=120s

echo "=== Deploying application services ==="
kubectl apply -f "$SCRIPT_DIR/vault-writer.yaml" -n $NAMESPACE
kubectl apply -f "$SCRIPT_DIR/ingestion-worker.yaml" -n $NAMESPACE

echo "=== Waiting for services ==="
kubectl wait --for=condition=ready pod -l app=vault-writer -n $NAMESPACE --timeout=90s
kubectl wait --for=condition=ready pod -l app=ingestion-worker -n $NAMESPACE --timeout=90s

echo "=== Deployment complete ==="
kubectl get pods -n $NAMESPACE
