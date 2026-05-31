"""C5 Evidence link idempotency: unique constraint to prevent duplicate links on redelivery.

Adds a uniqueness guarantee on evidence.evidence_links so that at-least-once
re-delivery of the same processing event cannot create duplicate evidence links.
The natural identity of an evidence link is the (source object, raw event it cites,
relationship kind) tuple, captured by (source_type, source_id, raw_context_event_id,
link_type). Combined with deterministic source ids and an ON CONFLICT DO NOTHING write
in the C5 repository, re-processing an event becomes idempotent at the link layer.

This does NOT change no-orphan-claims semantics — the deferred provenance trigger from
migration 005 still enforces that every link cites an existing vault event.

Revision ID: 007
Revises: 006
Create Date: 2026-05-31
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_evidence_link_dedup",
        "evidence_links",
        ["source_type", "source_id", "raw_context_event_id", "link_type"],
        schema="evidence",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_evidence_link_dedup",
        "evidence_links",
        schema="evidence",
        type_="unique",
    )
