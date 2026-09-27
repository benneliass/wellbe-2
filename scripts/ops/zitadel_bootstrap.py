#!/usr/bin/env python3
"""Idempotently configure ZITADEL for WellBe login.

Ensures (search before create, converge on re-run):
  * project ``wellbe``
  * OIDC app ``wellbe-web``: user-agent (SPA), PKCE / auth method NONE, auth code +
    refresh token grants, JWT access tokens, redirect + post-logout URIs for each
    web origin, built-in (v1) login UI
  * human user ``ben`` (owner; initial password must be changed on first login)
  * human user ``demo`` (shared demo login, linked to the demo patient afterwards
    with scripts/ops/link_identity.py)

Prints the ids the Helm values and link_identity.py need (no secrets).

Environment:
  ZITADEL_URL              base URL to call, e.g. https://wellbe-auth.tail9c487a.ts.net
                           or a port-forward such as http://localhost:8090
  ZITADEL_HOST_HEADER      optional Host override (port-forward: the external domain)
  ZITADEL_ISSUER           token audience for key-file auth (default ZITADEL_URL)
  ZITADEL_ORG_ID           optional org to create everything in (default: caller's org)
  ZITADEL_PAT | ZITADEL_PAT_FILE | ZITADEL_KEY_FILE
                           admin credential: a personal access token, or a machine
                           user key JSON (JWT-profile grant)
  OWNER_EMAIL              email for user ``ben`` (required)
  OWNER_INITIAL_PASSWORD   initial password for ``ben`` (required when creating)
  DEMO_PASSWORD            password for ``demo`` (required when creating)
  DEMO_EMAIL               default demo@wellbe.invalid
  WEB_ORIGINS              comma-separated, default
                           https://wellbe.tail9c487a.ts.net,http://localhost:3000

Run from the backend workspace (httpx + PyJWT):
  cd backend && uv run python ../scripts/ops/zitadel_bootstrap.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

PROJECT_NAME = "wellbe"
APP_NAME = "wellbe-web"
DEFAULT_ORIGINS = "https://wellbe.tail9c487a.ts.net,http://localhost:3000"
EQUALS = "TEXT_QUERY_METHOD_EQUALS"


class ZitadelError(RuntimeError):
    pass


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        sys.exit(f"{name} is required")
    return value or ""


def _machine_key_token(client: httpx.Client, key_file: str, audience: str) -> str:
    import jwt  # PyJWT, from the backend workspace

    key = json.loads(Path(key_file).read_text())
    now = int(time.time())
    assertion = jwt.encode(
        {"iss": key["userId"], "sub": key["userId"], "aud": audience, "iat": now, "exp": now + 300},
        key["key"],
        algorithm="RS256",
        headers={"kid": key["keyId"]},
    )
    resp = client.post(
        "/oauth/v2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "scope": "openid urn:zitadel:iam:org:project:id:zitadel:aud",
            "assertion": assertion,
        },
    )
    if resp.status_code != 200:
        raise ZitadelError(f"token exchange failed: {resp.status_code} {resp.text}")
    token: str = resp.json()["access_token"]
    return token


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    base = _env("ZITADEL_URL", required=True).rstrip("/")
    headers = {"Accept": "application/json"}
    if host := _env("ZITADEL_HOST_HEADER"):
        headers["Host"] = host
    client = httpx.Client(base_url=base, headers=headers, timeout=20.0, transport=transport)

    if pat := _env("ZITADEL_PAT"):
        token = pat.strip()
    elif pat_file := _env("ZITADEL_PAT_FILE"):
        token = Path(pat_file).read_text().strip()
    elif key_file := _env("ZITADEL_KEY_FILE"):
        token = _machine_key_token(client, key_file, _env("ZITADEL_ISSUER", base))
    else:
        sys.exit("one of ZITADEL_PAT, ZITADEL_PAT_FILE or ZITADEL_KEY_FILE is required")
    client.headers["Authorization"] = f"Bearer {token}"
    if org := _env("ZITADEL_ORG_ID"):
        client.headers["x-zitadel-orgid"] = org
    return client


def _call(client: httpx.Client, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    resp = client.request(method, path, json=body)
    if resp.status_code >= 400:
        raise ZitadelError(f"{method} {path} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else {}


def _no_changes(err: ZitadelError) -> bool:
    text = str(err)
    return "NoChanges" in text or "No changes" in text or "COMMAND-1m88i" in text


@dataclass
class Result:
    project_id: str
    app_id: str
    client_id: str
    users: dict[str, str]


def ensure_project(client: httpx.Client, log: list[str]) -> str:
    found = _call(
        client,
        "POST",
        "/management/v1/projects/_search",
        {"queries": [{"nameQuery": {"name": PROJECT_NAME, "method": EQUALS}}]},
    ).get("result", [])
    if found:
        log.append(f"project {PROJECT_NAME}: exists")
        project_id: str = found[0]["id"]
        return project_id
    created = _call(client, "POST", "/management/v1/projects", {"name": PROJECT_NAME})
    log.append(f"project {PROJECT_NAME}: created")
    project_id = created["id"]
    return project_id


def oidc_config(origins: list[str]) -> dict[str, Any]:
    has_http = any(o.startswith("http://") for o in origins)
    return {
        "redirectUris": [f"{o}/auth/callback" for o in origins],
        "postLogoutRedirectUris": [f"{o}/" for o in origins],
        "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
        "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"],
        "appType": "OIDC_APP_TYPE_USER_AGENT",
        "authMethodType": "OIDC_AUTH_METHOD_TYPE_NONE",
        "accessTokenType": "OIDC_TOKEN_TYPE_JWT",
        # Plain-http redirect URIs (http://localhost:3000) are only accepted in dev mode.
        "devMode": has_http,
        "accessTokenRoleAssertion": False,
        "idTokenRoleAssertion": False,
        "idTokenUserinfoAssertion": True,
        "clockSkew": "0s",
        "additionalOrigins": [],
        # The chart does not run the separate Login V2 container.
        "loginVersion": {"loginV1": {}},
    }


def ensure_app(
    client: httpx.Client, project_id: str, origins: list[str], log: list[str]
) -> tuple[str, str]:
    config = oidc_config(origins)
    found = _call(
        client,
        "POST",
        f"/management/v1/projects/{project_id}/apps/_search",
        {"queries": [{"nameQuery": {"name": APP_NAME, "method": EQUALS}}]},
    ).get("result", [])
    if not found:
        created = _call(
            client,
            "POST",
            f"/management/v1/projects/{project_id}/apps/oidc",
            {"name": APP_NAME, "version": "OIDC_VERSION_1_0", **config},
        )
        log.append(f"app {APP_NAME}: created")
        return created["appId"], created["clientId"]
    app = found[0]
    app_id: str = app["id"]
    client_id: str = app.get("oidcConfig", {}).get("clientId", "")
    if not client_id:
        raise ZitadelError(f"app {APP_NAME} exists but is not an OIDC app")
    try:
        _call(
            client,
            "PUT",
            f"/management/v1/projects/{project_id}/apps/{app_id}/oidc_config",
            {"version": "OIDC_VERSION_1_0", **config},
        )
        log.append(f"app {APP_NAME}: exists, config converged")
    except ZitadelError as err:
        if not _no_changes(err):
            raise
        log.append(f"app {APP_NAME}: exists, config unchanged")
    return app_id, client_id


def ensure_human(
    client: httpx.Client,
    *,
    username: str,
    given: str,
    family: str,
    email: str,
    password_env: str,
    change_required: bool,
    log: list[str],
) -> str:
    query: list[dict[str, Any]] = [{"userNameQuery": {"userName": username, "method": EQUALS}}]
    if org := _env("ZITADEL_ORG_ID"):
        query.append({"organizationIdQuery": {"organizationId": org}})
    found = _call(client, "POST", "/v2/users", {"queries": query})
    result = found.get("result", [])
    if result:
        log.append(f"user {username}: exists (password untouched)")
        user_id: str = result[0]["userId"]
        return user_id
    password = _env(password_env, required=True)
    created = _call(
        client,
        "POST",
        "/v2/users/human",
        {
            "username": username,
            "profile": {"givenName": given, "familyName": family, "displayName": given},
            "email": {"email": email, "isVerified": True},
            "password": {"password": password, "changeRequired": change_required},
        },
    )
    log.append(f"user {username}: created")
    user_id = created["userId"]
    return user_id


def disable_instance_login_v2(client: httpx.Client, log: list[str]) -> None:
    _call(client, "PUT", "/v2/features/instance", {"loginV2": {"required": False}})
    log.append("instance feature loginV2.required: false")


def bootstrap(client: httpx.Client, *, instance_login_v1: bool) -> tuple[Result, list[str]]:
    log: list[str] = []
    origins = [o.strip().rstrip("/") for o in _env("WEB_ORIGINS", DEFAULT_ORIGINS).split(",")]
    origins = [o for o in origins if o]
    owner_email = _env("OWNER_EMAIL", required=True)
    if instance_login_v1:
        disable_instance_login_v2(client, log)
    project_id = ensure_project(client, log)
    app_id, client_id = ensure_app(client, project_id, origins, log)
    users = {
        "ben": ensure_human(
            client,
            username="ben",
            given="Ben",
            family="Owner",
            email=owner_email,
            password_env="OWNER_INITIAL_PASSWORD",
            change_required=True,
            log=log,
        ),
        "demo": ensure_human(
            client,
            username="demo",
            given="Demo",
            family="User",
            email=_env("DEMO_EMAIL", "demo@wellbe.invalid"),
            password_env="DEMO_PASSWORD",
            change_required=False,
            log=log,
        ),
    }
    return Result(project_id, app_id, client_id, users), log


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently configure ZITADEL for WellBe.")
    parser.add_argument(
        "--instance-login-v1",
        action="store_true",
        help="also set the instance feature loginV2.required=false (instances created "
        "on ZITADEL v4 default to the Login V2 UI, which the chart does not deploy)",
    )
    args = parser.parse_args()
    with build_client() as client:
        try:
            result, log = bootstrap(client, instance_login_v1=args.instance_login_v1)
        except ZitadelError as err:
            sys.exit(f"zitadel bootstrap failed: {err}")
    for line in log:
        print(f"# {line}", file=sys.stderr)
    print(f"ZITADEL_PROJECT_ID={result.project_id}")
    print(f"WELLBE_WEB_APP_ID={result.app_id}")
    print(f"WELLBE_WEB_CLIENT_ID={result.client_id}")
    print(f"ZITADEL_USER_ID_BEN={result.users['ben']}")
    print(f"ZITADEL_USER_ID_DEMO={result.users['demo']}")


if __name__ == "__main__":
    main()
