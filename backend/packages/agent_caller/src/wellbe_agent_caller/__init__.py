"""The one way WellBe calls an external agent. Features register their own purposes."""

from wellbe_agent_caller.caller import ask, known_purposes, register_purpose
from wellbe_agent_caller.types import AskFailure, AskSuccess, Binding, Field, Purpose

__all__ = [
    "AskFailure",
    "AskSuccess",
    "Binding",
    "Field",
    "Purpose",
    "ask",
    "known_purposes",
    "register_purpose",
]
