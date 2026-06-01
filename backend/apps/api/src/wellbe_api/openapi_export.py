"""Export OpenAPI specs for the C13 boundary.

Emits three golden specs into ``contracts/openapi/``:

- ``wellbe.openapi.json``  — combined (drives the generated TS client).
- ``wellbe-v1.openapi.json`` — only ``/health`` + ``/v1/*`` paths and the schemas
  they reference. This proves v1 excludes v2-only fields (deep-grant, Theory,
  Investigation, external-evidence internals) — old clients cannot silently
  ignore safety-critical v2 fields because the v1 contract never contains them.
- ``wellbe-v2.openapi.json`` — only ``/v2/*`` paths and their schemas.

Run: ``python -m wellbe_api.openapi_export`` (writes files) or import ``build_specs``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from wellbe_api.main import app

_REF_RE = re.compile(r"#/components/schemas/([^\"/]+)")


def _collect_refs(node: Any, acc: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            m = _REF_RE.fullmatch(ref)
            if m:
                acc.add(m.group(1))
        for value in node.values():
            _collect_refs(value, acc)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, acc)


def _closure(seed: set[str], schemas: dict[str, Any]) -> set[str]:
    """Transitive closure of schema names reachable from ``seed``."""
    keep = set(seed)
    frontier = set(seed)
    while frontier:
        nxt: set[str] = set()
        for name in frontier:
            refs: set[str] = set()
            _collect_refs(schemas.get(name, {}), refs)
            nxt |= refs - keep
        keep |= nxt
        frontier = nxt
    return keep


def _subset(spec: dict[str, Any], *, keep_path: Any) -> dict[str, Any]:
    paths = {p: item for p, item in spec["paths"].items() if keep_path(p)}
    seed: set[str] = set()
    _collect_refs(paths, seed)
    all_schemas = spec.get("components", {}).get("schemas", {})
    keep = _closure(seed, all_schemas)
    out: dict[str, Any] = {
        "openapi": spec["openapi"],
        "info": dict(spec["info"]),
        "paths": paths,
    }
    if keep:
        kept = {n: all_schemas[n] for n in sorted(keep) if n in all_schemas}
        out["components"] = {"schemas": kept}
    return out


def build_specs() -> dict[str, dict[str, Any]]:
    combined = app.openapi()
    v1 = _subset(combined, keep_path=lambda p: p == "/health" or p.startswith("/v1"))
    v1["info"] = {**v1["info"], "title": "WellBe API (v1)"}
    v2 = _subset(combined, keep_path=lambda p: p.startswith("/v2"))
    v2["info"] = {**v2["info"], "title": "WellBe API (v2)"}
    return {
        "wellbe.openapi.json": combined,
        "wellbe-v1.openapi.json": v1,
        "wellbe-v2.openapi.json": v2,
    }


def _repo_root() -> Path:
    # backend/apps/api/src/wellbe_api/openapi_export.py -> repo root is parents[5]
    return Path(__file__).resolve().parents[5]


def write_specs(out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or (_repo_root() / "contracts" / "openapi")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, spec in build_specs().items():
        path = out_dir / name
        path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for path in write_specs():
        print(f"wrote {path}")
