"""C7 Health Thread Engine schema.

Implements the approved WEL-92 decision:
docs/decisions/health-thread-state-machine-enforcement.md

Creates the ``thread`` schema with:
- ``health_threads`` — canonical current status + status_version for fast reads
- ``thread_state_transitions`` — append-only lifecycle history (one row per commit)
- ``health_thread_allowed_transitions`` — DB-level lookup of structurally allowed
  edges, seeded to match the Python graph in wellbe_contracts.c7_thread
- a BEFORE UPDATE trigger that rejects any status change not present in the
  allowed-transitions table (defence-in-depth; the domain layer is the primary
  owner of transition validity).

State-change events are written to the existing events.outbox_events table.

Revision ID: 010
Revises: 009
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Migration DDL favors exact SQL/check-constraint readability over wrapping.
# ruff: noqa: E501

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

_STATUS_VALUES = (
    "draft",
    "active_unresolved",
    "waiting_for_result",
    "referred",
    "watchful_waiting",
    "escalated",
    "explained",
    "chronic_monitoring",
    "closed",
    "reopened",
    "archived",
)

# (from_status, to_status) edges — must match wellbe_contracts.c7_thread.ALLOWED_TRANSITIONS
_ALLOWED_EDGES = [
    ("draft", "active_unresolved"),
    ("draft", "archived"),
    ("active_unresolved", "waiting_for_result"),
    ("active_unresolved", "referred"),
    ("active_unresolved", "watchful_waiting"),
    ("active_unresolved", "escalated"),
    ("active_unresolved", "explained"),
    ("active_unresolved", "chronic_monitoring"),
    ("waiting_for_result", "active_unresolved"),
    ("waiting_for_result", "explained"),
    ("waiting_for_result", "escalated"),
    ("waiting_for_result", "chronic_monitoring"),
    ("referred", "active_unresolved"),
    ("referred", "waiting_for_result"),
    ("referred", "explained"),
    ("referred", "chronic_monitoring"),
    ("watchful_waiting", "active_unresolved"),
    ("watchful_waiting", "escalated"),
    ("watchful_waiting", "explained"),
    ("watchful_waiting", "chronic_monitoring"),
    ("escalated", "active_unresolved"),
    ("escalated", "waiting_for_result"),
    ("escalated", "referred"),
    ("escalated", "explained"),
    ("explained", "closed"),
    ("explained", "chronic_monitoring"),
    ("explained", "active_unresolved"),
    ("chronic_monitoring", "active_unresolved"),
    ("chronic_monitoring", "escalated"),
    ("chronic_monitoring", "closed"),
    ("closed", "reopened"),
    ("reopened", "active_unresolved"),
]

_STATUS_CHECK = "status IN (" + ", ".join(f"'{s}'" for s in _STATUS_VALUES) + ")"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS thread")

    op.create_table(
        "health_threads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("status_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(_STATUS_CHECK, name="ck_health_thread_status"),
        sa.CheckConstraint("status_version >= 1", name="ck_health_thread_version_positive"),
        schema="thread",
    )
    op.create_index(
        "ix_health_threads_patient",
        "health_threads",
        ["patient_id", "status"],
        schema="thread",
    )

    op.create_table(
        "thread_state_transitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("thread.health_threads.id"),
            nullable=False,
        ),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("transition_seq", sa.Integer(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "safety_flags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "actor_type IN ('user','clinician','system','workflow','admin')",
            name="ck_transition_actor_type",
        ),
        sa.UniqueConstraint(
            "thread_id", "transition_seq", name="uq_thread_transition_seq"
        ),
        sa.UniqueConstraint(
            "thread_id", "idempotency_key", name="uq_thread_idempotency_key"
        ),
        schema="thread",
    )
    op.create_index(
        "ix_thread_transitions_thread",
        "thread_state_transitions",
        ["thread_id", "transition_seq"],
        schema="thread",
    )

    op.create_table(
        "health_thread_allowed_transitions",
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("from_status", "to_status", name="pk_allowed_transition"),
        schema="thread",
    )

    values_sql = ", ".join(f"('{f}', '{t}')" for f, t in _ALLOWED_EDGES)
    op.execute(
        f"""
        INSERT INTO thread.health_thread_allowed_transitions (from_status, to_status)
        VALUES {values_sql}
        ON CONFLICT (from_status, to_status) DO NOTHING;
        """
    )

    # Defence-in-depth: reject any status change not present in the allowed table.
    # The domain layer is the primary owner; this trigger catches direct/buggy writes.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION thread.enforce_health_thread_transition()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT EXISTS (
                    SELECT 1 FROM thread.health_thread_allowed_transitions a
                    WHERE a.from_status = OLD.status AND a.to_status = NEW.status
                ) THEN
                    RAISE EXCEPTION
                        'Illegal health thread transition: % -> %', OLD.status, NEW.status
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.status_version <= OLD.status_version THEN
                    RAISE EXCEPTION
                        'status_version must increase on transition (% -> %)',
                        OLD.status_version, NEW.status_version
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_enforce_health_thread_transition
            BEFORE UPDATE ON thread.health_threads
            FOR EACH ROW
            EXECUTE FUNCTION thread.enforce_health_thread_transition();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_enforce_health_thread_transition ON thread.health_threads"
    )
    op.execute("DROP FUNCTION IF EXISTS thread.enforce_health_thread_transition()")
    op.drop_table("health_thread_allowed_transitions", schema="thread")
    op.drop_table("thread_state_transitions", schema="thread")
    op.drop_table("health_threads", schema="thread")
    op.execute("DROP SCHEMA IF EXISTS thread")
