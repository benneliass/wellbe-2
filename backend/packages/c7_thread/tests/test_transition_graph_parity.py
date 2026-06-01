"""Guarantee the DB allowed-transitions seed matches the Python graph.

The migration cannot import wellbe_contracts (the migration image only ships
db/migrations), so the edge list is duplicated. This test fails loudly if the
two ever drift.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from wellbe_contracts.c7_thread import ALLOWED_TRANSITIONS


def _load_migration_edges() -> set[tuple[str, str]]:
    # tests -> c7_thread -> packages -> backend -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = repo_root / "db" / "migrations" / "versions" / "010_c7_health_threads.py"
    spec = importlib.util.spec_from_file_location("c7_migration_010", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module._ALLOWED_EDGES)


def _contracts_edges() -> set[tuple[str, str]]:
    return {
        (f.value, t.value)
        for f, targets in ALLOWED_TRANSITIONS.items()
        for t in targets
    }


def test_migration_seed_matches_contract_graph():
    assert _load_migration_edges() == _contracts_edges()
