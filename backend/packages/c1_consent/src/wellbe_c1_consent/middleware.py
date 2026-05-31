from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status

from wellbe_c1_consent.zitadel import ZitadelTokenVerifier

_verifier: ZitadelTokenVerifier | None = None


def configure_auth(zitadel_domain: str, audience: str | None = None) -> None:
    global _verifier  # noqa: PLW0603
    _verifier = ZitadelTokenVerifier(zitadel_domain, audience=audience)


async def auth_dependency(request: Request) -> dict[str, Any]:
    if _verifier is None:
        raise RuntimeError("auth not configured — call configure_auth() at startup")

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        claims = await _verifier.verify_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    actor_id_raw = claims.get("sub")
    if not actor_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    try:
        actor_id = UUID(actor_id_raw)
    except ValueError:
        actor_id = None

    return {
        "actor_id": actor_id,
        "sub": actor_id_raw,
        "scopes": claims.get("scope", "").split(),
        "claims": claims,
    }
