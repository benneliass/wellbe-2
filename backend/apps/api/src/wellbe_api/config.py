"""C13 API settings."""

from __future__ import annotations

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WELLBE_", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://wellbe:wellbe_dev@wellbe-postgres:5432/wellbe"
    )
    redis_url: str = "redis://wellbe-redis:6379/0"
    # C3 ingestion worker (the capture write path forwards here; it owns the
    # adapter registry and the C2 Vault append).
    ingestion_worker_url: str = "http://ingestion-worker:8003"
    # C10 render-token HMAC secret. Matches the safety-gate default so render
    # tokens minted at visit-packet share time validate consistently.
    c10_token_secret: SecretStr = SecretStr("local-dev-c10-render-token-secret")
    # Deployment-level ISO region for triage emergency-number substitution (e.g.
    # "GB" -> 999). Unset keeps the generalized "your local emergency number".
    triage_default_region: str | None = None
    log_level: str = "INFO"
    environment: str = "dev"
    # Browser origins allowed to call this boundary cross-origin. The web app is
    # served from a different host (app.localhost) than the API (api.localhost),
    # and every data request carries custom X-Wellbe-* headers, which forces a
    # CORS preflight. Without an allow-list the browser blocks all data fetches.
    # Override via WELLBE_CORS_ALLOW_ORIGINS (JSON list) per environment.
    cors_allow_origins: list[str] = [
        "http://app.localhost",
        "https://app.localhost",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # How the boundary authenticates callers.
    #   dev-headers — trusts X-Wellbe-* identity headers (local kind, tests, CI).
    #   oidc        — requires a ZITADEL-issued JWT access token; identity headers
    #                 are ignored and the actor is resolved from identity.accounts.
    auth_mode: Literal["dev-headers", "oidc"] = "dev-headers"
    # Exact `iss` claim value, e.g. https://wellbe-auth.tail9c487a.ts.net
    oidc_issuer: str = ""
    # Accepted `aud` values, comma-separated (ZITADEL puts the project id and the
    # client id in access-token audiences; either is sufficient).
    oidc_audience: str = ""
    # Optional explicit JWKS URL (skips discovery), e.g. the in-cluster Service
    # http://zitadel:8090/oauth/v2/keys. Pair with oidc_jwks_host_header so ZITADEL
    # resolves its instance from the external domain.
    oidc_jwks_url: str = ""
    oidc_jwks_host_header: str = ""
    oidc_algorithms: str = "RS256"
    oidc_leeway_seconds: int = 30
    oidc_jwks_cache_ttl_seconds: int = 3600

    @property
    def oidc_audiences(self) -> list[str]:
        return [a.strip() for a in self.oidc_audience.split(",") if a.strip()]

    @property
    def oidc_algorithm_list(self) -> list[str]:
        return [a.strip() for a in self.oidc_algorithms.split(",") if a.strip()]
