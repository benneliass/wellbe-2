#!/usr/bin/env python3
"""Fail if any service image would import a workspace package it does not install.

Each backend image runs ``uv sync --package <app>``, which installs only the
declared dependency closure of that app. A ``wellbe_*`` import outside that
closure works in the dev workspace (everything installed) but crashes in the
image. Run from the repo root: ``python3 scripts/qa/check_workspace_deps.py``.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
IMPORT = re.compile(r"^\s*(?:from|import)\s+(wellbe_[a-z0-9_]+)", re.M)


def _projects() -> dict[str, Path]:
    found = {}
    for pyproject in BACKEND.glob("*/*/pyproject.toml"):
        name = tomllib.loads(pyproject.read_text())["project"]["name"]
        found[name] = pyproject.parent
    return found


def _deps(root: Path) -> set[str]:
    data = tomllib.loads((root / "pyproject.toml").read_text())
    specs = data["project"].get("dependencies", [])
    names = (re.split(r"[\[<>=~! ;]", spec, maxsplit=1)[0] for spec in specs)
    return {n for n in names if n.startswith("wellbe-")}


def _module(name: str) -> str:
    return name.replace("-", "_")


def main() -> int:
    projects = _projects()
    failures = 0
    for app, root in sorted(projects.items()):
        if root.parent.name != "apps":
            continue
        closure, todo = {app}, [app]
        while todo:
            for dep in _deps(projects[todo.pop()]):
                if dep not in closure:
                    closure.add(dep)
                    todo.append(dep)
        installed = {_module(n) for n in closure}
        for member in sorted(closure):
            src = projects[member] / "src"
            for py in src.rglob("*.py"):
                for mod in set(IMPORT.findall(py.read_text())) - installed:
                    failures += 1
                    print(f"{app}: {py.relative_to(BACKEND)} imports {mod} (not installed)")
    print("ok" if not failures else f"{failures} missing workspace dependency import(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
