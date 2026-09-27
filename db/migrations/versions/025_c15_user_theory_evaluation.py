"""C15 user-authored theory evaluation (owner decision 2026-09-27).

The USER marks a theory (open / under_review / supported / weakened / ruled_out)
and must cite personal evidence plus a rationale; the system never auto-decides.
The user's mark maps onto the EXISTING non-diagnostic status taxonomy, so the
``c15.theories.status`` CHECK is unchanged (G1: no ``ruled_out``/``confirmed``
status is ever stored). See docs/decisions/theory-object-evaluation-and-safety.md.

``c15.theory_evaluations`` already exists (012) as the immutable, versioned
evaluation log; user evaluations are recorded in the same log so
``theories.latest_evaluation_id`` and ``evaluation_version`` stay coherent:

- ``evaluation_kind``   'system' (012 evaluator) | 'user'
- ``assessment``        the user's mark (NULL for system rows)
- ``from_status``       theory status before the evaluation
- ``proposed_status``   (existing) = to_status
- ``evaluator_actor_id`` (existing) = actor_id
- ``rationale``         required free text for user rows
- ``evidence_refs``     [{kind, id}] — at least one for user rows
- ``idempotency_key``   unique; replays return the original evaluation

``c15.theories.version`` adds optimistic concurrency (expected_version).

Revision ID: 025
Revises: 024
Create Date: 2026-09-27
"""

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None

_STATUSES = (
    "'unreviewed','needs_more_data','partially_supported',"
    "'not_supported_by_current_data','contradicted_by_current_data',"
    "'discuss_with_clinician','clinician_reviewed'"
)
_ASSESSMENTS = "'open','under_review','supported','weakened','ruled_out'"


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE c15.theories
          ADD COLUMN version integer NOT NULL DEFAULT 1,
          ADD CONSTRAINT ck_theories_version_positive CHECK (version >= 1)
        """
    )
    op.execute(
        f"""
        ALTER TABLE c15.theory_evaluations
          ADD COLUMN evaluation_kind text NOT NULL DEFAULT 'system',
          ADD COLUMN assessment text,
          ADD COLUMN from_status text,
          ADD COLUMN rationale text,
          ADD COLUMN evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
          ADD COLUMN idempotency_key text,
          ADD CONSTRAINT uq_theory_evaluations_idempotency_key UNIQUE (idempotency_key),
          ADD CONSTRAINT ck_theory_eval_kind CHECK (evaluation_kind IN ('system','user')),
          ADD CONSTRAINT ck_theory_eval_assessment
            CHECK (assessment IS NULL OR assessment IN ({_ASSESSMENTS})),
          ADD CONSTRAINT ck_theory_eval_from_status
            CHECK (from_status IS NULL OR from_status IN ({_STATUSES})),
          ADD CONSTRAINT ck_theory_eval_proposed_status
            CHECK (proposed_status IN ({_STATUSES})),
          ADD CONSTRAINT ck_theory_eval_evidence_refs_array
            CHECK (jsonb_typeof(evidence_refs) = 'array'),
          ADD CONSTRAINT ck_theory_eval_user_requirements CHECK (
            evaluation_kind <> 'user' OR (
              assessment IS NOT NULL
              AND from_status IS NOT NULL
              AND evaluator_actor_id IS NOT NULL
              AND rationale IS NOT NULL
              AND length(btrim(rationale)) > 0
              AND jsonb_array_length(evidence_refs) >= 1
            )
          )
        """
    )
    op.execute(
        "CREATE INDEX ix_theory_evaluations_user ON c15.theory_evaluations "
        "(theory_id, evaluation_version DESC) WHERE evaluation_kind = 'user'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS c15.ix_theory_evaluations_user")
    op.execute(
        """
        ALTER TABLE c15.theory_evaluations
          DROP CONSTRAINT IF EXISTS ck_theory_eval_user_requirements,
          DROP CONSTRAINT IF EXISTS ck_theory_eval_evidence_refs_array,
          DROP CONSTRAINT IF EXISTS ck_theory_eval_proposed_status,
          DROP CONSTRAINT IF EXISTS ck_theory_eval_from_status,
          DROP CONSTRAINT IF EXISTS ck_theory_eval_assessment,
          DROP CONSTRAINT IF EXISTS ck_theory_eval_kind,
          DROP CONSTRAINT IF EXISTS uq_theory_evaluations_idempotency_key,
          DROP COLUMN IF EXISTS idempotency_key,
          DROP COLUMN IF EXISTS evidence_refs,
          DROP COLUMN IF EXISTS rationale,
          DROP COLUMN IF EXISTS from_status,
          DROP COLUMN IF EXISTS assessment,
          DROP COLUMN IF EXISTS evaluation_kind
        """
    )
    op.execute(
        """
        ALTER TABLE c15.theories
          DROP CONSTRAINT IF EXISTS ck_theories_version_positive,
          DROP COLUMN IF EXISTS version
        """
    )
