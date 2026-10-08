# Homeserver access

WellBe is `https://wellbe.tail9c487a.ts.net/`.

The chart on the k3s cluster is GitOps. Argo CD (app `wellbe` in
`benneliass/home-server`, `argocd/apps/wellbe.yaml`) tracks `main` at
`infra/helm/wellbe-local` with `values-homeserver.yaml`. Image builds run on
push to `main` only.

## Kubernetes API

`kubectl` uses `~/.kube/clusters/home-server`. The control plane is node
`home-server-worker` (`192.168.1.201`). `192.168.1.200` (`home-server`) is a
worker only.

```sh
export KUBECONFIG=$HOME/.kube/clusters/home-server
kubectl get nodes
```

Argo CD is `https://argocd.tail9c487a.ts.net` (username and password, no SSO).
The app UI shows whether a sync happened and whether the `dev-workspace-seed`
hook Job failed.

## Which image is running

`values-homeserver.yaml` image tags are fallbacks. The tags Argo CD applies
are the Helm parameters in `infra/helm/wellbe-local/.argocd-source-wellbe.yaml`.
argocd-image-updater rewrites that file so an auth edit in the values file
does not collide with an image bump. Read the parameter file, not the values
literals, to see the deployed version.

`devSeed.image` is one of those parameters. Enabling the seed in the values
file still runs whatever tag the parameter file sets, unless the values change
is made after checking that file.

## Config changes roll pods

Deployments that read a ConfigMap carry a `checksum/config` annotation on the
pod template (`wellbe-local.configChecksum`). Changing the ConfigMap changes
the pod template, so Argo CD rolls the workload. Web has no ConfigMap; its
auth env is on the pod template, so an `auth.mode` change rolls it too.

## Demo seed

`auth.mode: oidc` and `devSeed.enabled: true` fail the chart render. The seed
calls the API with `X-Wellbe-*` headers, which OIDC ignores.

Safe order, after the API image includes the dev-header preflight:

1. `auth.mode: dev-headers`, `devSeed.enabled: false`. Sync. Wait until
   `GET /v1/threads` with the dev headers returns 200. Try the demo is off
   while dev-headers is on.
2. `devSeed.enabled: true`. Sync. The hook Job `dev-workspace-seed` must reach
   Complete. It truncates patient tables only after the dev-header check
   returns 200 and the stored seed revision differs. A failed Job has not
   reseeded. If the check never succeeds, the tables are unchanged.
3. Confirm the revision and the notes. The seed does not replace an existing
   controller account on the demo patient, so the ZITADEL `demo` user stays
   bound and the new captures are on that patient.
4. `auth.mode: oidc`, `devSeed.enabled: false`. Sync.

Details of the OIDC flip and the demo re-bind are in `auth-oidc.md`.
