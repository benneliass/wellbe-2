"""Grounding checks. A schema cannot see the note or the handles this request issued."""

from __future__ import annotations

from collections.abc import Mapping

_NEEDS_HANDLE = frozenset({"link", "open_content", "walk"})
_NO_HANDLE = frozenset({"no_link", "uncertain", "standalone"})


def run_check(name: str, value: Mapping[str, object], payload: Mapping[str, object]) -> bool:
    if name == "keywords_in_text":
        return _keywords_in_text(value, payload)
    if name == "issued_handle":
        return _issued_handle(value, payload)
    if name == "decision_handles":
        return _decision_handles(value, payload)
    return False


def _keywords_in_text(value: Mapping[str, object], payload: Mapping[str, object]) -> bool:
    text = payload.get("text")
    words = value.get("keywords")
    if not isinstance(text, str) or not isinstance(words, list):
        return False
    haystack = text.casefold()
    return all(isinstance(word, str) and word.casefold() in haystack for word in words)


def _issued_handle(value: Mapping[str, object], payload: Mapping[str, object]) -> bool:
    verdict = value.get("verdict")
    handle = value.get("handle")
    issued = payload.get("issued_handles")
    if not isinstance(verdict, str) or not isinstance(issued, list):
        return False
    allowed = {item for item in issued if isinstance(item, str)}
    if verdict in _NEEDS_HANDLE:
        return isinstance(handle, str) and handle in allowed
    if verdict in _NO_HANDLE:
        return handle is None
    return False


def _decision_handles(value: Mapping[str, object], payload: Mapping[str, object]) -> bool:
    decisions = value.get("decisions")
    issued = payload.get("issued_handles")
    if not isinstance(decisions, list) or not isinstance(issued, list):
        return False
    allowed = {item for item in issued if isinstance(item, str)}
    for item in decisions:
        if not isinstance(item, dict):
            return False
        handle = item.get("handle")
        if not isinstance(handle, str) or handle not in allowed:
            return False
    return True
