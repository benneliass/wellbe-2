"""Results and Documents read models over the caller's own C2 captures + C4 facts.

Results group ``lab_result`` / ``vital_sign`` facts by analyte (the
``kind:concept`` prefix of the C4 normalized key), keep every reading for a
trend, and attach the Health Threads the analyte's C6 node already belongs to.

The only interpretation applied is a *literal* comparison of a single numeric
value (or a ``systolic/diastolic`` pair) against the reference range exactly as
the source printed it. Anything that cannot be compared literally is
``not_compared``. There is no normality verdict and no diagnostic copy; a
source-provided flag stays source metadata and is not surfaced here.

Documents list uploaded PDFs/photos with a plain-words processing state. There
is no persisted per-document processing status yet, so the state is derived:

- any extracted fact for the capture  -> ``processed``
- none yet, added within the grace window -> ``waiting``
- none after the grace window -> ``could_not_read`` (e.g. image-only documents
  while OCR is not deployed). The original stays stored in the Vault.

The free-text extractor always emits at least a fallback fact for any readable
text, so "no facts after the window" reliably means "no readable text".
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c2_vault.models import RawContextEventRow
from wellbe_c4_processing.models import ExtractedFactRow
from wellbe_c6_graph.models import KgNodeRow
from wellbe_c7_thread.models import HealthThreadRow
from wellbe_contracts.records import (
    AnalyteResultV2,
    DocumentsResponseV2,
    DocumentStatus,
    DocumentV2,
    ExtractedCountV2,
    ObservationV2,
    RangePosition,
    RecordSourceV2,
    ResultsResponseV2,
    ThreadRefV2,
)

RESULT_FACT_TYPES = ("lab_result", "vital_sign")
DOCUMENT_SOURCE_TYPES = ("pdf", "photo")
PROCESSING_GRACE = timedelta(minutes=30)
_MAX_FACTS = 1000
_MAX_DOCUMENTS = 200

_NUM = r"(\d+(?:\.\d+)?)"
_SINGLE_VALUE_RE = re.compile(rf"^{_NUM}$")
_PAIR_VALUE_RE = re.compile(rf"^{_NUM}\s*/\s*{_NUM}$")
_BETWEEN_RE = re.compile(rf"^{_NUM}\s*(?:-|–|—|to)\s*{_NUM}$", re.I)
_BOUND_RE = re.compile(rf"^(<=|>=|≤|≥|<|>)\s*{_NUM}$")
_PAIR_BOUND_RE = re.compile(rf"^(<=|>=|≤|≥|<|>)\s*{_NUM}\s*/\s*{_NUM}$")

_RANGE_NOTES = {
    RangePosition.WITHIN: "Within the reference range shown on the report",
    RangePosition.OUTSIDE: "Outside the reference range shown on the report",
}

_FACT_LABELS: dict[str, tuple[str, str]] = {
    "lab_result": ("lab result", "lab results"),
    "vital_sign": ("vital sign", "vital signs"),
    "symptom": ("symptom", "symptoms"),
    "medication": ("medication", "medications"),
    "procedure": ("procedure", "procedures"),
    "allergy": ("allergy", "allergies"),
    "immunization": ("immunization", "immunizations"),
    "family_history": ("family history note", "family history notes"),
    "social_history": ("everyday-life note", "everyday-life notes"),
    "finding": ("finding mentioned", "findings mentioned"),
    "dx_mention": ("condition mentioned", "conditions mentioned"),
    "other": ("other note", "other notes"),
}


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _within(op: str, value: float, bound: float) -> bool:
    if op == "<":
        return value < bound
    if op in ("<=", "≤"):
        return value <= bound
    if op == ">":
        return value > bound
    return value >= bound


def compare_to_range(value: str | None, reference_range: str | None) -> RangePosition:
    """Literal comparison of a value against the range printed with it."""
    v = (value or "").strip()
    r = (reference_range or "").strip()
    if not v or not r:
        return RangePosition.NOT_COMPARED

    single = _SINGLE_VALUE_RE.match(v)
    if single:
        x = float(single.group(1))
        between = _BETWEEN_RE.match(r)
        if between:
            low, high = float(between.group(1)), float(between.group(2))
            if low > high:
                return RangePosition.NOT_COMPARED
            return RangePosition.WITHIN if low <= x <= high else RangePosition.OUTSIDE
        bound = _BOUND_RE.match(r)
        if bound:
            ok = _within(bound.group(1), x, float(bound.group(2)))
            return RangePosition.WITHIN if ok else RangePosition.OUTSIDE
        return RangePosition.NOT_COMPARED

    pair = _PAIR_VALUE_RE.match(v)
    pair_bound = _PAIR_BOUND_RE.match(r)
    if pair and pair_bound:
        op = pair_bound.group(1)
        ok = _within(op, float(pair.group(1)), float(pair_bound.group(2))) and _within(
            op, float(pair.group(2)), float(pair_bound.group(3))
        )
        return RangePosition.WITHIN if ok else RangePosition.OUTSIDE
    return RangePosition.NOT_COMPARED


def range_note(position: RangePosition, reference_range: str | None) -> str:
    if position in _RANGE_NOTES:
        return _RANGE_NOTES[position]
    if reference_range:
        return "Shown with a reference range that can't be compared directly"
    return "No reference range was given with this result"


def _numeric(value: str) -> float | None:
    m = _SINGLE_VALUE_RE.match(value.strip())
    return float(m.group(1)) if m else None


def analyte_key(fact_type: str, normalized_key: str, label: str) -> str:
    parts = (normalized_key or "").split(":")
    if len(parts) >= 2 and parts[0] in ("lab", "vital") and parts[1]:
        return f"{parts[0]}:{parts[1]}"
    kind = "vital" if fact_type == "vital_sign" else "lab"
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "unnamed"
    return f"{kind}:{slug}"


def source_for(event: Any) -> RecordSourceV2:
    """Plain-language source for a raw capture (never shows an id)."""
    meta: Mapping[str, Any] = event.source_metadata or {}
    source_type = str(event.source_type)
    capture_id = str(event.id)
    origin = str(meta.get("source") or "").strip()
    if source_type == "pdf" or meta.get("capture_type") == "document":
        is_photo = str(event.mime_type or "").startswith("image/")
        label = "From a photo you added" if is_photo else "From a PDF you added"
        return RecordSourceV2(
            kind="document",
            display_label=f"{label} · {origin}" if origin else label,
            capture_id=capture_id,
            document_id=capture_id,
            review_marker="not-clinician-reviewed",
        )
    if source_type == "photo":
        label = "From a photo you added"
        return RecordSourceV2(
            kind="photo",
            display_label=f"{label} · {origin}" if origin else label,
            capture_id=capture_id,
            document_id=capture_id,
            review_marker="not-clinician-reviewed",
        )
    if source_type in ("fhir", "device"):
        return RecordSourceV2(
            kind="connected_source",
            display_label=origin or "From a connected source",
            capture_id=capture_id,
            review_marker="not-clinician-reviewed",
        )
    return RecordSourceV2(
        kind="entered_by_you",
        display_label=f"Entered by you · {origin}" if origin else "Entered by you",
        capture_id=capture_id,
        review_marker="patient-entered",
    )


def _meta_thread_id(event: Any) -> uuid.UUID | None:
    raw = (event.source_metadata or {}).get("thread_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def build_results(
    *,
    facts: Iterable[Any],
    events: Mapping[uuid.UUID, Any],
    node_threads: Mapping[str, Iterable[uuid.UUID]],
    thread_titles: Mapping[uuid.UUID, str],
) -> ResultsResponseV2:
    """Pure transform: facts + their captures + thread links -> grouped results."""
    groups: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    for fact in facts:
        event = events.get(fact.raw_context_event_id)
        if event is None:
            continue
        key = analyte_key(fact.fact_type, fact.normalized_key, fact.entity_label)
        groups[key].append((fact, event))

    analytes: list[AnalyteResultV2] = []
    for key, rows in groups.items():
        rows.sort(key=lambda fe: _as_utc(fe[0].captured_at))
        history: list[ObservationV2] = []
        thread_ids: list[uuid.UUID] = []
        for fact, event in rows:
            qm: Mapping[str, Any] = fact.quality_metadata or {}
            value = str(qm.get("raw_value") or "").strip()
            if not value:
                continue
            reference = (str(qm.get("reference_range") or "").strip()) or None
            position = compare_to_range(value, reference)
            history.append(
                ObservationV2(
                    value=value,
                    unit=(str(qm.get("raw_unit") or "").strip()) or None,
                    numeric_value=_numeric(value),
                    reference_range=reference,
                    range_position=position,
                    range_note=range_note(position, reference),
                    observed_at=_as_utc(fact.captured_at),
                    source=source_for(event),
                )
            )
            candidates = list(node_threads.get(fact.normalized_key, ()))
            meta_tid = _meta_thread_id(event)
            if meta_tid is not None:
                candidates.append(meta_tid)
            for tid in candidates:
                if tid in thread_titles and tid not in thread_ids:
                    thread_ids.append(tid)
        if not history:
            continue
        latest_fact = rows[-1][0]
        label = str(
            (latest_fact.quality_metadata or {}).get("raw_test_name") or latest_fact.entity_label
        )
        analytes.append(
            AnalyteResultV2(
                analyte_key=key,
                display_label=label,
                kind=key.split(":", 1)[0],
                latest=history[-1],
                history=history,
                threads=[ThreadRefV2(thread_id=str(t), title=thread_titles[t]) for t in thread_ids],
            )
        )

    analytes.sort(key=lambda a: a.latest.observed_at, reverse=True)
    if analytes:
        n = len(analytes)
        headline = f"{n} kind{'s' if n != 1 else ''} of result in your records"
        note = (
            "Values and reference ranges are shown exactly as your sources gave "
            "them. Being outside a printed range is not a diagnosis — it's "
            "something you can ask about."
        )
    else:
        headline = "No results yet"
        note = (
            "When you add a lab or test result — typed in or from a document — it "
            "will appear here with its date, reference range, and source."
        )
    return ResultsResponseV2(headline=headline, analytes=analytes, note=note)


def _type_label(mime_type: str) -> str:
    if mime_type == "application/pdf":
        return "PDF"
    if mime_type.startswith("image/"):
        return "Photo"
    return "Document"


def _count_label(kind: str, count: int) -> str:
    singular, plural = _FACT_LABELS.get(kind, ("item", "items"))
    return singular if count == 1 else plural


def document_status(
    *, added_at: datetime, extracted_total: int, now: datetime
) -> tuple[DocumentStatus, str, str]:
    if extracted_total > 0:
        noun = "thing" if extracted_total == 1 else "things"
        return (
            DocumentStatus.PROCESSED,
            "Processed",
            f"WellBe read this and found {extracted_total} {noun} to keep.",
        )
    if now - _as_utc(added_at) < PROCESSING_GRACE:
        return (
            DocumentStatus.WAITING,
            "Waiting to be read",
            "WellBe hasn't finished reading this yet. It usually takes a few minutes.",
        )
    return (
        DocumentStatus.COULD_NOT_READ,
        "Could not be read",
        "WellBe couldn't find readable text in this document. The original is "
        "still safely stored, and you can type in anything important.",
    )


def build_documents(
    *,
    events: Iterable[Any],
    fact_counts: Mapping[uuid.UUID, Mapping[str, int]],
    now: datetime | None = None,
) -> DocumentsResponseV2:
    """Pure transform: document captures + per-capture fact counts -> documents."""
    now = now or datetime.now(UTC)
    documents: list[DocumentV2] = []
    for event in events:
        counts = fact_counts.get(event.id, {})
        total = sum(counts.values())
        mime = str(event.mime_type or "")
        type_label = _type_label(mime)
        origin = str((event.source_metadata or {}).get("source") or "").strip()
        base = "PDF document" if type_label == "PDF" else f"{type_label} of a document"
        if type_label == "Document":
            base = "Document"
        status, status_label, status_detail = document_status(
            added_at=event.captured_at, extracted_total=total, now=now
        )
        documents.append(
            DocumentV2(
                document_id=str(event.id),
                display_label=f"{base} from {origin}" if origin else base,
                type_label=type_label,
                mime_type=mime,
                added_at=_as_utc(event.captured_at),
                status=status,
                status_label=status_label,
                status_detail=status_detail,
                extracted_total=total,
                extracted=[
                    ExtractedCountV2(kind=k, label=_count_label(k, c), count=c)
                    for k, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
                ],
                result_count=sum(counts.get(k, 0) for k in RESULT_FACT_TYPES),
            )
        )
    documents.sort(key=lambda d: d.added_at, reverse=True)
    if documents:
        n = len(documents)
        headline = f"{n} document{'s' if n != 1 else ''} you've added"
        note = (
            "Originals are stored unchanged. What WellBe extracts is kept "
            "separately so you can check it against the source."
        )
    else:
        headline = "No documents yet"
        note = (
            "Add a lab report, letter, or discharge summary and WellBe will read "
            "it, keep the original, and show what it found."
        )
    return DocumentsResponseV2(headline=headline, documents=documents, note=note)


@dataclass
class _ResultRows:
    facts: list[ExtractedFactRow]
    events: dict[uuid.UUID, RawContextEventRow]
    node_threads: dict[str, list[uuid.UUID]]
    thread_titles: dict[uuid.UUID, str]


async def _load_result_rows(session: AsyncSession, patient_id: uuid.UUID) -> _ResultRows:
    facts = list(
        (
            await session.execute(
                select(ExtractedFactRow)
                .where(
                    ExtractedFactRow.patient_id == patient_id,
                    ExtractedFactRow.fact_type.in_(RESULT_FACT_TYPES),
                    ExtractedFactRow.is_negated.is_(False),
                    ExtractedFactRow.is_hypothetical.is_(False),
                    ExtractedFactRow.subject == "patient",
                )
                .order_by(ExtractedFactRow.captured_at.desc())
                .limit(_MAX_FACTS)
            )
        )
        .scalars()
        .all()
    )
    event_ids = {f.raw_context_event_id for f in facts}
    events: dict[uuid.UUID, RawContextEventRow] = {}
    if event_ids:
        rows = await session.execute(
            select(RawContextEventRow).where(
                RawContextEventRow.patient_id == patient_id,
                RawContextEventRow.id.in_(event_ids),
            )
        )
        events = {e.id: e for e in rows.scalars().all()}

    keys = {f.normalized_key for f in facts}
    node_threads: dict[str, list[uuid.UUID]] = {}
    if keys:
        rows = await session.execute(
            select(KgNodeRow.normalized_key, KgNodeRow.thread_ids).where(
                KgNodeRow.patient_id == patient_id,
                KgNodeRow.normalized_key.in_(keys),
            )
        )
        node_threads = {k: list(t or []) for k, t in rows.all()}

    rows = await session.execute(
        select(HealthThreadRow.id, HealthThreadRow.title).where(
            HealthThreadRow.patient_id == patient_id
        )
    )
    thread_titles = {tid: title for tid, title in rows.all()}
    return _ResultRows(facts, events, node_threads, thread_titles)


async def load_results(*, session: AsyncSession, patient_id: uuid.UUID) -> ResultsResponseV2:
    rows = await _load_result_rows(session, patient_id)
    return build_results(
        facts=rows.facts,
        events=rows.events,
        node_threads=rows.node_threads,
        thread_titles=rows.thread_titles,
    )


async def load_documents(*, session: AsyncSession, patient_id: uuid.UUID) -> DocumentsResponseV2:
    events = list(
        (
            await session.execute(
                select(RawContextEventRow)
                .where(
                    RawContextEventRow.patient_id == patient_id,
                    RawContextEventRow.duplicate_of_event_id.is_(None),
                    or_(
                        RawContextEventRow.source_type.in_(DOCUMENT_SOURCE_TYPES),
                        RawContextEventRow.source_metadata["capture_type"].astext == "document",
                    ),
                )
                .order_by(RawContextEventRow.captured_at.desc())
                .limit(_MAX_DOCUMENTS)
            )
        )
        .scalars()
        .all()
    )
    fact_counts: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
    if events:
        rows = await session.execute(
            select(
                ExtractedFactRow.raw_context_event_id,
                ExtractedFactRow.fact_type,
                func.count(),
            )
            .where(
                ExtractedFactRow.patient_id == patient_id,
                ExtractedFactRow.raw_context_event_id.in_([e.id for e in events]),
            )
            .group_by(ExtractedFactRow.raw_context_event_id, ExtractedFactRow.fact_type)
        )
        for event_id, fact_type, count in rows.all():
            fact_counts[event_id][fact_type] = int(count)
    return build_documents(events=events, fact_counts=fact_counts)
