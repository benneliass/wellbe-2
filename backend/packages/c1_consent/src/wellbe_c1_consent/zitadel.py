from __future__ import annotations

import time

import httpx
import jwt
from jwt import PyJWKClient


class ZitadelTokenVerifier:
    JWKS_REFRESH_INTERVAL = 3600

    def __init__(self, zitadel_domain: str, audience: str | None = None) -> None:
        self._issuer = zitadel_domain.rstrip("/")
        self._audience = audience
        self._jwks_client: PyJWKClient | None = None
        self._jwks_fetched_at: float = 0

    async def verify_token(self, token: str) -> dict:
        jwks_client = await self._get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        options: dict = {}
        if self._audience is None:
            options["verify_aud"] = False

        claims: dict = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=self._audience,
            options=options,
        )
        return claims

    async def _get_jwks_client(self) -> PyJWKClient:
        now = time.monotonic()
        if self._jwks_client is not None and (now - self._jwks_fetched_at) < self.JWKS_REFRESH_INTERVAL:
            return self._jwks_client

        oidc_url = f"{self._issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            resp = await client.get(oidc_url)
            resp.raise_for_status()
            config = resp.json()

        jwks_uri = config["jwks_uri"]
        self._jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
        self._jwks_fetched_at = now
        return self._jwks_client
