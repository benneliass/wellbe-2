#!/usr/bin/env python3
"""Idempotently set up the service identity behind WellBe's own sign-in screens.

The web app renders the sign-in UI itself (``/signin``) and asks ZITADEL, server
side, to check the password and finish the OIDC auth request. That needs a
machine user with the instance role ``IAM_LOGIN_CLIENT``. This script ensures:

  * machine user ``wellbe-login`` (bearer tokens)
  * instance membership ``IAM_LOGIN_CLIENT`` for it
  * a password lockout policy, since the sign-in form is now ours to rate-limit
  * optionally a new personal access token, written to ``--pat-out`` (mode 600)
    and never printed; store it as the cluster secret the web Deployment reads

Environment:
  ZITADEL_URL   base URL, e.g. https://wellbe-auth.tail9c487a.ts.net
  ZITADEL_PAT   instance admin personal access token (the bootstrap PAT)

Run from the backend workspace:
  cd backend && uv run python ../scripts/ops/zitadel_login_client.py --pat-out /tmp/login.pat
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import httpx

USERNAME = "wellbe-login"
ROLE = "IAM_LOGIN_CLIENT"
MAX_PASSWORD_ATTEMPTS = 10
PAT_EXPIRY = "2030-01-01T00:00:00Z"
EQUALS = "TEXT_QUERY_METHOD_EQUALS"


class ZitadelError(RuntimeError):
    pass


def _call(client: httpx.Client, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    resp = client.request(method, path, json=body)
    if resp.status_code >= 400:
        raise ZitadelError(f"{method} {path} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else {}


def _benign(err: ZitadelError) -> bool:
    text = str(err).lower().replace(" ", "")
    return any(s in text for s in ("alreadyexists", "nochanges", "notchanged", "notbeenchanged"))


def ensure_machine_user(client: httpx.Client, log: list[str]) -> str:
    found = _call(
        client,
        "POST",
        "/v2/users",
        {"queries": [{"userNameQuery": {"userName": USERNAME, "method": EQUALS}}]},
    ).get("result", [])
    if found:
        log.append(f"user {USERNAME}: exists")
        user_id: str = found[0]["userId"]
        return user_id
    created = _call(
        client,
        "POST",
        "/management/v1/users/machine",
        {
            "userName": USERNAME,
            "name": "WellBe sign-in",
            "description": "Server side of the WellBe sign-in screens",
            "accessTokenType": "ACCESS_TOKEN_TYPE_BEARER",
        },
    )
    log.append(f"user {USERNAME}: created")
    user_id = created["userId"]
    return user_id


def ensure_role(client: httpx.Client, user_id: str, log: list[str]) -> None:
    try:
        _call(client, "POST", "/admin/v1/members", {"userId": user_id, "roles": [ROLE]})
        log.append(f"instance member {ROLE}: added")
    except ZitadelError as err:
        if not _benign(err):
            raise
        try:
            _call(client, "PUT", f"/admin/v1/members/{user_id}", {"roles": [ROLE]})
            log.append(f"instance member {ROLE}: converged")
        except ZitadelError as err2:
            if not _benign(err2):
                raise
            log.append(f"instance member {ROLE}: unchanged")


def ensure_lockout(client: httpx.Client, log: list[str]) -> None:
    try:
        _call(
            client,
            "PUT",
            # Read at /policies/lockout, but the update keeps the legacy path.
            "/admin/v1/policies/password/lockout",
            {"maxPasswordAttempts": MAX_PASSWORD_ATTEMPTS},
        )
        log.append(f"lockout policy: {MAX_PASSWORD_ATTEMPTS} password attempts")
    except ZitadelError as err:
        if not _benign(err):
            raise
        log.append("lockout policy: unchanged")


def mint_pat(client: httpx.Client, user_id: str, out: Path, log: list[str]) -> None:
    created = _call(
        client, "POST", f"/management/v1/users/{user_id}/pats", {"expirationDate": PAT_EXPIRY}
    )
    out.touch(mode=0o600, exist_ok=True)
    out.chmod(0o600)
    out.write_text(created["token"])
    log.append(f"pat {created['tokenId']}: written to {out} (expires {PAT_EXPIRY})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pat-out", type=Path, help="mint a new PAT and write it here")
    args = parser.parse_args()
    url = os.environ.get("ZITADEL_URL", "").rstrip("/")
    pat = os.environ.get("ZITADEL_PAT", "")
    if not url or not pat:
        print("ZITADEL_URL and ZITADEL_PAT are required", file=sys.stderr)
        return 2
    log: list[str] = []
    with httpx.Client(
        base_url=url, headers={"Authorization": f"Bearer {pat.strip()}"}, timeout=20.0
    ) as client:
        try:
            user_id = ensure_machine_user(client, log)
            ensure_role(client, user_id, log)
            ensure_lockout(client, log)
            if args.pat_out:
                mint_pat(client, user_id, args.pat_out, log)
        except ZitadelError as err:
            print(f"login client setup failed: {err}", file=sys.stderr)
            return 1
    for line in log:
        print(f"# {line}", file=sys.stderr)
    print(f"ZITADEL_LOGIN_CLIENT_USER_ID={user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
