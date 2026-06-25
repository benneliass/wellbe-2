"""Versioned vital-sign concept registry (WEL-185).

Per the approved decision (docs/decisions/structured-capture-extraction-typing.md),
WellBe has no dedicated ``vital`` capture type — vitals arrive as ``capture_type=lab``.
Inside the structured-observation extractor a lab payload is typed ``vital_sign``
only when its test name matches a **governed, versioned** vital concept here;
otherwise it stays ``lab_result``.

This registry is the single, testable contract for that content-based distinction.
It is intentionally small and conservative (the FHIR Vital Signs minimum set):
adding aliases/concepts is backward-compatible; *reclassifying* an existing
normalized key requires a new ``VITAL_REGISTRY_VERSION`` + a backfill plan.

No clinical interpretation lives here — only identity (is this test a vital, and
which canonical vital concept is it). Normality/abnormality is never computed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Bump on any *reclassification* (a key that used to be lab_result becoming a
# vital, or a concept key changing). Additive aliases do not require a bump.
VITAL_REGISTRY_VERSION = "vital-registry-v1"


@dataclass(frozen=True)
class VitalConcept:
    """A canonical vital-sign concept.

    ``key``      — stable concept slug (no kind prefix), used in the normalized key.
    ``display``  — canonical human label (provenance keeps the source test name).
    ``aliases``  — normalized name fragments that identify this concept. Multi-word
                   aliases match as a substring of the normalized test name;
                   single-word aliases match a whole token (avoids e.g. "bp"
                   matching inside "bnp").
    ``composite``— true for observations carried as components (blood pressure →
                   systolic/diastolic), which the extractor parses into components.
    """

    key: str
    display: str
    aliases: tuple[str, ...]
    composite: bool = False


# FHIR Vital Signs minimum concept set (S3/S6 in the findings). Conservative by
# design — unknown home/device vitals fall through to lab_result until added.
_VITALS: tuple[VitalConcept, ...] = (
    VitalConcept(
        key="blood_pressure",
        display="Blood pressure",
        aliases=("blood pressure", "systolic", "diastolic", "bp"),
        composite=True,
    ),
    VitalConcept(
        key="heart_rate",
        display="Heart rate",
        aliases=("heart rate", "pulse", "pulse rate"),
    ),
    VitalConcept(
        key="respiratory_rate",
        display="Respiratory rate",
        aliases=("respiratory rate", "breathing rate", "resp rate"),
    ),
    VitalConcept(
        key="body_temperature",
        display="Body temperature",
        aliases=("body temperature", "temperature"),
    ),
    VitalConcept(
        key="oxygen_saturation",
        display="Oxygen saturation",
        aliases=("oxygen saturation", "spo2", "o2 saturation", "pulse oximetry"),
    ),
    VitalConcept(
        key="body_weight",
        display="Body weight",
        aliases=("body weight", "weight"),
    ),
    VitalConcept(
        key="body_height",
        display="Body height",
        aliases=("body height", "height"),
    ),
    VitalConcept(
        key="body_mass_index",
        display="Body mass index",
        aliases=("body mass index", "bmi"),
    ),
)


def _normalize(text: str) -> str:
    """Lowercase and collapse non-alphanumerics to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def classify_vital(test_name: str) -> VitalConcept | None:
    """Return the matching ``VitalConcept`` for a lab test name, or ``None``.

    Deterministic and side-effect free so it can be golden-tested. Multi-word
    aliases match as a normalized substring; single-word aliases must match a
    whole token.
    """
    normalized = _normalize(test_name)
    if not normalized:
        return None
    tokens = set(normalized.split())
    for concept in _VITALS:
        for alias in concept.aliases:
            if " " in alias:
                if alias in normalized:
                    return concept
            elif alias in tokens:
                return concept
    return None


__all__ = ["VITAL_REGISTRY_VERSION", "VitalConcept", "classify_vital"]
