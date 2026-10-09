#!/usr/bin/env python3
"""Check docs/current/capability-index.md structure and evidence paths.

The checker looks at paths, not behavior. A listed evidence path must exist.
A partial row must name a gap. Status must be one of the closed set.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "current" / "capability-index.md"
STATUSES = {"shipped", "partial", "designed", "deferred"}


def parse_tables(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        if len(cells) != len(header):
            raise SystemExit(f"row has {len(cells)} cells, header has {len(header)}: {stripped}")
        rows.append(dict(zip(header, cells)))
    return rows


def evidence_paths(cell: str) -> list[str]:
    paths: list[str] = []
    parts = cell.replace("`", " ").replace(",", " ").split()
    for part in parts:
        if "/" in part or part.endswith(".py") or part.endswith(".tsx") or part.endswith(".ts"):
            paths.append(part)
    return paths


def main() -> int:
    if not INDEX.is_file():
        print(f"missing {INDEX.relative_to(ROOT)}", file=sys.stderr)
        return 1
    rows = parse_tables(INDEX.read_text())
    if not rows:
        print("no capability rows found", file=sys.stderr)
        return 1
    errors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        ident = row.get("id", "")
        status = row.get("status", "")
        gap = row.get("gap", "").strip()
        if not ident:
            errors.append("row is missing id")
            continue
        if ident in seen:
            errors.append(f"{ident}: duplicate id")
        seen.add(ident)
        if status not in STATUSES:
            errors.append(f"{ident}: status {status!r} is outside shipped|partial|designed|deferred")
        if status == "partial" and gap in {"", "—", "-"}:
            errors.append(f"{ident}: partial row has no gap")
        for path in evidence_paths(row.get("evidence", "")):
            if not (ROOT / path).exists():
                errors.append(f"{ident}: evidence path does not exist: {path}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok {len(rows)} capabilities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
