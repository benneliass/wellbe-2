from __future__ import annotations

import json
from pathlib import Path

import pytest
from wellbe_api.openapi_export import build_specs

_OPENAPI_DIR = Path(__file__).resolve().parents[4] / "contracts" / "openapi"


def _serialize(spec: dict) -> str:
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize(
    "name",
    ["wellbe.openapi.json", "wellbe-v1.openapi.json", "wellbe-v2.openapi.json"],
)
def test_openapi_golden_snapshot_is_current(name: str) -> None:
    """The committed spec must match what the live app generates.

    If this fails, run: python -m wellbe_api.openapi_export
    """
    golden = (_OPENAPI_DIR / name).read_text()
    current = _serialize(build_specs()[name])
    assert current == golden, f"{name} is stale — regenerate the OpenAPI specs"


def test_v1_spec_excludes_v2_only_schemas() -> None:
    v1 = build_specs()["wellbe-v1.openapi.json"]
    schemas = set(v1.get("components", {}).get("schemas", {}))
    forbidden = {
        "InvestigationV2",
        "TheoryV2",
        "GrantV2",
        "ExternalSourceRefV2",
        "RelevanceLinkV2",
        "AccessPredicateV2",
        "RenderApprovalV2",
    }
    leak = schemas & forbidden
    assert not leak, f"v1 must not expose v2-only safety-critical DTOs: {leak}"


def test_v1_paths_are_v1_only() -> None:
    v1 = build_specs()["wellbe-v1.openapi.json"]
    for path in v1["paths"]:
        assert path == "/health" or path.startswith("/v1"), path
