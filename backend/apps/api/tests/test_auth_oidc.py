"""WELLBE_AUTH_MODE=oidc boundary tests.

Tokens are signed with an RSA key generated per test session and verified against
a local in-memory JWKS, so nothing touches the network. Covers: a valid token
yields the account-bound principal; bad signature / wrong audience / expired /
missing token -> 401; X-Wellbe-* identity headers are ignored; an identity with no
finalized account -> 403 onboarding_required while onboarding itself still works;
and JWKS key rotation (unknown kid triggers a refresh).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from wellbe_api import deps
from wellbe_api import main as api_main
from wellbe_api.auth import OidcVerifier, TokenInvalidError
from wellbe_api.deps import IdentityDep, OnboardingRequiredError, PrincipalDep, get_session
from wellbe_api.routers import onboarding_v1

_ISSUER = "https://auth.test.example"
_AUDIENCE = "wellbe-project-123"
_SUBJECT = "zitadel-user-1"
_UNKNOWN_SUBJECT = "zitadel-user-unknown"
_PATIENT = uuid.UUID("de7a0000-0000-4000-8000-000000000001")
_OTHER = uuid.UUID("99999999-9999-4999-8999-999999999999")


def _rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


_KEY = _rsa_key()
_OTHER_KEY = _rsa_key()


def _jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, Any]:
    jwk: dict[str, Any] = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return jwk


def _token(
    *,
    key: rsa.RSAPrivateKey = _KEY,
    kid: str = "k1",
    sub: str = _SUBJECT,
    aud: str | list[str] = _AUDIENCE,
    iss: str = _ISSUER,
    exp_in: int = 300,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": iss,
        "sub": sub,
        "aud": aud,
        "iat": now,
        "nbf": now,
        "exp": now + exp_in,
    }
    claims.update(extra or {})
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


class _Jwks:
    def __init__(self, *keys: dict[str, Any]) -> None:
        self.keys = list(keys)
        self.calls = 0

    async def __call__(self) -> dict[str, Any]:
        self.calls += 1
        return {"keys": self.keys}


class _FakeOnboardingService:
    accounts: dict[tuple[str, str], uuid.UUID] = {(_ISSUER, _SUBJECT): _PATIENT}

    def __init__(self, _session: Any) -> None: ...

    async def active_controller_patient_id(self, *, issuer: str, subject: str) -> uuid.UUID | None:
        return self.accounts.get((issuer, subject))


class _FakeSession:
    async def commit(self) -> None: ...


@pytest.fixture
def jwks() -> _Jwks:
    return _Jwks(_jwk(_KEY, "k1"))


@pytest.fixture(autouse=True)
def _oidc_mode(monkeypatch: pytest.MonkeyPatch, jwks: _Jwks) -> AsyncGenerator[None]:
    monkeypatch.setattr(deps.settings, "auth_mode", "oidc")
    monkeypatch.setattr(
        deps,
        "_oidc_verifier",
        OidcVerifier(issuer=_ISSUER, audiences=[_AUDIENCE], fetch_jwks=jwks),
    )
    monkeypatch.setattr(deps, "OnboardingService", _FakeOnboardingService)

    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    api_main.app.dependency_overrides[get_session] = _fake_session
    probe.dependency_overrides[get_session] = _fake_session
    yield
    api_main.app.dependency_overrides.pop(get_session, None)
    probe.dependency_overrides.pop(get_session, None)


# A minimal app exposing the resolved principal/identity, with the real handlers.
probe = FastAPI()
probe.add_exception_handler(deps.UnauthenticatedError, api_main._unauth_handler)  # type: ignore[arg-type]
probe.add_exception_handler(OnboardingRequiredError, api_main._onboarding_handler)  # type: ignore[arg-type]


@probe.get("/whoami")
async def _whoami(principal: PrincipalDep) -> dict[str, Any]:
    return {
        "actor_id": str(principal.actor_id),
        "patient_id": str(principal.patient_id),
        "actor_type": principal.actor_type,
        "is_controller": principal.is_controller,
    }


@probe.get("/identity")
async def _identity(identity: IdentityDep) -> dict[str, Any]:
    return {"issuer": identity.issuer, "subject": identity.subject}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_resolves_account_principal() -> None:
    resp = TestClient(probe).get("/whoami", headers=_bearer(_token()))
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "actor_id": str(_PATIENT),
        "patient_id": str(_PATIENT),
        "actor_type": "controller",
        "is_controller": True,
    }


def test_audience_list_containing_configured_audience_is_accepted() -> None:
    token = _token(aud=["client-abc", _AUDIENCE])
    assert TestClient(probe).get("/whoami", headers=_bearer(token)).status_code == 200


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_token(key=_OTHER_KEY), id="bad-signature"),
        pytest.param(_token(aud="someone-else"), id="wrong-audience"),
        pytest.param(_token(iss="https://evil.example"), id="wrong-issuer"),
        pytest.param(_token(exp_in=-120), id="expired"),
        pytest.param("not-a-jwt", id="malformed"),
    ],
)
def test_invalid_tokens_are_401(token: str) -> None:
    resp = TestClient(probe).get("/whoami", headers=_bearer(token))
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"
    assert resp.headers["www-authenticate"].startswith("Bearer")


def test_symmetric_alg_confusion_is_rejected() -> None:
    public_pem = _jwk(_KEY, "k1")["n"]
    forged = jwt.encode(
        {"iss": _ISSUER, "sub": _SUBJECT, "aud": _AUDIENCE, "exp": int(time.time()) + 60},
        public_pem,
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    assert TestClient(probe).get("/whoami", headers=_bearer(forged)).status_code == 401


def test_expiry_within_leeway_is_accepted() -> None:
    token = _token(exp_in=-5)
    assert TestClient(probe).get("/whoami", headers=_bearer(token)).status_code == 200


def test_missing_token_is_401_even_with_dev_headers() -> None:
    resp = TestClient(probe).get(
        "/whoami",
        headers={
            "X-Wellbe-Actor-Id": str(_PATIENT),
            "X-Wellbe-Issuer": _ISSUER,
            "X-Wellbe-Subject": _SUBJECT,
        },
    )
    assert resp.status_code == 401
    assert TestClient(probe).get("/identity", headers={"X-Wellbe-Subject": "x"}).status_code == 401


def test_identity_headers_are_ignored_in_oidc_mode() -> None:
    headers = {
        **_bearer(_token()),
        "X-Wellbe-Actor-Id": str(_OTHER),
        "X-Wellbe-Actor-Type": "controller",
        "X-Wellbe-Issuer": "dev-local",
        "X-Wellbe-Subject": "dev-controller",
    }
    who = TestClient(probe).get("/whoami", headers=headers).json()
    assert who["actor_id"] == str(_PATIENT)
    ident = TestClient(probe).get("/identity", headers=headers).json()
    assert ident == {"issuer": _ISSUER, "subject": _SUBJECT}


def test_foreign_patient_header_is_never_controller() -> None:
    headers = {
        **_bearer(_token()),
        "X-Wellbe-Patient-Id": str(_OTHER),
        "X-Wellbe-Actor-Type": "controller",
    }
    who = TestClient(probe).get("/whoami", headers=headers).json()
    assert who["actor_id"] == str(_PATIENT)
    assert who["patient_id"] == str(_OTHER)
    assert who["is_controller"] is False
    assert who["actor_type"] == "user"


def test_unknown_subject_is_onboarding_required_on_data_routes() -> None:
    token = _token(sub=_UNKNOWN_SUBJECT)
    resp = TestClient(api_main.app).get("/v1/threads", headers=_bearer(token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "onboarding_required"


def test_unknown_subject_can_still_reach_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    class _Svc:
        def __init__(self, _session: Any) -> None: ...

        async def find_account(self, *, issuer: str, subject: str) -> None:
            seen.update(issuer=issuer, subject=subject)
            return None

    monkeypatch.setattr(onboarding_v1, "OnboardingService", _Svc)
    token = _token(sub=_UNKNOWN_SUBJECT)
    resp = TestClient(api_main.app).get(
        "/v1/onboarding",
        headers={**_bearer(token), "X-Wellbe-Subject": "spoofed", "X-Wellbe-Issuer": "dev-local"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "none"
    assert seen == {"issuer": _ISSUER, "subject": _UNKNOWN_SUBJECT}


async def test_unknown_kid_triggers_jwks_refresh() -> None:
    source = _Jwks(_jwk(_KEY, "k1"))
    verifier = OidcVerifier(
        issuer=_ISSUER, audiences=[_AUDIENCE], fetch_jwks=source, min_refresh_interval_seconds=0
    )
    await verifier.verify(_token())
    await verifier.verify(_token())
    assert source.calls == 1  # cached within TTL

    source.keys.append(_jwk(_OTHER_KEY, "k2"))  # issuer rotates in a new key
    claims = await verifier.verify(_token(key=_OTHER_KEY, kid="k2"))
    assert claims["sub"] == _SUBJECT
    assert source.calls == 2


async def test_unknown_kid_refresh_is_rate_limited() -> None:
    source = _Jwks(_jwk(_KEY, "k1"))
    verifier = OidcVerifier(issuer=_ISSUER, audiences=[_AUDIENCE], fetch_jwks=source)
    await verifier.verify(_token())
    for _ in range(3):
        with pytest.raises(TokenInvalidError):
            await verifier.verify(_token(kid="nope"))
    assert source.calls == 1


def test_verifier_refuses_incomplete_config() -> None:
    with pytest.raises(ValueError):
        OidcVerifier(issuer=_ISSUER, audiences=[], fetch_jwks=_Jwks())
    with pytest.raises(ValueError):
        OidcVerifier(
            issuer=_ISSUER, audiences=[_AUDIENCE], fetch_jwks=_Jwks(), algorithms=["HS256"]
        )
