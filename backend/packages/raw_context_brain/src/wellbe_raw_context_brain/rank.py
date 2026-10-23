"""Fixed rank order. The lab records the order and does not settle product weights."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from wellbe_raw_context_brain.types import Origin, Rankable

_RANK_KEYS = (
    "authorized",
    "provenance",
    "relevance",
    "novelty",
    "inverse_degree",
    "inverse_hop",
)


def _number(item: Rankable | Mapping[str, object], key: str) -> float:
    value = item[key] if isinstance(item, Mapping) else getattr(item, key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _text(item: object, key: str) -> str:
    value = item[key] if isinstance(item, Mapping) else getattr(item, key)
    return str(value)


def _optional_number(item: object, key: str) -> float:
    value = item.get(key, 0) if isinstance(item, Mapping) else getattr(item, key, 0)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def compare_rank(left: Rankable, right: Rankable) -> float:
    for key in _RANK_KEYS:
        delta = _number(right, key) - _number(left, key)
        if abs(delta) > 1e-9:
            return delta
    left_id = _text(left, "id")
    right_id = _text(right, "id")
    if left_id == right_id:
        return 0
    if left_id < right_id:
        return -1
    return 1


def degree_divisor(degree: float) -> float:
    return math.log2(2 + degree)


def inverse_degree(degree: float) -> float:
    return 1 / degree_divisor(degree)


def provenance_rank(origin: Origin) -> int:
    if origin == "user_correction":
        return 2
    if origin == "model":
        return 1
    return 0


@dataclass(frozen=True)
class HysteresisResult[T]:
    ranked: list[T]
    held_previous: bool


def apply_hysteresis[T](
    ranked: list[T],
    previous_id: str | None,
    epsilon: float = 0.05,
) -> HysteresisResult[T]:
    """Holds the previous top note only when relevance is close and no higher key is worse."""
    if not previous_id or len(ranked) < 2:
        return HysteresisResult(ranked=ranked, held_previous=False)
    index = next(
        (position for position, item in enumerate(ranked) if _text(item, "id") == previous_id),
        -1,
    )
    if index <= 0:
        return HysteresisResult(ranked=ranked, held_previous=False)
    previous = ranked[index]
    top = ranked[0]
    if _optional_number(previous, "authorized") < _optional_number(top, "authorized"):
        return HysteresisResult(ranked=ranked, held_previous=False)
    if _optional_number(previous, "provenance") < _optional_number(top, "provenance"):
        return HysteresisResult(ranked=ranked, held_previous=False)
    if abs(_optional_number(top, "relevance") - _optional_number(previous, "relevance")) <= epsilon:
        previous_key = _text(previous, "id")
        held = [previous, *[item for item in ranked if _text(item, "id") != previous_key]]
        return HysteresisResult(ranked=held, held_previous=True)
    return HysteresisResult(ranked=ranked, held_previous=False)
