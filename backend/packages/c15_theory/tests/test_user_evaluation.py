"""User-authored theory evaluation (owner decision 2026-09-27).

The user marks a theory and must cite their own evidence from the
investigation's threads; the system never decides. Covers evidence validation,
optimistic concurrency, idempotent replay, the C6 edge projection, and the
outbox event.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from wellbe_c15_theory.errors import (
    TheoryBlockedError,
    TheoryEvidenceNotFoundError,
    TheoryEvidenceRequiredError,
    TheoryEvidenceUnrelatedError,
    TheoryNotFoundError,
    TheoryNotLinkedError,
    TheoryRationaleRequiredError,
    TheoryVersionConflictError,
)
from wellbe_c15_theory.evidence import EvidenceLinkInfo, FactInfo, resolve_evidence
from wellbe_c15_theory.repository import TheoryRepository
from wellbe_c15_theory.service import TheoryService
from wellbe_contracts.c15_theory import (
    ASSESSMENT_LABEL,
    ASSESSMENT_TO_STATUS,
    THEORY_USER_EVALUATED,
    TheoryAssessment,
    TheoryEvidenceRef,
    TheoryEvidenceRefKind,
    TheoryStatus,
)

PATIENT = uuid.uuid4()
OTHER_PATIENT = uuid.uuid4()
THREAD = uuid.uuid4()
OTHER_THREAD = uuid.uuid4()


class FakeStore:
    """In-memory EvidenceStore: facts/captures/links keyed by owner patient."""

    def __init__(self) -> None:
        self.facts: dict[uuid.UUID, tuple[uuid.UUID, FactInfo]] = {}
        self.captures: dict[uuid.UUID, uuid.UUID] = {}
        self.links: dict[uuid.UUID, tuple[uuid.UUID, EvidenceLinkInfo]] = {}
        # (patient, normalized_key) -> (node_id, thread_ids)
        self.nodes: dict[tuple[uuid.UUID, str], tuple[uuid.UUID, set[uuid.UUID]]] = {}

    def add_capture(self, patient: uuid.UUID) -> uuid.UUID:
        cid = uuid.uuid4()
        self.captures[cid] = patient
        return cid

    def add_fact(
        self, patient: uuid.UUID, key: str, capture: uuid.UUID | None = None
    ) -> FactInfo:
        fact = FactInfo(
            id=uuid.uuid4(),
            normalized_key=key,
            raw_context_event_id=capture or self.add_capture(patient),
        )
        self.facts[fact.id] = (patient, fact)
        return fact

    def add_node(self, patient: uuid.UUID, key: str, threads: set[uuid.UUID]) -> uuid.UUID:
        nid = uuid.uuid4()
        self.nodes[(patient, key)] = (nid, threads)
        return nid

    def add_link(
        self, patient: uuid.UUID, source_type: str, source_id: uuid.UUID, capture: uuid.UUID
    ) -> uuid.UUID:
        lid = uuid.uuid4()
        self.links[lid] = (
            patient,
            EvidenceLinkInfo(
                id=lid, source_type=source_type, source_id=source_id,
                raw_context_event_id=capture,
            ),
        )
        return lid

    async def get_fact(self, patient_id, fact_id):
        owner, fact = self.facts.get(fact_id, (None, None))
        return fact if owner == patient_id else None

    async def capture_exists(self, patient_id, capture_id):
        return self.captures.get(capture_id) == patient_id

    async def get_evidence_link(self, patient_id, link_id):
        owner, link = self.links.get(link_id, (None, None))
        return link if owner == patient_id else None

    async def facts_for_capture(self, patient_id, capture_id):
        return [
            f for owner, f in self.facts.values()
            if owner == patient_id and f.raw_context_event_id == capture_id
        ]

    async def thread_linked_captures(self, patient_id, thread_ids):
        return {
            link.raw_context_event_id
            for owner, link in self.links.values()
            if owner == patient_id
            and link.source_type == "health_thread"
            and link.source_id in thread_ids
        }

    async def thread_nodes_by_key(self, patient_id, keys, thread_ids):
        out = {}
        for key in keys:
            node = self.nodes.get((patient_id, key))
            if node is not None and node[1] & set(thread_ids):
                out[key] = node[0]
        return out


def _ref(kind: TheoryEvidenceRefKind, rid: uuid.UUID) -> TheoryEvidenceRef:
    return TheoryEvidenceRef(kind=kind, id=rid)


# ---------------------------------------------------------------------------
# Evidence resolution
# ---------------------------------------------------------------------------


class TestResolveEvidence:
    @pytest.mark.asyncio
    async def test_no_refs_is_rejected(self):
        with pytest.raises(TheoryEvidenceRequiredError) as exc:
            await resolve_evidence(FakeStore(), patient_id=PATIENT, thread_ids=[THREAD], refs=[])
        assert exc.value.code == "theory_evidence_required"

    @pytest.mark.asyncio
    async def test_no_linked_threads_is_rejected(self):
        store = FakeStore()
        fact = store.add_fact(PATIENT, "symptom:headache")
        with pytest.raises(TheoryNotLinkedError):
            await resolve_evidence(
                store, patient_id=PATIENT, thread_ids=[],
                refs=[_ref(TheoryEvidenceRefKind.FACT, fact.id)],
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", list(TheoryEvidenceRefKind))
    async def test_foreign_patient_ref_is_not_found(self, kind):
        store = FakeStore()
        capture = store.add_capture(OTHER_PATIENT)
        fact = store.add_fact(OTHER_PATIENT, "symptom:headache", capture)
        link = store.add_link(OTHER_PATIENT, "health_thread", THREAD, capture)
        rid = {
            TheoryEvidenceRefKind.FACT: fact.id,
            TheoryEvidenceRefKind.CAPTURE: capture,
            TheoryEvidenceRefKind.EVIDENCE_LINK: link,
        }[kind]
        with pytest.raises(TheoryEvidenceNotFoundError) as exc:
            await resolve_evidence(
                store, patient_id=PATIENT, thread_ids=[THREAD], refs=[_ref(kind, rid)]
            )
        assert exc.value.code == "theory_evidence_not_found"

    @pytest.mark.asyncio
    async def test_own_fact_outside_investigation_threads_is_unrelated(self):
        store = FakeStore()
        fact = store.add_fact(PATIENT, "symptom:knee_pain")
        store.add_node(PATIENT, "symptom:knee_pain", {OTHER_THREAD})
        with pytest.raises(TheoryEvidenceUnrelatedError) as exc:
            await resolve_evidence(
                store, patient_id=PATIENT, thread_ids=[THREAD],
                refs=[_ref(TheoryEvidenceRefKind.FACT, fact.id)],
            )
        assert exc.value.code == "theory_evidence_unrelated"

    @pytest.mark.asyncio
    async def test_fact_resolves_to_its_thread_node(self):
        store = FakeStore()
        fact = store.add_fact(PATIENT, "symptom:headache")
        node = store.add_node(PATIENT, "symptom:headache", {THREAD})
        ref = _ref(TheoryEvidenceRefKind.FACT, fact.id)
        out = await resolve_evidence(store, patient_id=PATIENT, thread_ids=[THREAD], refs=[ref])
        assert out.node_ids == [node]
        assert out.refs_for_node(node) == [ref]

    @pytest.mark.asyncio
    async def test_fact_from_thread_linked_capture_without_node_is_accepted(self):
        store = FakeStore()
        capture = store.add_capture(PATIENT)
        store.add_link(PATIENT, "health_thread", THREAD, capture)
        fact = store.add_fact(PATIENT, "symptom:headache", capture)
        out = await resolve_evidence(
            store, patient_id=PATIENT, thread_ids=[THREAD],
            refs=[_ref(TheoryEvidenceRefKind.FACT, fact.id)],
        )
        assert out.node_ids == []

    @pytest.mark.asyncio
    async def test_capture_and_thread_evidence_link_resolve_to_capture_fact_nodes(self):
        store = FakeStore()
        capture = store.add_capture(PATIENT)
        link = store.add_link(PATIENT, "health_thread", THREAD, capture)
        store.add_fact(PATIENT, "symptom:headache", capture)
        store.add_fact(PATIENT, "symptom:nausea", capture)
        n1 = store.add_node(PATIENT, "symptom:headache", {THREAD})
        n2 = store.add_node(PATIENT, "symptom:nausea", {THREAD})
        out = await resolve_evidence(
            store, patient_id=PATIENT, thread_ids=[THREAD],
            refs=[
                _ref(TheoryEvidenceRefKind.CAPTURE, capture),
                _ref(TheoryEvidenceRefKind.EVIDENCE_LINK, link),
                _ref(TheoryEvidenceRefKind.CAPTURE, capture),  # duplicate collapses
            ],
        )
        assert len(out.refs) == 2
        assert set(out.node_ids) == {n1, n2}

    @pytest.mark.asyncio
    async def test_extracted_fact_evidence_link_uses_the_fact(self):
        store = FakeStore()
        fact = store.add_fact(PATIENT, "symptom:headache")
        node = store.add_node(PATIENT, "symptom:headache", {THREAD})
        link = store.add_link(PATIENT, "extracted_fact", fact.id, fact.raw_context_event_id)
        out = await resolve_evidence(
            store, patient_id=PATIENT, thread_ids=[THREAD],
            refs=[_ref(TheoryEvidenceRefKind.EVIDENCE_LINK, link)],
        )
        assert out.node_ids == [node]

    @pytest.mark.asyncio
    async def test_evidence_link_for_another_thread_is_unrelated(self):
        store = FakeStore()
        capture = store.add_capture(PATIENT)
        link = store.add_link(PATIENT, "health_thread", OTHER_THREAD, capture)
        with pytest.raises(TheoryEvidenceUnrelatedError):
            await resolve_evidence(
                store, patient_id=PATIENT, thread_ids=[THREAD],
                refs=[_ref(TheoryEvidenceRefKind.EVIDENCE_LINK, link)],
            )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def _theory(**over):
    base = dict(
        id=uuid.uuid4(),
        patient_id=PATIENT,
        status="unreviewed",
        safety_level="low",
        version=1,
        projection_node_id=uuid.uuid4(),
        linked_investigation_id=uuid.uuid4(),
        normalized_question="Could my data be related to screen time?",
        theory_text="screen time causes my headaches",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _eval_row(theory, **over):
    base = dict(
        id=uuid.uuid4(), theory_id=theory.id, patient_id=PATIENT,
        evaluator_actor_id=PATIENT, evaluation_version=1, assessment="weakened",
        from_status="unreviewed", proposed_status="not_supported_by_current_data",
        rationale="Headaches continued on screen-free days.",
        evidence_refs=[], evidence_for_node_ids=[], evidence_against_node_ids=[],
        created_at=datetime.now(UTC),
    )
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture
def world():
    store = FakeStore()
    fact = store.add_fact(PATIENT, "symptom:headache")
    node = store.add_node(PATIENT, "symptom:headache", {THREAD})
    theory = _theory()

    svc = TheoryService(AsyncMock(), evidence_store=store)
    svc._repo = AsyncMock(spec=TheoryRepository)
    svc._graph = AsyncMock()
    svc._repo.find_evaluation_by_idempotency.return_value = None
    svc._repo.get.return_value = theory
    svc._repo.next_evaluation_version.return_value = 1
    svc._repo.apply_user_evaluation.return_value = 2

    async def _insert(**kw):
        return _eval_row(
            theory,
            id=kw["evaluation_id"],
            assessment=kw["assessment"],
            from_status=kw["from_status"],
            proposed_status=kw["to_status"],
            rationale=kw["rationale"],
            evidence_refs=kw["evidence_refs"],
            evidence_for_node_ids=kw["evidence_for_node_ids"],
            evidence_against_node_ids=kw["evidence_against_node_ids"],
        )

    svc._repo.insert_user_evaluation.side_effect = _insert
    return SimpleNamespace(svc=svc, store=store, fact=fact, node=node, theory=theory)


async def _evaluate(w, **over):
    kwargs = dict(
        theory_id=w.theory.id,
        patient_id=PATIENT,
        actor_id=PATIENT,
        assessment=TheoryAssessment.WEAKENED,
        rationale="Headaches continued on screen-free days.",
        evidence_refs=[_ref(TheoryEvidenceRefKind.FACT, w.fact.id)],
        expected_version=1,
        investigation_thread_ids=[THREAD],
        idempotency_key="idem-1",
        correlation_id="corr",
        trace_id="trace",
    )
    kwargs.update(over)
    with patch(
        "wellbe_c15_theory.service.emit_event", new=AsyncMock(return_value=uuid.uuid4())
    ) as emit:
        outcome = await w.svc.evaluate_by_user(**kwargs)
    return outcome, emit


class TestEvaluateByUser:
    @pytest.mark.asyncio
    async def test_weakened_records_evaluation_edges_and_event(self, world):
        outcome, emit = await _evaluate(world)

        ev = outcome.evaluation
        assert ev.assessment is TheoryAssessment.WEAKENED
        assert ev.from_status is TheoryStatus.UNREVIEWED
        assert ev.to_status is TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA
        assert outcome.theory_version == 2
        assert not outcome.replayed

        insert = world.svc._repo.insert_user_evaluation.await_args.kwargs
        assert insert["evidence_against_node_ids"] == [world.node]
        assert insert["evidence_for_node_ids"] == []
        assert insert["idempotency_key"] == f"theory-eval:{world.theory.id}:idem-1"
        # safety_level is carried, never lowered by a user mark.
        assert insert["safety_level"] == "low"

        apply = world.svc._repo.apply_user_evaluation.await_args.kwargs
        assert apply["expected_version"] == 1
        assert apply["status"] == "not_supported_by_current_data"

        sync = world.svc._repo.sync_user_evidence_edges.await_args.kwargs
        assert sync["edge_type"] == "evidence_against"
        assert sync["theory_node_id"] == world.theory.projection_node_id
        inputs = sync["score_inputs_by_node"][world.node]
        assert inputs["assessment"] == "weakened"
        assert inputs["source_ref_id"] == str(world.fact.id)
        world.svc._graph.tag_edges_within_thread.assert_awaited_once_with(
            patient_id=PATIENT, thread_id=THREAD
        )
        node_meta = world.svc._repo.update_theory_node.await_args.kwargs["metadata"]
        assert node_meta["theory_status"] == "not_supported_by_current_data"
        assert node_meta["user_assessment"] == "weakened"

        emit.assert_awaited_once()
        call = emit.await_args.kwargs
        assert call["event_type"] == THEORY_USER_EVALUATED == "c15.theory.evaluated.v1"
        payload = call["payload"]
        assert payload["assessment"] == "weakened"
        assert payload["to_status"] == "not_supported_by_current_data"
        assert payload["theory_version"] == 2
        assert payload["evidence_node_ids"] == [str(world.node)]

    @pytest.mark.asyncio
    async def test_supported_projects_evidence_for(self, world):
        await _evaluate(world, assessment=TheoryAssessment.SUPPORTED)
        sync = world.svc._repo.sync_user_evidence_edges.await_args.kwargs
        assert sync["edge_type"] == "evidence_for"
        insert = world.svc._repo.insert_user_evaluation.await_args.kwargs
        assert insert["evidence_for_node_ids"] == [world.node]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "assessment", [TheoryAssessment.OPEN, TheoryAssessment.UNDER_REVIEW]
    )
    async def test_open_and_under_review_clear_directional_edges(self, world, assessment):
        outcome, _ = await _evaluate(world, assessment=assessment)
        sync = world.svc._repo.sync_user_evidence_edges.await_args.kwargs
        assert sync["edge_type"] is None
        assert outcome.evaluation.to_status is ASSESSMENT_TO_STATUS[assessment]

    @pytest.mark.asyncio
    async def test_no_evidence_is_rejected_before_any_write(self, world):
        with pytest.raises(TheoryEvidenceRequiredError):
            await _evaluate(world, evidence_refs=[])
        world.svc._repo.insert_user_evaluation.assert_not_awaited()
        world.svc._repo.apply_user_evaluation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_foreign_patient_evidence_is_rejected(self, world):
        foreign = world.store.add_fact(OTHER_PATIENT, "symptom:headache")
        with pytest.raises(TheoryEvidenceNotFoundError):
            await _evaluate(world, evidence_refs=[_ref(TheoryEvidenceRefKind.FACT, foreign.id)])
        world.svc._repo.insert_user_evaluation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_blank_rationale_is_rejected(self, world):
        with pytest.raises(TheoryRationaleRequiredError):
            await _evaluate(world, rationale="   ")

    @pytest.mark.asyncio
    async def test_stale_expected_version_conflicts(self, world):
        world.svc._repo.get.return_value = _theory(id=world.theory.id, version=3)
        with pytest.raises(TheoryVersionConflictError):
            await _evaluate(world, expected_version=2)
        world.svc._repo.insert_user_evaluation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_concurrent_write_loses_compare_and_set(self, world):
        world.svc._repo.apply_user_evaluation.return_value = None
        with pytest.raises(TheoryVersionConflictError):
            await _evaluate(world)
        world.svc._repo.sync_user_evidence_edges.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_blocked_theory_cannot_be_evaluated(self, world):
        world.svc._repo.get.return_value = _theory(
            id=world.theory.id, safety_level="blocked_due_to_diagnostic_claim"
        )
        with pytest.raises(TheoryBlockedError):
            await _evaluate(world)

    @pytest.mark.asyncio
    async def test_other_patients_theory_is_not_found(self, world):
        world.svc._repo.get.return_value = _theory(id=world.theory.id, patient_id=OTHER_PATIENT)
        with pytest.raises(TheoryNotFoundError):
            await _evaluate(world)

    @pytest.mark.asyncio
    async def test_idempotent_replay_returns_original_without_writing(self, world):
        prior = _eval_row(world.theory)
        world.svc._repo.find_evaluation_by_idempotency.return_value = prior
        outcome, emit = await _evaluate(world)
        assert outcome.replayed
        assert outcome.evaluation.evaluation_id == prior.id
        world.svc._repo.insert_user_evaluation.assert_not_awaited()
        emit.assert_not_awaited()


class TestAssessmentVocabulary:
    def test_every_mark_maps_to_an_existing_non_diagnostic_status(self):
        assert set(ASSESSMENT_TO_STATUS) == set(TheoryAssessment)
        statuses = {s.value for s in TheoryStatus}
        assert "ruled_out" not in statuses and "confirmed" not in statuses
        assert all(s.value in statuses for s in ASSESSMENT_TO_STATUS.values())

    def test_labels_are_attributed_to_the_user(self):
        for label in ASSESSMENT_LABEL.values():
            assert label.startswith("You ")
        assert ASSESSMENT_LABEL[TheoryAssessment.RULED_OUT] == (
            "You marked this theory as ruled out"
        )
