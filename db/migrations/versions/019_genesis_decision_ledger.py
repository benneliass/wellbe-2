"""Thread genesis decision ledger — append-only, idempotent triage records.

Implements Story B0 of the thread-genesis MVP loop (WEL-175), grounded in the
approved decision docs/decisions/thread-genesis-triage-decision-contract.md
(WEL-171, S1).

Creates the ``genesis`` schema with ``genesis_decisions`` — one row per
(concern_key, genesis event) routing decision. Append-only and idempotent on
``decision_inputs_hash`` (redelivery of the same genesis event is a no-op via
ON CONFLICT DO NOTHING). A re-evaluation under a new ``policy_version`` writes a
new row that references the prior via ``supersedes_decision_id`` rather than
mutating it.

This is an internal pipeline ledger written by the system genesis consumer
(analogous to ``evidence.evidence_links``): no clinical facts, never mutated, so
no row-level security — patient isolation is enforced at any read boundary.

Revision ID: 019
Revises: 018
Create Date: 2026-06-18
"""

from alembic import op

# ruff: noqa: E501

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS genesis")

    op.execute(
        """
        CREATE TABLE genesis.genesis_decisions (
          decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          source_event_id uuid NOT NULL,
          capture_id uuid NOT NULL,
          fact_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          graph_node_id uuid,
          graph_cluster_id uuid,
          concern_key jsonb NOT NULL DEFAULT '{}'::jsonb,
          episode_bucket text NOT NULL,
          decision text NOT NULL,
          reason_code text NOT NULL,
          confidence double precision,
          policy_version integer NOT NULL,
          target_thread_id uuid,
          candidate_id uuid,
          created_thread_id uuid,
          evidence_link_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          decision_inputs_hash text NOT NULL,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          supersedes_decision_id uuid,
          CONSTRAINT ck_genesis_decision
            CHECK (decision IN ('attach', 'create', 'candidate', 'no_thread')),
          CONSTRAINT uq_genesis_decision_inputs_hash UNIQUE (decision_inputs_hash)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_genesis_decisions_capture ON genesis.genesis_decisions (capture_id)"
    )
    op.execute(
        "CREATE INDEX ix_genesis_decisions_user ON genesis.genesis_decisions (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS genesis CASCADE")
