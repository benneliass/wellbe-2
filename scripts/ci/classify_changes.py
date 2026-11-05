#!/usr/bin/env python3
"""Map a list of changed paths to the CI modules that must run.

The image-updater write-back is ignored, so a commit that only moves an image
tag selects no module. A missing diff (``#unknown``) or any edit under
``.github/workflows/`` or ``.github/actions/`` turns every module on: skipping
tests because the diff could not be read would hide a broken change.
"""

from __future__ import annotations

import sys
from pathlib import Path

UNKNOWN = "#unknown"
IMAGE_UPDATER = "infra/helm/wellbe-local/.argocd-source-wellbe.yaml"

MODULES = (
    "python",
    "node",
    "browser",
    "labs",
    "migrations",
    "safety",
    "capability",
    "deploy",
)

# (module, path prefixes, exact files). A prefix must include its trailing slash.
RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "python",
        ("backend/",),
        ("scripts/qa/check_workspace_deps.py",),
    ),
    (
        "node",
        ("apps/", "packages/"),
        ("package.json", "package-lock.json"),
    ),
    (
        "browser",
        ("apps/web/", "packages/ui/", "packages/api-client/"),
        (),
    ),
    (
        "labs",
        ("labs/raw-context-brain/",),
        (),
    ),
    (
        "migrations",
        ("db/",),
        ("infra/local/Dockerfile.postgres",),
    ),
    (
        "safety",
        (
            "backend/packages/c10_safety/",
            "backend/packages/contracts/src/wellbe_contracts/triage/",
            "backend/apps/safety-gate/",
            "evals/safety/",
            "docs/safety/",
        ),
        (
            ".cursor/rules/wellbe-vision-guardrails.mdc",
            ".cursor/rules/audience-guardrails.mdc",
        ),
    ),
    (
        "capability",
        ("docs/",),
        ("scripts/check-capability-index.py",),
    ),
    (
        "deploy",
        (
            "backend/",
            "apps/web/",
            "packages/",
            "db/",
            "infra/helm/",
            "infra/k8s/",
        ),
        (
            "package.json",
            "package-lock.json",
            "infra/local/Dockerfile.postgres",
        ),
    ),
)


def _clean(path: str) -> str:
    text = path.strip().replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def _matches(path: str, prefixes: tuple[str, ...], files: tuple[str, ...]) -> bool:
    return path in files or any(path.startswith(prefix) for prefix in prefixes)


def classify(paths: list[str]) -> dict[str, bool]:
    cleaned = [item for item in (_clean(path) for path in paths) if item]
    if any(path == UNKNOWN for path in cleaned):
        return {name: True for name in MODULES}

    meaningful = [path for path in cleaned if path != IMAGE_UPDATER]
    if any(
        path.startswith(".github/workflows/") or path.startswith(".github/actions/")
        for path in meaningful
    ):
        return {name: True for name in MODULES}

    flags = {name: False for name in MODULES}
    for name, prefixes, files in RULES:
        flags[name] = any(_matches(path, prefixes, files) for path in meaningful)
    return flags


def format_output(flags: dict[str, bool]) -> str:
    missing = [name for name in MODULES if name not in flags]
    if missing:
        raise ValueError(f"missing modules: {', '.join(missing)}")
    return "".join(f"{name}={'true' if flags[name] else 'false'}\n" for name in MODULES)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: classify_changes.py CHANGED_PATHS_FILE", file=sys.stderr)
        return 2
    paths = Path(argv[1]).read_text(encoding="utf-8").splitlines()
    flags = classify(paths)
    sys.stdout.write(format_output(flags))
    selected = [name for name in MODULES if flags[name]]
    print(
        "modules: " + (", ".join(selected) if selected else "(none)"),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
