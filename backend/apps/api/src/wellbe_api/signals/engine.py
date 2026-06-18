"""Coverage-aware, never-alarm Home signals summary — WEL-91.

Replaces the hard-coded mock "Your signals look steady · 6 of 6 systems in
range" with a *live, honest* summary derived from the user's own C6 graph
nodes (which carry ``node_type`` and ``last_seen_at``).

Per docs/decisions/signals-summary-semantics.md (approved):

- **Coverage-first** — report *what current data exists* per area, never a
  global "all clear". The denominator counts only areas with fresh data; the
  total is shown separately so coverage is never conflated with status.
- **Missing/stale = explicit unknown** — an area with no fresh signal-bearing
  data is ``NO_DATA`` ("not enough current data"), never green/in-range.
- **No clinical verdict** — we do NOT assert "in range"/"steady": we have no
  reference ranges here. Per-area status is strictly coverage/recency. This
  asserts **no health claim**; C10 still reviews the copy for never-alarm.
- **Suppress when sparse** — with no fresh data anywhere, the aggregate line is
  suppressed in favour of a calm learning/onboarding state.

The composed copy is gated by C10 (fail-closed) before release.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from wellbe_c6_graph.models import KgNodeRow
from wellbe_c6_graph.repository import GraphRepository
from wellbe_contracts.c10_safety import (
    C10Decision,
    C10SafetyEvaluationRequestV1,
    EngineRiskTier,
    OutputFormat,
    OutputType,
    ProvenanceCompleteness,
    ReviewMarker,
    UrgencyClass,
    UrgencyContext,
    UrgencySource,
    WorkspaceType,
)
from wellbe_contracts.signals import (
    ConfidenceLabel,
    SignalArea,
    SignalsSummaryV2,
    SignalStatus,
)

from wellbe_api.config import ApiSettings

_settings = ApiSettings()
_POLICY_VERSION = "signals-c10-v1"

# Data older than this is "stale" for coverage purposes (deferred: per-signal
# freshness thresholds — see the decision's Implementation notes).
_FRESH_WINDOW = timedelta(days=90)


@dataclass(frozen=True)
class _AreaDef:
    id: str
    label: str
    node_types: tuple[str, ...]
    # Optional label keywords; when set, a node must also match one to contribute.
    keywords: tuple[str, ...] = ()


# Fixed area set from the decision's initial system set. Mapping is conservative
# and explicit; a node may legitimately contribute to more than one area (e.g. a
# lipid panel informs both cardiovascular and metabolic coverage).
_AREAS: tuple[_AreaDef, ...] = (
    _AreaDef("cardiovascular", "Cardiovascular", ("VitalSign", "LabResult"),
             ("blood pressure", "bp", "heart rate", "pulse", "hr",
              "cholesterol", "lipid", "ldl", "hdl")),
    _AreaDef("metabolic", "Metabolic", ("LabResult", "VitalSign"),
             ("glucose", "a1c", "hba1c", "insulin", "triglyceride",
              "cholesterol", "lipid", "weight", "bmi")),
    _AreaDef("sleep", "Sleep", ("VitalSign", "Symptom", "SocialFactor", "Other"),
             ("sleep", "insomnia", "rem", "apnea")),
    _AreaDef("activity", "Activity", ("SocialFactor", "VitalSign", "Other"),
             ("steps", "activity", "exercise", "walk", "workout", "active")),
    _AreaDef("inflammation", "Inflammation", ("LabResult",),
             ("crp", "esr", "wbc", "ferritin", "inflam", "sed rate")),
    _AreaDef("vitals", "Vitals", ("VitalSign",)),
)


@dataclass
class SignalsResult:
    summary: SignalsSummaryV2 | None = None
    areas: list[SignalArea] = field(default_factory=list)


def _matches(area: _AreaDef, node: KgNodeRow) -> bool:
    if node.node_type not in area.node_types:
        return False
    if not area.keywords:
        return True
    label = (node.display_label or "").lower()
    return any(kw in label for kw in area.keywords)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _humanize_age(last: datetime, *, now: datetime) -> str:
    days = max(0, (now - _as_utc(last)).days)
    if days == 0:
        return "Updated today"
    if days == 1:
        return "Updated yesterday"
    if days < 30:
        return f"Updated {days} days ago"
    months = days // 30
    return f"Updated about {months} month{'s' if months > 1 else ''} ago"


def _build_area(area: _AreaDef, nodes: list[KgNodeRow], *, now: datetime) -> SignalArea:
    contributing = [n for n in nodes if _matches(area, n)]
    count = len(contributing)
    if not contributing:
        return SignalArea(
            id=area.id, label=area.label, status=SignalStatus.NO_DATA,
            status_label="Not enough current data",
            confidence=ConfidenceLabel.NONE, confidence_label="No data yet",
            last_updated=None,
            recency_note="Add data here and it'll show up — nothing is assumed.",
            source_count=0,
        )

    last = max(_as_utc(n.last_seen_at) for n in contributing)
    fresh = (now - last) <= _FRESH_WINDOW
    if fresh:
        status = SignalStatus.RECENT
        status_label = "Recent data"
        conf = ConfidenceLabel.GOOD if count >= 2 else ConfidenceLabel.LIMITED
        conf_label = "Based on several recent entries" if count >= 2 else "Based on limited data"
    else:
        status = SignalStatus.STALE
        status_label = "Older data"
        conf = ConfidenceLabel.LIMITED
        conf_label = "Your most recent data here is a while ago"

    return SignalArea(
        id=area.id, label=area.label, status=status, status_label=status_label,
        confidence=conf, confidence_label=conf_label, last_updated=last,
        recency_note=_humanize_age(last, now=now), source_count=count,
    )


def build_summary(nodes: list[KgNodeRow], *, now: datetime | None = None) -> SignalsSummaryV2:
    """Pure transform: a patient's nodes -> coverage-first signals summary."""
    now = now or datetime.now(UTC)
    areas = [_build_area(a, nodes, now=now) for a in _AREAS]
    with_data = sum(1 for a in areas if a.status is SignalStatus.RECENT)
    total = len(areas)

    if with_data == 0:
        return SignalsSummaryV2(
            headline="Still getting to know your health",
            coverage_label=f"No current data yet across {total} areas",
            areas_with_data=0, areas_total=total, areas=areas, suppressed=True,
            note=(
                "As you add results, notes, and connected data, this will show "
                "what's current in your records — never a verdict, just what's "
                "there and how fresh it is."
            ),
        )

    return SignalsSummaryV2(
        headline="Here's what's current in your records",
        coverage_label=f"Recent data for {with_data} of {total} areas",
        areas_with_data=with_data, areas_total=total, areas=areas, suppressed=False,
        note=(
            "This shows which areas have recent data and how fresh it is — not "
            "whether anything is normal or a cause for concern. Areas without "
            "current data simply aren't assessed."
        ),
    )


def _build_eval_request(
    *, summary: SignalsSummaryV2, patient_id: uuid.UUID, correlation_id: str
) -> C10SafetyEvaluationRequestV1:
    parts = [summary.headline, summary.coverage_label]
    parts += [f"{a.label}: {a.status_label}" for a in summary.areas]
    parts.append(summary.note)
    return C10SafetyEvaluationRequestV1(
        request_id=str(uuid.uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key=f"signals:{correlation_id}",
        output_text="\n".join(parts),
        output_format=OutputFormat.STRUCTURED_BLOCKS,
        output_type=OutputType.OTHER,
        target_audience="patient",
        surface="home_signals",
        review_markers=[
            ReviewMarker.AI_SUMMARIZED,
            ReviewMarker.NOT_CLINICIAN_REVIEWED,
        ],
        urgency=UrgencyContext(
            urgency_class=UrgencyClass.NONE, urgency_source=UrgencySource.NONE
        ),
        # Coverage statements only — no in-range/diagnostic health claim asserted.
        claim_map=[],
        claim_map_complete=True,
        no_health_claims_asserted=True,
        engine_name="signals_engine",
        engine_version="1.0",
        engine_risk_tier=EngineRiskTier.HIGH,
        upstream_run_id=correlation_id,
        actor_id=str(patient_id),
        workspace_id=str(patient_id),
        workspace_type=WorkspaceType.INDIVIDUAL,
        active_role_type="controller",
        purpose_code="home_signals",
        access_decision_id="self",
        access_predicate_hash="self",
        c10_policy_version=_POLICY_VERSION,
        deterministic_ruleset_version=_POLICY_VERSION,
        nemo_guardrails_config_id=_POLICY_VERSION,
        llama_guard_policy_version=_POLICY_VERSION,
        risk_tier_policy_version=_POLICY_VERSION,
        correlation_id=correlation_id,
        patient_id=str(patient_id),
        provenance_completeness=ProvenanceCompleteness.NOT_APPLICABLE_NO_HEALTH_CLAIMS,
    )


def gate_summary(
    *, summary: SignalsSummaryV2, patient_id: uuid.UUID, correlation_id: str
) -> C10Decision:
    """Run the composed signals copy through C10 (fail-closed)."""
    from wellbe_c10_safety import SafetyGateEvaluator

    evaluator = SafetyGateEvaluator(
        token_secret=_settings.c10_token_secret.get_secret_value()
    )
    request = _build_eval_request(
        summary=summary, patient_id=patient_id, correlation_id=correlation_id
    )
    return evaluator.evaluate(request).decision


# Node types that can bear a signal we summarise. (Excludes hypotheses, family
# history, allergies, immunizations, investigations, theories.)
_SIGNAL_NODE_TYPES = ["VitalSign", "LabResult", "Symptom", "SocialFactor", "Other"]


async def summarize_signals(
    *, session, patient_id: uuid.UUID, correlation_id: str
) -> SignalsResult:
    """Full pipeline: read patient nodes -> coverage summary -> C10 gate."""
    repo = GraphRepository(session)
    nodes = await repo.nodes_for_patient(
        patient_id=patient_id, node_types=_SIGNAL_NODE_TYPES
    )
    summary = build_summary(nodes)

    decision = gate_summary(
        summary=summary, patient_id=patient_id, correlation_id=correlation_id
    )
    if decision not in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}:
        # Fail closed: show the calm learning state, never ungated copy.
        safe = SignalsSummaryV2(
            headline="Still getting to know your health",
            coverage_label="Your signals view is warming up",
            areas_with_data=0, areas_total=len(_AREAS), areas=[], suppressed=True,
            note=(
                "We'll show what's current in your records here soon. If you "
                "have a health concern, please reach out to a clinician."
            ),
        )
        return SignalsResult(summary=safe, areas=[])

    return SignalsResult(summary=summary, areas=summary.areas)
