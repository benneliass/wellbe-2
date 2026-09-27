"""OIDC bearer-token verification for the C13 boundary (WELLBE_AUTH_MODE=oidc).

Access tokens are JWTs issued by ZITADEL. They are verified locally against the
issuer's JWKS: signature (asymmetric algorithms only), ``iss``, ``aud`` (the
configured project / client ids), and ``exp``/``nbf`` with a small leeway. Keys
are cached with a TTL and re-fetched when a token carries an unknown ``kid``
(key rotation), rate-limited so garbage ``kid`` values cannot hammer the issuer.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import jwt

JwksFetcher = Callable[[], Awaitable[dict[str, Any]]]

# Symmetric algorithms are never accepted: the JWKS is public, so an HS* token
# "signed" with a public key would otherwise verify.
_ALLOWED_ALGORITHMS = frozenset({"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256"})


class TokenInvalidError(Exception):
    """The bearer token is missing, malformed, or failed verification."""


class OidcVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audiences: list[str],
        fetch_jwks: JwksFetcher,
        algorithms: list[str] | None = None,
        leeway_seconds: int = 30,
        cache_ttl_seconds: int = 3600,
        min_refresh_interval_seconds: float = 30.0,
    ) -> None:
        if not issuer:
            raise ValueError("OIDC issuer is required")
        if not audiences:
            raise ValueError("at least one OIDC audience is required")
        algs = algorithms or ["RS256"]
        unsupported = set(algs) - _ALLOWED_ALGORITHMS
        if unsupported:
            raise ValueError(f"unsupported JWT algorithms: {sorted(unsupported)}")
        self._issuer = issuer
        self._audiences = audiences
        self._algorithms = algs
        self._leeway = leeway_seconds
        self._ttl = cache_ttl_seconds
        self._min_refresh = min_refresh_interval_seconds
        self._fetch_jwks = fetch_jwks
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def issuer(self) -> str:
        return self._issuer

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise TokenInvalidError("malformed token") from exc
        kid = header.get("kid")
        alg = header.get("alg")
        if not isinstance(kid, str) or alg not in self._algorithms:
            raise TokenInvalidError("token header rejected")

        key = await self._key_for(kid)
        if key.algorithm_name != alg:
            raise TokenInvalidError("token algorithm does not match signing key")
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key.key,
                algorithms=[alg],
                audience=self._audiences,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iss", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise TokenInvalidError(type(exc).__name__) from exc
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise TokenInvalidError("token subject missing")
        return claims

    async def _key_for(self, kid: str) -> jwt.PyJWK:
        now = time.monotonic()
        stale = self._fetched_at is None or (now - self._fetched_at) >= self._ttl
        if not stale and kid in self._keys:
            return self._keys[kid]
        async with self._lock:
            now = time.monotonic()
            stale = self._fetched_at is None or (now - self._fetched_at) >= self._ttl
            may_refresh = self._fetched_at is None or (now - self._fetched_at) >= self._min_refresh
            if (stale or kid not in self._keys) and may_refresh:
                await self._refresh()
        key = self._keys.get(kid)
        if key is None:
            raise TokenInvalidError("unknown signing key")
        return key

    async def _refresh(self) -> None:
        try:
            jwks = await self._fetch_jwks()
        except Exception as exc:  # noqa: BLE001 - any fetch failure is a verify failure
            if self._keys:
                # Keep serving the last known keys; retry after the min interval.
                self._fetched_at = time.monotonic() - self._ttl + self._min_refresh
                return
            raise TokenInvalidError("signing keys unavailable") from exc
        keys: dict[str, jwt.PyJWK] = {}
        for entry in jwks.get("keys", []):
            if entry.get("use", "sig") != "sig" or not entry.get("kid"):
                continue
            try:
                keys[entry["kid"]] = jwt.PyJWK(entry, algorithm=entry.get("alg"))
            except jwt.PyJWTError:
                continue
        self._keys = keys
        self._fetched_at = time.monotonic()


def http_jwks_fetcher(
    *, issuer: str, jwks_url: str = "", host_header: str = "", timeout: float = 5.0
) -> JwksFetcher:
    """JWKS fetcher over HTTP. Without an explicit ``jwks_url`` the issuer's
    discovery document is consulted. ``host_header`` lets an in-cluster caller reach
    ZITADEL by its Service name while presenting the external domain ZITADEL uses
    to resolve the instance."""
    headers = {"Host": host_header} if host_header else {}

    async def _fetch() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            url = jwks_url
            if not url:
                resp = await client.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
                resp.raise_for_status()
                url = resp.json()["jwks_uri"]
            resp = await client.get(url)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data

    return _fetch


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise TokenInvalidError("missing bearer token")
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise TokenInvalidError("missing bearer token")
    return token
