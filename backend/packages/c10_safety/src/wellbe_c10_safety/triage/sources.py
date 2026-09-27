"""Public sources the triage red-flag rules are linked to.

Every source here is cited in the approved decision record
``docs/decisions/triage-escalation-safety-rules.md`` (research + re-run research).
"""

from __future__ import annotations

from wellbe_contracts.triage import TriageSourceV2

_SOURCES = (
    TriageSourceV2(
        source_id="cdc-stroke-signs",
        publisher="CDC",
        title="Signs and Symptoms of Stroke",
        url="https://www.cdc.gov/stroke/signs-symptoms/index.html",
    ),
    TriageSourceV2(
        source_id="aha-warning-signs",
        publisher="American Heart Association",
        title="Heart Attack and Stroke Symptoms",
        url="https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms",
    ),
    TriageSourceV2(
        source_id="medlineplus-emergencies",
        publisher="MedlinePlus (U.S. National Library of Medicine)",
        title="Recognizing medical emergencies",
        url="https://medlineplus.gov/ency/article/001927.htm",
    ),
    TriageSourceV2(
        source_id="mayo-shortness-of-breath",
        publisher="Mayo Clinic",
        title="Shortness of breath: When to see a doctor",
        url=(
            "https://www.mayoclinic.org/symptoms/shortness-of-breath/basics/"
            "when-to-see-doctor/sym-20050890"
        ),
    ),
    TriageSourceV2(
        source_id="mayo-anaphylaxis",
        publisher="Mayo Clinic",
        title="Anaphylaxis: Symptoms and causes",
        url=(
            "https://www.mayoclinic.org/diseases-conditions/anaphylaxis/"
            "symptoms-causes/syc-20351468"
        ),
    ),
    TriageSourceV2(
        source_id="cdc-flu-warning-signs",
        publisher="CDC",
        title="Signs and Symptoms of Flu (emergency warning signs)",
        url="https://www.cdc.gov/flu/signs-symptoms/index.html",
    ),
    TriageSourceV2(
        source_id="cdc-hear-her",
        publisher="CDC",
        title="Urgent Maternal Warning Signs (HEAR HER)",
        url="https://www.cdc.gov/hearher/maternal-warning-signs/index.html",
    ),
    TriageSourceV2(
        source_id="nimh-suicide-warning-signs",
        publisher="NIMH",
        title="Warning Signs of Suicide",
        url="https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide",
    ),
    TriageSourceV2(
        source_id="samhsa-in-crisis",
        publisher="SAMHSA",
        title="Find Support: In Crisis",
        url="https://www.samhsa.gov/find-support/in-crisis",
    ),
    TriageSourceV2(
        source_id="nhs-when-to-call-999",
        publisher="NHS",
        title="When to call 999",
        url=(
            "https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/"
        ),
    ),
    TriageSourceV2(
        source_id="nhs-serious-illness-children",
        publisher="NHS",
        title="Is your baby or toddler seriously ill?",
        url="https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/",
    ),
    TriageSourceV2(
        source_id="nice-ng143-traffic-light",
        publisher="NICE",
        title="Fever in under 5s (NG143) traffic-light table",
        url="https://www.nice.org.uk/guidance/NG143",
    ),
)

SOURCES: dict[str, TriageSourceV2] = {s.source_id: s for s in _SOURCES}

# Shown with the routine route: the "not all-inclusive" safety-net pattern.
ROUTINE_SOURCE_IDS: tuple[str, ...] = ("medlineplus-emergencies", "cdc-flu-warning-signs")
