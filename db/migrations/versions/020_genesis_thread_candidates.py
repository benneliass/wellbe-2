"""Thread genesis pending candidates — the durable "Things noticed" store.

Implements Story C0 of the thread-genesis MVP loop (WEL-177), grounded in the
approved decision docs/decisions/thread-genesis-pending-candidate-object.md
(WEL-171, S2).

Creates ``genesis.thread_candidates`` — the non-alarming, lossless destination for
weak/ambiguous concern signals that are not yet active threads. It is deliberately
a distinct store from the C9 ``pending_items`` ledger, which mandates a
``primary_thread_id`` and uses follow-up/referral statuses and so cannot represent
a pre-thread candidate.

Create/update is idempotent on ``candidate_key`` (a deterministic hash of the
concern key + episode bucket, excluding the source event) so repeated mentions of
one concern update a single candidate (``seen_count`` increments) rather than
fragmenting. ``ck_genesis_candidate_has_source`` enforces no-orphan candidates —
every candidate traces back to a capture or a fact.

Revision ID: 020
Revises: 019
Create Date: 2026-06-18
"""

from alembic import op

# ruff: noqa: E501

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE genesis.thread_candidates (
          candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          candidate_key text NOT NULL,
          concern_key jsonb NOT NULL DEFAULT '{}'::jsonb,
          episode_bucket text NOT NULL,
          display_title text NOT NULL,
          candidate_type text NOT NULL,
          source_capture_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          source_fact_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          source_graph_entity_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          evidence_link_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
          status text NOT NULL DEFAULT 'pending',
          confidence double precision,
          reason_code text,
          first_seen_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          last_seen_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          seen_count integer NOT NULL DEFAULT 1,
          promoted_thread_id uuid,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          updated_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          CONSTRAINT ck_genesis_candidate_status
            CHECK (status IN ('pending', 'promoted', 'dismissed', 'merged', 'expired')),
          CONSTRAINT ck_genesis_candidate_has_source
            CHECK (cardinality(source_capture_ids) > 0 OR cardinality(source_fact_ids) > 0),
          CONSTRAINT uq_genesis_candidate_key UNIQUE (candidate_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_genesis_candidates_pending ON genesis.thread_candidates (user_id, last_seen_at DESC) WHERE status = 'pending'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS genesis.thread_candidates")
