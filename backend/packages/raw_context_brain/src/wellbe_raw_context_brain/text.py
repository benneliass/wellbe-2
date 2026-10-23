"""Token overlap, vectors, and the lab's deterministic random stream."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence

_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "after",
        "before",
        "at",
        "was",
        "is",
    }
)


def sha256(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _i32(value: int) -> int:
    bits = _u32(value)
    if bits >= 0x80000000:
        return bits - 0x100000000
    return bits


def _imul(left: int, right: int) -> int:
    return _i32(_i32(left) * _i32(right))


def mulberry32(seed: int) -> Callable[[], float]:
    """Same stream as the lab view. Each draw is in [0, 1)."""
    state = _u32(seed)

    def draw() -> float:
        nonlocal state
        state = _u32(state + 0x6D2B79F5)
        mixed = _imul(_u32(state ^ (state >> 15)), _u32(1 | state))
        mixed_bits = _u32(mixed)
        product = _imul(mixed_bits ^ (mixed_bits >> 7), _u32(61 | mixed_bits))
        mixed = _i32(_u32(_i32(mixed + product)) ^ mixed_bits)
        mixed_bits = _u32(mixed)
        return (mixed_bits ^ (mixed_bits >> 14)) / 4294967296

    return draw


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text.lower():
        if char.isascii() and (char.isalnum() or char == ":"):
            current.append(char)
            continue
        if current:
            token = "".join(current)
            current = []
            if len(token) > 1 and token not in _STOP:
                tokens.append(token)
    if current:
        token = "".join(current)
        if len(token) > 1 and token not in _STOP:
            tokens.append(token)
    return tokens


def jaccard(left_text: str, right_text: str) -> float:
    left = set(tokenize(left_text))
    right = set(tokenize(right_text))
    if not left and not right:
        return 0.0
    intersection = sum(1 for token in left if token in right)
    union = len(left) + len(right) - intersection
    if union == 0:
        return 0.0
    return intersection / union


def token_vector(text: str, dim: int = 32) -> list[float]:
    vector = [0.0] * dim
    for token in tokenize(text):
        hashed = int(sha256(token)[:8], 16)
        vector[hashed % dim] += 1.0
        sign = 0.5 if (hashed & 1) == 0 else -0.5
        vector[(hashed >> 8) % dim] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm > 0:
        vector = [value / norm for value in vector]
    return vector


def cosine_distance(left: Sequence[float], right: Sequence[float]) -> float:
    dot = 0.0
    for index, value in enumerate(left):
        dot += value * right[index]
    return 1.0 - dot


def edge_key(left: str, right: str) -> str:
    if left < right:
        return f"{left}|{right}"
    return f"{right}|{left}"
