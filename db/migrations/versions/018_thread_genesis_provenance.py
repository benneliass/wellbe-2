"""Thread genesis provenance — C7 genesis metadata + C5 thread evidence source.

Implements Story A of the thread-genesis MVP loop (WEL-174), grounded in the
approved decisions:
- docs/decisions/thread-genesis-from-capture.md (WEL-170)
- docs/decisions/thread-genesis-triage-decision-contract.md (WEL-171)

Two changes that together let the continuity/triage genesis consumer create a
Health Thread that is atomically backed by the raw capture it was opened from:

1. ``thread.health_threads`` gains genesis provenance columns
   (``created_by`` user|system, ``created_via``, ``genesis_reason``,
   ``concern_key``). Existing rows are user-created by definition, so
   ``created_by`` backfills to ``'user'``.
2. ``evidence.evidence_links`` allows ``health_thread`` as a ``source_type`` so a
   thread can carry C5 originating evidence links back to its raw source events
   (no orphan claims). The check constraint is widened, not loosened — all prior
   source types remain valid.

Revision ID: 018
Revises: 017
Create Date: 2026-06-18
"""

from alembic import op

# ruff: noqa: E501

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. C7 genesis provenance on health_threads.
    op.execute(
        """
        ALTER TABLE thread.health_threads
          ADD COLUMN created_by text NOT NULL DEFAULT 'user',
          ADD COLUMN created_via text,
          ADD COLUMN genesis_reason text,
          ADD COLUMN concern_key jsonb;
        ALTER TABLE thread.health_threads
          ADD CONSTRAINT ck_health_thread_created_by
          CHECK (created_by IN ('user', 'system'));
        """
    )

    # 2. Allow health_thread as a C5 evidence source_type (widen the check).
    op.execute(
        """
        ALTER TABLE evidence.evidence_links
          DROP CONSTRAINT ck_evidence_source_type;
        ALTER TABLE evidence.evidence_links
          ADD CONSTRAINT ck_evidence_source_type
          CHECK (source_type IN ('extracted_fact', 'health_signal', 'memory_entry', 'ai_summary', 'ai_response', 'health_thread'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE evidence.evidence_links
          DROP CONSTRAINT ck_evidence_source_type;
        ALTER TABLE evidence.evidence_links
          ADD CONSTRAINT ck_evidence_source_type
          CHECK (source_type IN ('extracted_fact', 'health_signal', 'memory_entry', 'ai_summary', 'ai_response'));
        """
    )
    op.execute(
        """
        ALTER TABLE thread.health_threads
          DROP CONSTRAINT IF EXISTS ck_health_thread_created_by;
        ALTER TABLE thread.health_threads
          DROP COLUMN IF EXISTS concern_key,
          DROP COLUMN IF EXISTS genesis_reason,
          DROP COLUMN IF EXISTS created_via,
          DROP COLUMN IF EXISTS created_by;
        """
    )
