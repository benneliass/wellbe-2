# Runbook: switch WellBe to OIDC login (ZITADEL)

Moves the homeserver from the spoofable dev identity headers to real login through
the in-chart ZITADEL. Order: **expose ZITADEL → get an admin token → bootstrap →
link demo → fill values → flip mode**. Local kind and CI stay on `dev-headers`.

## How the two modes work

| | `dev-headers` (default: local, CI) | `oidc` (homeserver after the flip) |
|---|---|---|
| API (`WELLBE_AUTH_MODE`) | Trusts `X-Wellbe-Actor-Id` / `-Patient-Id` / `-Actor-Type`, and `X-Wellbe-Issuer` / `-Subject` for onboarding | Requires `Authorization: Bearer <ZITADEL JWT access token>`. Verifies signature (JWKS, cached; refetched on unknown `kid`), `iss`, `aud`, `exp`/`nbf` (30 s leeway). **All X-Wellbe identity headers are ignored.** The actor is the finalized `identity.accounts` row for the token's `(iss, sub)`. |
| Unknown / not-finalized identity | n/a | Onboarding routes work; every other route returns `403 {"code":"onboarding_required"}` |
| Delegated access | `X-Wellbe-Patient-Id` ≠ actor → C1 grant check | Same: `X-Wellbe-Patient-Id` may name another patient, which gives a non-controller principal that `require_access` admits only on a live C1 grant |
| Web (`/auth-config.js`, runtime env) | "New to WellBe" / "Dev workspace" dev identities (localStorage) | Authorization Code + PKCE (public client `wellbe-web`), tokens in sessionStorage, refresh-token renewal, sign-out ends the ZITADEL session. No account yet → `/onboarding` |

Web auth settings are **runtime** env vars on the web Deployment
(`NEXT_PUBLIC_WELLBE_AUTH_MODE`, `NEXT_PUBLIC_WELLBE_OIDC_ISSUER`,
`NEXT_PUBLIC_WELLBE_OIDC_CLIENT_ID`), served to the browser by `/auth-config.js`, so
the same image serves both modes. Only `NEXT_PUBLIC_WELLBE_API_URL` and the dev ids
remain build args.

Helm keeps everything under the top-level `auth:` key (see `values.yaml`). Rendering
fails fast if `auth.mode=oidc` is missing `issuer` / `audience` / `webClientId`, or
if `devSeed.enabled` is still true (the seed drives the API with dev headers).

## Prerequisites

- Images built from a commit that contains this change are deployed (api + web).
- Tailnet HTTPS certificates enabled (already true for `wellbe` / `wellbe-api`).
- `values-homeserver.yaml` already sets (and ArgoCD has synced):
  `auth.zitadel.externalDomain: wellbe-auth.tail9c487a.ts.net`, `externalPort: "443"`,
  `externalSecure: true` (→ `--tlsMode external`), `tailscaleIngress.enabled: true`,
  and the first-instance settings (org `WellBe`, Login V2 off, bootstrap machine user).

## 1. Check ZITADEL is reachable on its new domain

```sh
kubectl -n wellbe get ingress wellbe-auth-ts
curl -s https://wellbe-auth.tail9c487a.ts.net/.well-known/openid-configuration | jq -r .issuer
# expect: https://wellbe-auth.tail9c487a.ts.net
kubectl -n wellbe get secret zitadel-bootstrap-pat   # exists => skip to step 3
```

## 2. Get an admin credential

The first-instance settings (bootstrap machine user + PAT Secret, org name,
Login V2 off, correct external domain) only apply when ZITADEL initializes an
**empty** database. The current homeserver instance was initialized with
`externalDomain=localhost` and likely defaults to Login V2 (a separate UI this chart
does not run), so the recommended path is A.

### A. Recommended: re-initialize ZITADEL's own database

Safe today: nothing in WellBe references ZITADEL data yet (the API is still on
dev-headers), and ZITADEL uses its own `zitadel` database — WellBe data is untouched.

The chart's default masterkey is public, so a re-initialized instance must get its
own. Create the secret first and set `zitadel.masterkeySecret: {name: zitadel-masterkey}`
in `values-homeserver.yaml` in the same change that triggers the reset (a masterkey
change on an existing ZITADEL database makes its encrypted data unreadable):

```sh
kubectl -n wellbe create secret generic zitadel-masterkey \
  --from-literal=masterkey="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)"
```

The zitadel Deployment uses `strategy: Recreate`, so once the values change syncs
the old pod (old masterkey) is gone and only the new pod can re-initialize the
database. It fails against the old database until you drop it:

```sh
kubectl -n wellbe exec statefulset/postgres -- \
  psql -U wellbe -d postgres -c 'DROP DATABASE zitadel WITH (FORCE);'
kubectl -n wellbe rollout restart deploy/zitadel
kubectl -n wellbe rollout status deploy/zitadel --timeout=10m
kubectl -n wellbe logs deploy/zitadel -c bootstrap-pat-writer
# expect: secret zitadel-bootstrap-pat created
```

`start-from-init` recreates the database, the instance (org `WellBe`, built-in
login), the default human admin `zitadel-admin@wellbe.wellbe-auth.tail9c487a.ts.net`
(password `Password1!`, must change on first login — do it now in
`https://wellbe-auth.tail9c487a.ts.net/ui/console`), and the machine user
`wellbe-bootstrap` (IAM owner) whose PAT lands in Secret `zitadel-bootstrap-pat`.

### B. Alternative: keep the existing instance

1. Open `https://wellbe-auth.tail9c487a.ts.net/ui/console` and sign in as
   `zitadel-admin@zitadel.localhost` (default password `Password1!` unless changed).
   If you are redirected to `/ui/v2/login` and get an error, the instance requires
   Login V2 — use path A.
2. Users → Service Users → New (`wellbe-bootstrap`, access token type Bearer);
   Personal Access Tokens → New → copy the token.
3. Default settings / Instance → Members → add `wellbe-bootstrap` as **IAM Owner**.
4. Store it: `kubectl -n wellbe create secret generic zitadel-bootstrap-pat --from-literal=pat='<PAT>'`
5. Run step 3 with `--instance-login-v1` (sets the instance feature
   `loginV2.required=false`).

A machine-user key JSON works instead of a PAT: `ZITADEL_KEY_FILE=/path/key.json`.

## 3. Bootstrap project, app and users

From a machine on the tailnet (repo root):

```sh
export ZITADEL_URL=https://wellbe-auth.tail9c487a.ts.net
export ZITADEL_PAT="$(kubectl -n wellbe get secret zitadel-bootstrap-pat -o jsonpath='{.data.pat}' | base64 -d)"
export OWNER_EMAIL='<owner email>'
export OWNER_INITIAL_PASSWORD='<temp password>'   # changed on first login
export DEMO_PASSWORD='<demo password>'
# Password policy default: >= 8 chars with upper, lower, digit and symbol.
cd backend && uv run python ../scripts/ops/zitadel_bootstrap.py
```

Not on the tailnet? `kubectl -n wellbe port-forward svc/zitadel 8090:8090` and use
`ZITADEL_URL=http://localhost:8090 ZITADEL_HOST_HEADER=wellbe-auth.tail9c487a.ts.net`.

It is idempotent (re-run converges the app config, never resets passwords) and
prints:

```
ZITADEL_PROJECT_ID=...
WELLBE_WEB_APP_ID=...
WELLBE_WEB_CLIENT_ID=...
ZITADEL_USER_ID_BEN=...
ZITADEL_USER_ID_DEMO=...
```

The `wellbe-web` app: user-agent, auth method NONE (PKCE), grants auth code +
refresh token, JWT access tokens, redirect URIs
`https://wellbe.tail9c487a.ts.net/auth/callback` and
`http://localhost:3000/auth/callback`, post-logout URIs `<origin>/`. The plain-http
localhost URI requires ZITADEL "dev mode" on the app; drop it with
`WEB_ORIGINS=https://wellbe.tail9c487a.ts.net` to turn dev mode off.

Recommended once in the console: Default settings → Login behavior → untick
"User registration allowed" (only `ben` and `demo` should exist).

Brand the login pages as WellBe (colours, logo, Figtree font, no ZITADEL
watermark, WellBe wording). Idempotent; re-run after any ZITADEL re-init:

```sh
cd backend && uv run python ../scripts/ops/zitadel_branding.py   # same ZITADEL_URL / ZITADEL_PAT
```

## 4. Link the demo login to the demo patient

The demo patient `de7a0000-0000-4000-8000-000000000001` is bound to the dev
identity `dev-local/dev-controller`, and a patient has exactly one account, so
re-bind it (`--replace`; account, onboarding state and workspace are kept):

```sh
kubectl -n wellbe exec -i deploy/api -- python - \
  --issuer https://wellbe-auth.tail9c487a.ts.net \
  --subject "$ZITADEL_USER_ID_DEMO" \
  --patient-id de7a0000-0000-4000-8000-000000000001 \
  --display-name Demo --replace < scripts/ops/link_identity.py
# expect: re-bound from (dev-local, dev-controller): (...) -> patient de7a0000-...
```

Re-running prints `unchanged`. `ben` is **not** linked — his first login goes
through onboarding and creates a new patient.

## 5. Fill values and flip the mode

In `infra/helm/wellbe-local/values-homeserver.yaml`, replace `auth.mode: dev-headers`
with the commented block, filling the ids from step 3, and disable the seed:

```yaml
devSeed:
  enabled: false          # was true

auth:
  mode: oidc
  oidc:
    issuer: "https://wellbe-auth.tail9c487a.ts.net"
    audience: ["<ZITADEL_PROJECT_ID>", "<WELLBE_WEB_CLIENT_ID>"]
    webClientId: "<WELLBE_WEB_CLIENT_ID>"
    jwksUrl: "http://zitadel:8090/oauth/v2/keys"
    jwksHostHeader: "wellbe-auth.tail9c487a.ts.net"
  zitadel: ...            # unchanged
```

Check the render, commit, push; ArgoCD rolls api (config map) and web (env):

```sh
helm template wellbe infra/helm/wellbe-local -f infra/helm/wellbe-local/values-homeserver.yaml >/dev/null
kubectl -n wellbe rollout restart deploy/api deploy/web   # config map changes do not restart pods
```

## 6. Verify

```sh
curl -s https://wellbe.tail9c487a.ts.net/auth-config.js
# window.__WELLBE_AUTH_CONFIG__ = {"mode":"oidc",...}
curl -s -o /dev/null -w '%{http_code}\n' https://wellbe-api.tail9c487a.ts.net/v1/threads \
  -H 'X-Wellbe-Actor-Id: de7a0000-0000-4000-8000-000000000001'
# 401 — identity headers are no longer trusted
kubectl -n wellbe exec deploy/api -- python -c "import httpx; print(httpx.get('http://zitadel:8090/oauth/v2/keys', headers={'Host': 'wellbe-auth.tail9c487a.ts.net'}).status_code)"
# 200 — the API can fetch the JWKS in-cluster
```

In a browser: `https://wellbe.tail9c487a.ts.net` → Sign in → `demo` lands in the
seeded workspace; `ben` changes his password, then goes through onboarding into a
new workspace. Sign out returns to the front door.

## 7. WellBe's own sign-in screens (optional)

ZITADEL's hosted pages can only be recoloured. With `auth.oidc.customLogin` the web
app renders the sign-in itself at `/login`: ZITADEL redirects authorize requests
to `<baseUri>/login?authRequest=V2_…`, and `/login/submit` checks the password
and finishes the auth request server side, with a service token that never
reaches the browser.

```sh
# Machine user wellbe-login (instance role IAM_LOGIN_CLIENT), 10-attempt lockout,
# and a fresh token stored as the web Deployment's secret.
cd backend && F=$(mktemp) && uv run python ../scripts/ops/zitadel_login_client.py --pat-out "$F" \
  && kubectl -n wellbe create secret generic wellbe-login-client --from-file=pat="$F" \
       --dry-run=client -o yaml | kubectl apply -f - ; rm -f "$F"
```

Deploy with `auth.oidc.customLogin.enabled: true` (values-homeserver.yaml) and
wait for the web rollout, then point the app at it:

```sh
ZITADEL_LOGIN_V2_BASE_URI=https://wellbe.tail9c487a.ts.net \
  uv run python ../scripts/ops/zitadel_bootstrap.py   # same env as step 3
```

Always pass `ZITADEL_LOGIN_V2_BASE_URI` on later bootstrap runs; without it the
app goes back to ZITADEL's pages. Check: Sign in on the front door shows the
WellBe card at `/login`, a wrong password says the login and password don't match,
and a correct one lands in the workspace.

### Try the demo (optional)

`auth.oidc.customLogin.demo.enabled: true` (on in values-homeserver.yaml) adds
"Try the demo" to the front door. It runs the normal authorize redirect; the
`/login` page then posts only the auth request id to `/login/demo`, which creates
a ZITADEL session for the fixed login `demo.loginName` (default `demo`, the user
linked to the demo patient in step 4) with a user check only, no password, and
finishes the auth request. ZITADEL allows this for the `IAM_LOGIN_CLIENT` token,
so no demo password is stored anywhere in the cluster. The login name comes from
server config only; the browser cannot pick another user.

Anyone who can reach the web origin can open the demo workspace, and everyone
shares it: keep only sample data in that patient, and treat anything written
there as public to the tailnet. The demo tokens carry no `amr` claim. Turning the
flag off removes the button (`/auth-config.js` publishes `demo: false`) and makes
`/login/demo` answer 404. Check: front door → Try the demo → "Opening the demo…"
→ the workspace as Demo, without typing anything.

QA against an OIDC deployment signs in through the same screen:

```sh
# Two throwaway ZITADEL users (created and deleted by the run), full API journey.
ZITADEL_PAT=... uv run python ../scripts/qa/journey.py
# Live browser suite as demo (global setup signs in once via /login).
cd apps/web && E2E_LOGIN_PASSWORD=... npm run e2e:live
```

To undo, re-run the bootstrap without `ZITADEL_LOGIN_V2_BASE_URI` (the web
settings can stay; `/login` is simply never reached). A login locked by the
lockout policy is unlocked in the ZITADEL console, or with
`POST /v2/users/{id}/unlock`.

## Rollback

Set `auth.mode: dev-headers` and `devSeed.enabled: true`, and re-bind the demo
patient to the dev identity (otherwise the dev seed's account step conflicts):

```sh
kubectl -n wellbe exec -i deploy/api -- python - --issuer dev-local --subject dev-controller \
  --patient-id de7a0000-0000-4000-8000-000000000001 --replace < scripts/ops/link_identity.py
```
