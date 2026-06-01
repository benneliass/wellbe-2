"""Guarantee the DB allowed-transitions seed matches the Python matrix."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from wellbe_contracts.c14_investigation import ALLOWED_INVESTIGATION_TRANSITIONS


def _load_migration_edges() -> set[tuple[str, str]]:
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = (
        repo_root / "db" / "migrations" / "versions" / "011_c14_investigations.py"
    )
    spec = importlib.util.spec_from_file_location("c14_migration_011", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module._ALLOWED_EDGES)


def _contracts_edges() -> set[tuple[str, str]]:
    return {
        (f.value, t.value)
        for f, ts in ALLOWED_INVESTIGATION_TRANSITIONS.items()
        for t in ts
    }


def test_migration_seed_matches_contract_graph():
    assert _load_migration_edges() == _contracts_edges()
