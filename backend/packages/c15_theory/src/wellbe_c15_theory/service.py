"""C15 Theory service.

Theory is the most diagnosis-adjacent surface. Safety is layered:
  1. normalizer.py blocks/reframes diagnostic text (C15 validator)
  2. personal support status comes from personal facts ONLY (G2)
  3. external sources attach as context, never as graph evidence edges (G2)
  4. every user-facing output passes the C10 gate (consumed via its contract)
  5. schema constraints + prohibited edges back-stop the above
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c6_graph.repository import GraphRepository
from wellbe_contracts.c15_theory import (
    ASSESSMENT_EVIDENCE_DIRECTION,
    ASSESSMENT_TO_STATUS,
    MAX_EVIDENCE_REFS,
    RATIONALE_MAX_LENGTH,
    THEORY_CREATED,
    THEORY_EVALUATED,
    THEORY_USER_EVALUATED,
    ContextDirection,
    EvidenceDirection,
    ExternalContextRef,
    PersonalEvidenceRef,
    TheoryAssessment,
    TheoryCreatedPayload,
    TheoryEvaluatedPayload,
    TheoryEvaluationResult,
    TheoryEvidenceRef,
    TheorySafetyLevel,
    TheoryStatus,
    TheoryType,
    TheoryUserEvaluatedPayload,
    TheoryUserEvaluation,
)
from wellbe_events import emit_event

from wellbe_c15_theory import c10_gate
from wellbe_c15_theory.errors import (
    TheoryBlockedError,
    TheoryEvidenceRequiredError,
    TheoryNotFoundError,
    TheoryRationaleRequiredError,
    TheoryVersionConflictError,
)
from wellbe_c15_theory.evidence import EvidenceStore, SqlEvidenceStore, resolve_evidence
from wellbe_c15_theory.models import TheoryEvaluationRow
from wellbe_c15_theory.normalizer import normalize_theory_text, theory_display_label
from wellbe_c15_theory.repository import TheoryRepository
from wellbe_c15_theory.status_rules import status_from_personal_evidence

_EDGE_TYPE = {
    EvidenceDirection.FOR: "evidence_for",
    EvidenceDirection.AGAINST: "evidence_against",
}
_DEFAULT_EVIDENCE_SCORE = 0.5


class TheoryService:
    def __init__(
        self, session: AsyncSession, *, evidence_store: EvidenceStore | None = None
    ) -> None:
        self._session = session
        self._repo = TheoryRepository(session)
        self._graph = GraphRepository(session)
        self._evidence: EvidenceStore = evidence_store or SqlEvidenceStore(session)

    async def create_theory(
        self,
        *,
        patient_id: uuid.UUID,
        theory_text: str,
        theory_type: TheoryType,
        correlation_id: str,
        trace_id: str,
        linked_investigation_id: uuid.UUID | None = None,
        created_by_actor_id: uuid.UUID | None = None,
        theory_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        tid = theory_id or uuid.uuid4()
        normalization = normalize_theory_text(theory_text)

        await self._repo.create_theory(
            theory_id=tid,
            patient_id=patient_id,
            theory_text=theory_text,
            normalized_question=normalization.normalized_question,
            theory_type=theory_type.value,
            status=TheoryStatus.UNREVIEWED.value,
            safety_level=normalization.safety_level.value,
            linked_investigation_id=linked_investigation_id,
            created_by_actor_id=created_by_actor_id,
        )

        node_id: uuid.UUID | None = None
        if not normalization.blocked and normalization.normalized_question is not None:
            # Only non-blocked theories get a projection node (blocked = withheld).
            node_id = await self._repo.create_projection_node(
                patient_id=patient_id,
                theory_id=tid,
                display_label=theory_display_label(
                    normalization.normalized_question, theory_text
                ),
            )
            await self._repo.set_projection_node(tid, node_id)

        await emit_event(
            session=self._session,
            event_type=THEORY_CREATED,
            payload=TheoryCreatedPayload(
                theory_id=tid,
                patient_id=patient_id,
                theory_type=theory_type,
                status=TheoryStatus.UNREVIEWED,
                safety_level=normalization.safety_level,
                normalized_question=normalization.normalized_question,
                blocked=normalization.blocked,
                projection_node_id=node_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return tid

    async def evaluate_theory(
        self,
        *,
        theory_id: uuid.UUID,
        correlation_id: str,
        trace_id: str,
        personal_evidence: list[PersonalEvidenceRef] | None = None,
        external_context: list[ExternalContextRef] | None = None,
        missing_data: list[dict[str, object]] | None = None,
        urgent_symptom_present: bool = False,
        evaluator_actor_id: uuid.UUID | None = None,
    ) -> TheoryEvaluationResult:
        personal_evidence = personal_evidence or []
        external_context = external_context or []
        missing_data = missing_data or []

        theory = await self._repo.get(theory_id)
        if theory is None:
            raise TheoryNotFoundError(theory_id)
        if theory.safety_level == TheorySafetyLevel.BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM.value:
            raise TheoryBlockedError(theory_id)

        theory_node_id = theory.projection_node_id
        if theory_node_id is None:
            theory_node_id = await self._repo.create_projection_node(
                patient_id=theory.patient_id,
                theory_id=theory_id,
                display_label=theory_display_label(
                    theory.normalized_question, theory.theory_text
                ),
            )
            await self._repo.set_projection_node(theory_id, theory_node_id)

        # 1. Personal evidence edges ONLY (personal fact node -> Theory node).
        for_ids: list[uuid.UUID] = []
        against_ids: list[uuid.UUID] = []
        for ref in personal_evidence:
            await self._repo.create_evidence_edge(
                patient_id=theory.patient_id,
                from_node_id=ref.node_id,
                theory_node_id=theory_node_id,
                edge_type=_EDGE_TYPE[ref.direction],
                potential_score=_DEFAULT_EVIDENCE_SCORE,
            )
            if ref.direction is EvidenceDirection.FOR:
                for_ids.append(ref.node_id)
            else:
                against_ids.append(ref.node_id)

        # 2. External context attached separately (never a graph evidence edge).
        context_link_ids: list[uuid.UUID] = []
        for ctx in external_context:
            await self._repo.insert_external_context(
                theory_id=theory_id,
                patient_id=theory.patient_id,
                external_source_id=ctx.external_source_id,
                external_claim_id=ctx.external_claim_id,
                relevance_link_id=ctx.relevance_link_id,
                context_direction=ctx.context_direction.value
                if isinstance(ctx.context_direction, ContextDirection)
                else ctx.context_direction,
            )
            context_link_ids.append(ctx.relevance_link_id)

        # 3. Status from PERSONAL evidence only; safety_level + clinician routing.
        personal_status = status_from_personal_evidence(
            evidence_for=len(for_ids),
            evidence_against=len(against_ids),
            has_missing_data=bool(missing_data),
        )
        if urgent_symptom_present:
            safety_level = TheorySafetyLevel.URGENT_SYMPTOM_PRESENT
            status = TheoryStatus.DISCUSS_WITH_CLINICIAN
        elif against_ids:
            safety_level = TheorySafetyLevel.NEEDS_CLINICIAN_CONTEXT
            status = TheoryStatus.DISCUSS_WITH_CLINICIAN
        else:
            safety_level = TheorySafetyLevel.LOW
            status = personal_status

        # 4. Route user-facing text through C10 (consumed via its contract).
        output_text = theory.normalized_question or "Could my data be related to this?"
        c10_response = c10_gate.evaluate_theory_output(
            theory_id=theory_id,
            patient_id=theory.patient_id,
            actor_id=evaluator_actor_id,
            output_text=output_text,
            safety_level=safety_level,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        # 5. Persist immutable evaluation + apply to theory.
        evaluation_id = uuid.uuid4()
        version = await self._repo.next_evaluation_version(theory_id)
        await self._repo.insert_evaluation(
            evaluation_id=evaluation_id,
            theory_id=theory_id,
            patient_id=theory.patient_id,
            evaluation_version=version,
            evidence_for_node_ids=for_ids,
            evidence_against_node_ids=against_ids,
            missing_data=missing_data,
            external_context_link_ids=context_link_ids,
            proposed_status=status.value,
            proposed_safety_level=safety_level.value,
            c10_gate_result=c10_response.model_dump(mode="json"),
            evaluator_actor_id=evaluator_actor_id,
        )
        await self._repo.apply_evaluation(
            theory_id=theory_id,
            status=status.value,
            safety_level=safety_level.value,
            latest_evaluation_id=evaluation_id,
        )

        event_id = await emit_event(
            session=self._session,
            event_type=THEORY_EVALUATED,
            payload=TheoryEvaluatedPayload(
                theory_id=theory_id,
                patient_id=theory.patient_id,
                evaluation_id=evaluation_id,
                evaluation_version=version,
                status=status,
                safety_level=safety_level,
                c10_decision=c10_response.decision.value,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        return TheoryEvaluationResult(
            theory_id=theory_id,
            evaluation_id=evaluation_id,
            evaluation_version=version,
            status=status,
            safety_level=safety_level,
            evidence_for_count=len(for_ids),
            evidence_against_count=len(against_ids),
            c10_decision=c10_response.decision.value,
            event_id=event_id,
        )

    async def evaluate_by_user(
        self,
        *,
        theory_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_id: uuid.UUID,
        assessment: TheoryAssessment,
        rationale: str,
        evidence_refs: list[TheoryEvidenceRef],
        expected_version: int,
        investigation_thread_ids: list[uuid.UUID],
        idempotency_key: str,
        correlation_id: str,
        trace_id: str,
    ) -> UserEvaluationOutcome:
        """Record the USER's evaluation of a theory. The system never decides.

        The user's mark maps onto the non-diagnostic status taxonomy; every cited
        ref must be the patient's own and belong to the investigation's threads.
        Only the status changes — safety_level is never lowered by a user mark.
        """
        key = f"theory-eval:{theory_id}:{idempotency_key}"
        prior = await self._repo.find_evaluation_by_idempotency(key)
        if prior is not None:
            theory = await self._repo.get(theory_id)
            if prior.theory_id != theory_id or theory is None or theory.patient_id != patient_id:
                raise TheoryNotFoundError(theory_id)
            return UserEvaluationOutcome(
                evaluation=user_evaluation_from_row(prior),
                theory_version=theory.version,
                replayed=True,
            )

        theory = await self._repo.get(theory_id)
        if theory is None or theory.patient_id != patient_id:
            raise TheoryNotFoundError(theory_id)
        if theory.safety_level == TheorySafetyLevel.BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM.value:
            raise TheoryBlockedError(theory_id)
        if theory.version != expected_version:
            raise TheoryVersionConflictError(theory_id, expected_version, theory.version)

        text = rationale.strip()
        if not text:
            raise TheoryRationaleRequiredError("Add a short note explaining your evaluation.")
        if len(text) > RATIONALE_MAX_LENGTH:
            raise TheoryRationaleRequiredError(
                f"Keep the note under {RATIONALE_MAX_LENGTH} characters."
            )
        if len(evidence_refs) > MAX_EVIDENCE_REFS:
            raise TheoryEvidenceRequiredError(
                f"Cite at most {MAX_EVIDENCE_REFS} pieces of evidence."
            )

        resolved = await resolve_evidence(
            self._evidence,
            patient_id=patient_id,
            thread_ids=investigation_thread_ids,
            refs=evidence_refs,
        )

        from_status = TheoryStatus(theory.status)
        to_status = ASSESSMENT_TO_STATUS[assessment]
        direction = ASSESSMENT_EVIDENCE_DIRECTION[assessment]
        node_ids = resolved.node_ids

        theory_node_id = theory.projection_node_id
        if theory_node_id is None:
            theory_node_id = await self._repo.create_projection_node(
                patient_id=patient_id,
                theory_id=theory_id,
                display_label=theory_display_label(
                    theory.normalized_question, theory.theory_text
                ),
            )
            await self._repo.set_projection_node(theory_id, theory_node_id)

        evaluation_id = uuid.uuid4()
        evaluation_version = await self._repo.next_evaluation_version(theory_id)
        refs_json = [r.model_dump(mode="json") for r in resolved.refs]
        row = await self._repo.insert_user_evaluation(
            evaluation_id=evaluation_id,
            theory_id=theory_id,
            patient_id=patient_id,
            evaluation_version=evaluation_version,
            actor_id=actor_id,
            assessment=assessment.value,
            from_status=from_status.value,
            to_status=to_status.value,
            safety_level=theory.safety_level,
            rationale=text,
            evidence_refs=refs_json,
            evidence_for_node_ids=node_ids if direction is EvidenceDirection.FOR else [],
            evidence_against_node_ids=(
                node_ids if direction is EvidenceDirection.AGAINST else []
            ),
            idempotency_key=key,
        )
        new_version = await self._repo.apply_user_evaluation(
            theory_id=theory_id,
            expected_version=expected_version,
            status=to_status.value,
            latest_evaluation_id=evaluation_id,
        )
        if new_version is None:
            raise TheoryVersionConflictError(theory_id, expected_version, expected_version + 1)

        # C6 projection: the theory node reflects the user's current evaluation.
        edge_type = _EDGE_TYPE[direction] if direction is not None else None
        score_inputs_by_node = {
            node_id: {
                "score_semantics": "user_cited_evidence",
                "theory_id": str(theory_id),
                "evaluation_id": str(evaluation_id),
                "assessment": assessment.value,
                "evidence_refs": [
                    r.model_dump(mode="json") for r in resolved.refs_for_node(node_id)
                ],
                "source_ref_id": str(resolved.refs_for_node(node_id)[0].id),
            }
            for node_id in node_ids
        }
        await self._repo.sync_user_evidence_edges(
            patient_id=patient_id,
            theory_node_id=theory_node_id,
            edge_type=edge_type,
            score_inputs_by_node=score_inputs_by_node,
            potential_score=_DEFAULT_EVIDENCE_SCORE,
        )
        for thread_id in investigation_thread_ids:
            await self._graph.tag_nodes_with_thread(
                patient_id=patient_id, node_ids=[theory_node_id], thread_id=thread_id
            )
            await self._graph.tag_edges_within_thread(patient_id=patient_id, thread_id=thread_id)
        await self._repo.update_theory_node(
            patient_id=patient_id,
            node_id=theory_node_id,
            metadata={
                "theory_status": to_status.value,
                "user_assessment": assessment.value,
                "latest_evaluation_id": str(evaluation_id),
                "evaluated_by": "user",
            },
        )

        evaluation = user_evaluation_from_row(row)
        event_id = await emit_event(
            session=self._session,
            event_type=THEORY_USER_EVALUATED,
            payload=TheoryUserEvaluatedPayload(
                theory_id=theory_id,
                patient_id=patient_id,
                investigation_id=theory.linked_investigation_id,
                evaluation_id=evaluation_id,
                evaluation_version=evaluation_version,
                actor_id=actor_id,
                assessment=assessment,
                from_status=from_status,
                to_status=to_status,
                theory_version=new_version,
                evidence_refs=resolved.refs,
                evidence_node_ids=node_ids,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return UserEvaluationOutcome(
            evaluation=evaluation, theory_version=new_version, event_id=event_id
        )


@dataclass
class UserEvaluationOutcome:
    evaluation: TheoryUserEvaluation
    theory_version: int
    replayed: bool = False
    event_id: uuid.UUID | None = None


def user_evaluation_from_row(row: TheoryEvaluationRow) -> TheoryUserEvaluation:
    if row.evaluator_actor_id is None or row.assessment is None or row.from_status is None:
        raise ValueError(f"Theory evaluation {row.id} is not a user evaluation")
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return TheoryUserEvaluation(
        evaluation_id=row.id,
        theory_id=row.theory_id,
        patient_id=row.patient_id,
        actor_id=row.evaluator_actor_id,
        evaluation_version=row.evaluation_version,
        assessment=TheoryAssessment(row.assessment),
        from_status=TheoryStatus(row.from_status),
        to_status=TheoryStatus(row.proposed_status),
        rationale=row.rationale or "",
        evidence_refs=[TheoryEvidenceRef.model_validate(r) for r in row.evidence_refs or []],
        evidence_node_ids=[
            *(row.evidence_for_node_ids or []),
            *(row.evidence_against_node_ids or []),
        ],
        created_at=created,
    )
