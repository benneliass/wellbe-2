"""Ask WellBe answer engine — v1 closed-corpus, deterministic, non-diagnostic.

Per docs/decisions/ask-answer-engine-semantics.md:

- **Grounding** is a closed personal corpus only: the user's own C7 threads and
  C9 pending items. No general or model latent medical knowledge. The engine
  never free-text generates a claim; it summarises retrieved structured data,
  so every user-specific claim is source-linked (no orphan claims).
- **Intent pre-classification** routes urgent input to a calm escalation and
  diagnosis/treatment/management/medication requests to an out-of-scope
  clinician redirect — these are never answered.
- **Output validation** runs the composed answer through the C10 gate before
  release (fail-closed). Retrieved text is treated as evidence, never
  instructions.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_contracts.ask import AskCitation, AskMode
from wellbe_contracts.c10_safety import (
    C10Decision,
    C10SafetyEvaluationRequestV1,
    ClaimMapEntry,
    ClaimType,
    EngineRiskTier,
    EvidenceRef,
    EvidenceRefType,
    OutputFormat,
    OutputType,
    ProvenanceCompleteness,
    ReviewMarker,
    SourceType,
    UrgencyClass,
    UrgencyContext,
    UrgencySource,
    WorkspaceType,
)

from wellbe_api.config import ApiSettings

_settings = ApiSettings()
_POLICY_VERSION = "ask-c10-v1"
_CLOSED_STATUSES = {"closed", "archived"}
_RESOLVED_PENDING = {"resolved", "cancelled", "superseded"}

# Conservative red-flag patterns -> calm, specific escalation (never-alarm).
# Erring toward escalation is intentional for emergency-class input.
_URGENT_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bchest pain\b",
        r"\bpressure in (my )?chest\b",
        r"\b(can'?t|cannot|trouble|difficulty) breath",
        r"\bshort(ness)? of breath\b",
        r"\bheart attack\b",
        r"\bstroke\b",
        r"\bface (is )?droop",
        r"\bslurred speech\b",
        r"\bnumb(ness)? on one side\b",
        r"\bsevere bleeding\b",
        r"\bunconscious\b",
        r"\boverdose\b",
        r"\banaphylax",
        r"\bsuicid",
        r"\bkill myself\b",
        r"\bend my life\b",
        r"\b(harm|hurt) myself\b",
        r"\bself[- ]harm\b",
    )
]

# Diagnosis / treatment / management / medication intent -> out of scope.
_OUT_OF_SCOPE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bdo i have\b",
        r"\bwhat'?s wrong with me\b",
        r"\bdiagnos",
        r"\bwhat (condition|disease|illness)\b",
        r"\bis it (cancer|serious|dangerous)\b",
        r"\bshould i (take|stop|start)\b",
        r"\bwhat (medication|drug|dose|dosage)\b",
        r"\bhow (much|many) .*(should i take|mg)\b",
        r"\b(treat|treatment|cure|prescrib)",
        r"\bwhat should i do about\b",
    )
]

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "my", "me", "i", "do", "does", "did", "what", "why", "how", "when", "where",
    "about", "with", "have", "has", "had", "any", "show", "tell", "whats",
    "this", "that", "it", "im", "you", "your", "be", "was", "were", "get",
    "got", "going", "happening", "health", "status", "update", "summary",
}

_SUMMARY_INTENT = re.compile(
    r"\b(summary|overview|going on|status|open|pending|follow[- ]?up|"
    r"outstanding|whats new|update|recap|review|everything)\b",
    re.IGNORECASE,
)


@dataclass
class AnswerStatement:
    text: str
    citation: AskCitation | None  # None for meta/disclaimer lines


@dataclass
class AskResult:
    mode: AskMode
    statements: list[AnswerStatement] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def classify_intent(question: str) -> AskMode | None:
    """Return URGENT or OUT_OF_SCOPE_REDIRECT if the input matches; else None."""
    if any(p.search(question) for p in _URGENT_PATTERNS):
        return AskMode.URGENT
    if any(p.search(question) for p in _OUT_OF_SCOPE_PATTERNS):
        return AskMode.OUT_OF_SCOPE_REDIRECT
    return None


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


async def _retrieve(session, patient_id: uuid.UUID, question: str):
    """Closed-corpus retrieval over the user's own threads + pending items."""
    q_tokens = _tokens(question)
    summary_intent = bool(_SUMMARY_INTENT.search(question))

    thread_repo = ThreadRepository(session)
    continuity_repo = ContinuityRepository(session)

    threads = [
        t
        for t in await thread_repo.list_for_patient(patient_id)
        if t.status not in _CLOSED_STATUSES
    ]

    scored: list[tuple[int, object]] = []
    for t in threads:
        overlap = len(q_tokens & _tokens(t.title))
        if overlap > 0 or summary_intent:
            scored.append((overlap, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    matched_threads = [t for _, t in scored[:6]]

    pendings_by_thread: dict[uuid.UUID, list] = {}
    for t in matched_threads:
        items = await continuity_repo.items_for_thread(
            patient_id=patient_id, thread_id=t.id
        )
        pendings_by_thread[t.id] = [
            p for p in items if p.status not in _RESOLVED_PENDING
        ]
    return matched_threads, pendings_by_thread


def _urgent_result() -> AskResult:
    return AskResult(
        mode=AskMode.URGENT,
        statements=[
            AnswerStatement(
                text=(
                    "What you described can be a sign of something urgent. "
                    "I can't assess it for you — please get medical help now."
                ),
                citation=None,
            ),
            AnswerStatement(
                text=(
                    "If this is or might be an emergency, call your local "
                    "emergency number (for example 911 in the US, 999 in the "
                    "UK, 112 in the EU) or go to the nearest emergency room."
                ),
                citation=None,
            ),
        ],
        next_steps=[
            "Call your local emergency number now if symptoms are severe or worsening.",
            "If you are thinking about harming yourself, contact a crisis line "
            "(e.g. 988 in the US) — you don't have to handle this alone.",
        ],
    )


def _redirect_result() -> AskResult:
    return AskResult(
        mode=AskMode.OUT_OF_SCOPE_REDIRECT,
        statements=[
            AnswerStatement(
                text=(
                    "I can't diagnose, interpret, or advise on treatment or "
                    "medication — that's for a licensed clinician who can "
                    "examine you and see your full picture."
                ),
                citation=None,
            ),
            AnswerStatement(
                text=(
                    "What I can do is help you organise your own records and "
                    "prepare for that conversation."
                ),
                citation=None,
            ),
        ],
        next_steps=[
            "Use Prepare for a visit to build a source-linked packet for your clinician.",
            "Ask me to summarise what's open or recent in your own records.",
        ],
    )


def _no_sources_result() -> AskResult:
    return AskResult(
        mode=AskMode.NO_SOURCES,
        statements=[
            AnswerStatement(
                text=(
                    "I couldn't find anything in your own records that answers "
                    "that. I only answer from what you've logged — I don't draw "
                    "on outside medical knowledge."
                ),
                citation=None,
            )
        ],
        next_steps=[
            "Log a symptom, result, or note so I have something to work from.",
            "Try rephrasing using words from your own records.",
        ],
    )


def compose_answer(question, matched_threads, pendings_by_thread) -> AskResult:
    """Deterministically summarise retrieved evidence; every claim is sourced."""
    if not matched_threads:
        return _no_sources_result()

    statements: list[AnswerStatement] = [
        AnswerStatement(
            text="Here's what's in your own records related to that:",
            citation=None,
        )
    ]
    for t in matched_threads:
        status = str(t.status).replace("_", " ")
        statements.append(
            AnswerStatement(
                text=f"{t.title} — current status: {status}.",
                citation=AskCitation(
                    ref_type="health_thread", source_id=str(t.id), label=t.title
                ),
            )
        )
        for p in pendings_by_thread.get(t.id, []):
            p_status = str(p.status).replace("_", " ")
            statements.append(
                AnswerStatement(
                    text=f"  • Open item: {p.title} (status: {p_status}).",
                    citation=AskCitation(
                        ref_type="pending_item",
                        source_id=str(p.pending_item_id),
                        label=p.title,
                    ),
                )
            )
    statements.append(
        AnswerStatement(
            text=(
                "A recap of your own records — not medical advice, and not a "
                "diagnosis."
            ),
            citation=None,
        )
    )
    return AskResult(
        mode=AskMode.ANSWERED,
        statements=statements,
        next_steps=[
            "Open a thread to see its full timeline and evidence.",
            "Prepare a visit packet if you want to bring this to a clinician.",
        ],
    )


def _build_eval_request(
    *, result: AskResult, patient_id: uuid.UUID, question: str, correlation_id: str
) -> C10SafetyEvaluationRequestV1:
    parts: list[str] = []
    claim_map: list[ClaimMapEntry] = []
    cursor = 0
    for idx, st in enumerate(result.statements):
        start = cursor
        end = start + len(st.text)
        cursor = end + 1
        if st.citation is None:
            claim_type = ClaimType.META_OR_DISCLAIMER
            evidence_refs: list[EvidenceRef] = []
            personal = False
        else:
            claim_type = ClaimType.PERSONAL_FACT
            evidence_refs = [
                EvidenceRef(
                    evidence_ref_id=f"ask:{idx}",
                    ref_type=EvidenceRefType.EXTRACTED_FACT,
                    source_type=SourceType.PATIENT_ENTERED_NOTE,
                    source_id=st.citation.source_id,
                )
            ]
            personal = True
        claim_map.append(
            ClaimMapEntry(
                claim_id=f"ask:{idx}",
                char_start=start,
                char_end=end,
                claim_type=claim_type,
                personal_specific=personal,
                external_context_only=False,
                evidence_refs=evidence_refs,
                provenance_complete=True,
                uncertainty_label="source_summary",
            )
        )
        parts.append(st.text)

    has_claims = any(c.claim_type != ClaimType.META_OR_DISCLAIMER for c in claim_map)
    return C10SafetyEvaluationRequestV1(
        request_id=str(uuid.uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key=f"ask:{correlation_id}",
        output_text="\n".join(parts),
        output_format=OutputFormat.STRUCTURED_BLOCKS,
        output_type=OutputType.THREAD_SUMMARY,
        target_audience="patient",
        surface="ask_wellbe",
        review_markers=[ReviewMarker.PATIENT_ENTERED],
        urgency=UrgencyContext(
            urgency_class=UrgencyClass.NONE, urgency_source=UrgencySource.NONE
        ),
        claim_map=claim_map,
        claim_map_complete=True,
        no_health_claims_asserted=not has_claims,
        engine_name="ask_wellbe_engine",
        engine_version="1.0",
        engine_risk_tier=EngineRiskTier.MEDIUM,
        upstream_run_id=correlation_id,
        actor_id=str(patient_id),
        workspace_id=str(patient_id),
        workspace_type=WorkspaceType.INDIVIDUAL,
        active_role_type="controller",
        purpose_code="ask_wellbe",
        access_decision_id="self",
        access_predicate_hash="self",
        c10_policy_version=_POLICY_VERSION,
        deterministic_ruleset_version=_POLICY_VERSION,
        nemo_guardrails_config_id=_POLICY_VERSION,
        llama_guard_policy_version=_POLICY_VERSION,
        risk_tier_policy_version=_POLICY_VERSION,
        correlation_id=correlation_id,
        patient_id=str(patient_id),
        provenance_completeness=(
            ProvenanceCompleteness.COMPLETE
            if has_claims
            else ProvenanceCompleteness.NOT_APPLICABLE_NO_HEALTH_CLAIMS
        ),
    )


def gate_answer(
    *, result: AskResult, patient_id: uuid.UUID, question: str, correlation_id: str
) -> C10Decision:
    """Run the composed answer through the C10 gate (fail-closed)."""
    from wellbe_c10_safety import SafetyGateEvaluator

    evaluator = SafetyGateEvaluator(
        token_secret=_settings.c10_token_secret.get_secret_value()
    )
    request = _build_eval_request(
        result=result,
        patient_id=patient_id,
        question=question,
        correlation_id=correlation_id,
    )
    return evaluator.evaluate(request).decision


async def answer_question(
    *, session, patient_id: uuid.UUID, question: str, correlation_id: str
) -> AskResult:
    """Full pipeline: intent -> retrieve -> compose -> C10 gate."""
    intent = classify_intent(question)
    if intent is AskMode.URGENT:
        return _urgent_result()
    if intent is AskMode.OUT_OF_SCOPE_REDIRECT:
        return _redirect_result()

    matched_threads, pendings_by_thread = await _retrieve(
        session, patient_id, question
    )
    result = compose_answer(question, matched_threads, pendings_by_thread)

    if result.mode is AskMode.ANSWERED:
        decision = gate_answer(
            result=result,
            patient_id=patient_id,
            question=question,
            correlation_id=correlation_id,
        )
        if decision not in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}:
            return AskResult(
                mode=AskMode.BLOCKED,
                statements=[
                    AnswerStatement(
                        text=(
                            "I couldn't share a safe answer for that from your "
                            "records. If you have a health concern, please reach "
                            "out to a clinician."
                        ),
                        citation=None,
                    )
                ],
                next_steps=[
                    "Prepare a visit packet to bring your records to a clinician."
                ],
            )
    return result
