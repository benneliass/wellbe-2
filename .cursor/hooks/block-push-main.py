#!/usr/bin/env python3
"""Reject a shell command that pushes to main."""

from __future__ import annotations

import json
import re
import sys

def is_push_to_main(command: str) -> bool:
    if re.search(r"git\s+push\b", command) is None:
        return False
    if re.search(r"(?:^|\s)(?:\S+:)?main(?:\s|$)", command):
        return True
    if re.search(r"\brefs/heads/main\b", command):
        return True
    return False


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    command = str(payload.get("command") or "")
    if is_push_to_main(command):
        json.dump(
            {
                "permission": "deny",
                "user_message": "Pushing to main is blocked. Open a pull request instead.",
                "agent_message": "A project hook rejected this push because its destination is main.",
            },
            sys.stdout,
        )
        return 0
    json.dump({"permission": "allow"}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
