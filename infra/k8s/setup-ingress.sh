#!/usr/bin/env bash
# Install ingress-nginx into the local kind cluster via Helm (kind-tuned).
#
# Requires the cluster to have been created with infra/local/kind-cluster.yaml
# (node label ingress-ready=true + host port mappings for 80/443).
#
# Idempotent: re-running upgrades the release in place.
set -euo pipefail

NAMESPACE=ingress-nginx
RELEASE=ingress-nginx
CHART_VERSION=4.11.3   # ingress-nginx chart (controller v1.11.x)

echo "=== Adding ingress-nginx Helm repo ==="
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null 2>&1 || true
helm repo update ingress-nginx >/dev/null

echo "=== Installing ingress-nginx ($RELEASE) ==="
helm upgrade --install "$RELEASE" ingress-nginx/ingress-nginx \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --version "$CHART_VERSION" \
  --set controller.hostPort.enabled=true \
  --set controller.service.type=NodePort \
  --set controller.publishService.enabled=false \
  --set controller.watchIngressWithoutClass=true \
  --set-string "controller.nodeSelector.ingress-ready=true" \
  --set "controller.tolerations[0].key=node-role.kubernetes.io/control-plane" \
  --set "controller.tolerations[0].operator=Exists" \
  --set "controller.tolerations[0].effect=NoSchedule" \
  --wait --timeout 4m

echo "=== Waiting for the admission webhook endpoint ==="
kubectl wait --namespace "$NAMESPACE" \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

echo "=== ingress-nginx ready ==="
kubectl get pods,svc -n "$NAMESPACE"
