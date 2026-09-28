"""C10 triage check-in red-flag evaluator (deterministic, source-linked, no LLM)."""

from wellbe_c10_safety.triage.copy import TriageCopyViolationError, copy_violations
from wellbe_c10_safety.triage.evaluator import (
    answers_sha256,
    evaluate_triage,
    match_rules,
    ruleset_fingerprint,
)
from wellbe_c10_safety.triage.rules import CLINICAL_REVIEW_STATUS, RULES, RULESET_VERSION

__all__ = [
    "CLINICAL_REVIEW_STATUS",
    "RULES",
    "RULESET_VERSION",
    "TriageCopyViolationError",
    "answers_sha256",
    "copy_violations",
    "evaluate_triage",
    "match_rules",
    "ruleset_fingerprint",
]
