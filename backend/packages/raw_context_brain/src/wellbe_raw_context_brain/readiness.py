"""Privacy gate for the lab's hosted judge.

The individual confirms the provider agreement and retention.
No other flag turns the hosted judge on. This module does not call the network.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LONG_DIGIT_RUN = re.compile(r"[0-9]{9,}")

ReadinessEnv = Mapping[str, str] | None


@dataclass(frozen=True)
class NotRunColumn:
    column: Literal["not_run"] = "not_run"


@dataclass(frozen=True)
class ModelColumn:
    column: Literal["model"] = "model"


@dataclass(frozen=True)
class FounderColumn:
    column: Literal["founder"]
    pairs: list[object]


@dataclass(frozen=True)
class HeuristicColumn:
    column: Literal["heuristic"] = "heuristic"


ModelColumnResult = NotRunColumn | ModelColumn
FounderColumnResult = FounderColumn | HeuristicColumn


def hosted_judge_allowed(env: ReadinessEnv) -> bool:
    if env is None:
        return False
    agreement = env.get("WELLBE_PROVIDER_AGREEMENT") == "on"
    retention = env.get("WELLBE_RETENTION_CONFIRMED") == "on"
    return agreement and retention


def model_column(env: ReadinessEnv) -> ModelColumnResult:
    """Live model column. A heuristic percentage is never attached."""
    api_key = None if env is None else env.get("OPENAI_API_KEY")
    key_present = isinstance(api_key, str) and api_key.strip() != ""
    if not hosted_judge_allowed(env) or not key_present:
        return NotRunColumn()
    return ModelColumn()


def load_founder_gold(parsed: object) -> FounderColumnResult:
    if not isinstance(parsed, dict):
        return HeuristicColumn()
    reviewer = parsed.get("reviewer")
    pairs = parsed.get("pairs")
    if (
        parsed.get("reviewed") is not True
        or not isinstance(reviewer, str)
        or reviewer.strip() == ""
        or not isinstance(pairs, list)
    ):
        return HeuristicColumn()
    return FounderColumn(column="founder", pairs=pairs)


def assert_lab_note(text: str, env: ReadinessEnv) -> None:
    if hosted_judge_allowed(env):
        return
    if _EMAIL.search(text) or _LONG_DIGIT_RUN.search(text):
        raise ValueError("real_note_blocked")
