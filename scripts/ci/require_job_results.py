#!/usr/bin/env python3
"""Fail the CI gate unless every module passed or was skipped on purpose.

``changes`` and ``classifier`` always run, so anything other than success there
means the path split itself is untrusted. Every other job may be skipped when
its paths did not change. A missing result fails closed: a job dropped from
the workflow env must not look green.
"""

from __future__ import annotations

import os
import sys

# Job ids in .github/workflows/ci.yml. The orchestrator test checks the
# workflow still passes each of these in as RESULT_<NAME>.
EXPECTED = (
    "changes",
    "classifier",
    "backend",
    "frontend",
    "browser",
    "labs",
    "migrations",
    "safety",
    "capability",
    "cluster",
)

MUST_SUCCEED = frozenset({"changes", "classifier"})
ALLOWED = frozenset({"success", "skipped"})


def evaluate(results: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for name in EXPECTED:
        raw = results.get(name)
        if raw is None or raw.strip() == "":
            problems.append(f"{name}: missing result")
            continue
        value = raw.strip().lower()
        if name in MUST_SUCCEED:
            if value != "success":
                problems.append(f"{name}: {value}, expected success")
        elif value not in ALLOWED:
            problems.append(f"{name}: {value}")
    return problems


def results_from_env(environ: dict[str, str]) -> dict[str, str]:
    prefix = "RESULT_"
    found: dict[str, str] = {}
    for key, value in environ.items():
        if not key.startswith(prefix):
            continue
        found[key[len(prefix) :].lower()] = value
    return found


def main() -> int:
    problems = evaluate(results_from_env(dict(os.environ)))
    if problems:
        print("CI gate failed:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print("CI gate passed: every module succeeded or was skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
