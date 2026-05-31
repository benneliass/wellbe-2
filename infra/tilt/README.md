# Tilt Dev Workflow

Live code sync for wellbe-2 — Python source changes are reflected in running Kind pods in ~1 second, with no image rebuild required.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| [`tilt`](https://docs.tilt.dev/install.html) | Dev loop orchestrator | `brew install tilt-dev/tap/tilt` |
| [`kind`](https://kind.sigs.k8s.io/) | Local Kubernetes cluster | `brew install kind` |
| [`helm`](https://helm.sh/) | Chart rendering | `brew install helm` |
| [`docker`](https://docs.docker.com/get-docker/) | Image builds | Docker Desktop |

The Kind cluster must be named `desktop` (kubectl context `kind-desktop`). Create it with:

```bash
kind create cluster --name desktop
```

## Usage

### Start the dev loop

```bash
# From the repo root
tilt up
```

Tilt will:
1. Build the three service images with `DEV=true` (enables `uvicorn --reload`)
2. Load them into the Kind cluster (no registry push needed)
3. Render the Helm chart and apply it to the `wellbe` namespace
4. Open port-forwards: vault-writer → 8002, ingestion-worker → 8003, processing-worker → 8004
5. Start watching for file changes

### Stop and tear down

```bash
tilt down
```

This removes the Kubernetes resources. The Kind cluster itself is not deleted.

## How live sync works

### `.py` source file changed

When you save a `.py` file under `backend/apps/<service>/src/` or `backend/packages/`:

1. Tilt detects the change (~100 ms)
2. The file is synced directly into the running pod via `kubectl cp` (~200–500 ms)
3. `uvicorn --reload` detects the new file on disk and reloads the application (~200–500 ms)

Total round-trip: **~1 second**. No image rebuild. No pod restart.

### Dependency or Dockerfile changed

When you save `pyproject.toml` or any `Dockerfile`:

1. Tilt triggers a full `docker build` for the affected service
2. The new image is loaded into Kind
3. The pod is replaced with the new image

This is intentional — dependency changes require a proper rebuild to update the venv.

## Port forwards

| Service | Local port | Container port |
|---------|-----------|---------------|
| vault-writer | 8002 | 8002 |
| ingestion-worker | 8003 | 8003 |
| processing-worker | 8004 | 8004 |

## Notes

- Images use `imagePullPolicy: Never` in the Helm chart — Tilt loads images directly into Kind's image store, so no registry is needed.
- `postgres`, `redis`, `minio`, and `zitadel` are not managed by live_update. They start from their Helm chart values and are not reloaded on source changes.
- If you re-run the Helm release manually while Tilt has managed the same chart, pass `--server-side=false`. Helm v4's server-side apply can otherwise conflict with fields owned by Tilt's Kubernetes client.
- `infra/k8s/deploy.sh` also uses `--server-side=false` so rerunning Helm from the script keeps working after Tilt has touched the release.
- `DEV=true` is only passed by the Tiltfile. Production builds use the default `DEV=false`, which runs uvicorn without `--reload`.
