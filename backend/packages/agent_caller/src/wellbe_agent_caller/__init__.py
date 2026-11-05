"""The one way WellBe calls an external agent."""

from wellbe_agent_caller.caller import ask, known_purposes, register_purpose
from wellbe_agent_caller.purposes import KEYWORD_PASS, LINK_JUDGMENT, VISION_READ
from wellbe_agent_caller.types import AskFailure, AskSuccess, Binding, Purpose

__all__ = [
    "KEYWORD_PASS",
    "LINK_JUDGMENT",
    "VISION_READ",
    "AskFailure",
    "AskSuccess",
    "Binding",
    "Purpose",
    "ask",
    "known_purposes",
    "register_purpose",
]
