"""Throwaway OIDC identities for the QA journey against an OIDC deployment.

Each identity is a fresh ZITADEL human user (created with the instance admin
token, deleted afterwards) that signs in exactly like a browser does: PKCE
authorize at ZITADEL -> WellBe's /login/submit -> ZITADEL callback -> code
exchange. So the journey also proves the sign-in path end to end.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

import httpx


@dataclass(frozen=True)
class AuthConfig:
    mode: str
    issuer: str
    client_id: str


def fetch_auth_config(web: str) -> AuthConfig:
    """The web app's runtime auth config (/auth-config.js)."""
    text = httpx.get(f"{web}/auth-config.js", timeout=20).text
    match = re.search(r"=\s*(\{.*\})\s*;", text, re.S)
    data = json.loads(match.group(1)) if match else {}
    return AuthConfig(data.get("mode", "dev"), data.get("issuer", ""), data.get("clientId", ""))


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _query(url: str, name: str) -> str:
    values = parse_qs(urlparse(url).query).get(name)
    if not values:
        raise AssertionError(f"no {name} in {url}")
    return values[0]


def sign_in(web: str, config: AuthConfig, login_name: str, password: str) -> str:
    """Browser-equivalent sign-in through WellBe's login screen; returns the access token."""
    verifier, challenge = _pkce()
    redirect_uri = f"{web}/auth/callback"
    with httpx.Client(follow_redirects=False, timeout=30) as http:
        r = http.get(
            f"{config.issuer}/oauth/v2/authorize",
            params={
                "client_id": config.client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid profile email offline_access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": secrets.token_urlsafe(12),
            },
        )
        location = r.headers.get("location", "")
        assert location.startswith(f"{web}/login?"), f"authorize -> {r.status_code} {location}"
        r = http.post(
            f"{web}/login/submit",
            headers={"Origin": web},
            json={
                "authRequestId": _query(location, "authRequest"),
                "loginName": login_name,
                "password": password,
            },
        )
        body = r.json()
        assert body.get("kind") == "ok", f"/login/submit -> {r.status_code} {body}"
        callback: str = body["callbackUrl"]
        if not callback.startswith(redirect_uri):
            callback = http.get(callback).headers.get("location", "")
        code = _query(callback, "code")
        r = http.post(
            f"{config.issuer}/oauth/v2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": config.client_id,
                "code_verifier": verifier,
            },
        )
        assert r.status_code == 200, f"token exchange -> {r.status_code} {r.text[:200]}"
        token: str = r.json()["access_token"]
        return token


@dataclass
class ThrowawayUsers:
    """ZITADEL users created for one run; ``cleanup()`` deletes them all."""

    issuer: str
    admin_token: str
    created: list[str] = field(default_factory=list)

    def _admin(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.issuer,
            headers={"Authorization": f"Bearer {self.admin_token}"},
            timeout=20,
        )

    def create(self, username: str, display_name: str) -> str:
        """Create a verified human with a random password; returns the password."""
        password = f"Qa-{secrets.token_urlsafe(18)}-9a!"
        with self._admin() as admin:
            r = admin.post(
                "/v2/users/human",
                json={
                    "username": username,
                    "profile": {"givenName": display_name, "familyName": "QA"},
                    "email": {"email": f"{username}@wellbe.invalid", "isVerified": True},
                    "password": {"password": password, "changeRequired": False},
                },
            )
        assert r.status_code in (200, 201), f"create user {username} -> {r.status_code} {r.text}"
        self.created.append(r.json()["userId"])
        return password

    def cleanup(self) -> None:
        with self._admin() as admin:
            for user_id in self.created:
                admin.delete(f"/v2/users/{user_id}")
        self.created.clear()
