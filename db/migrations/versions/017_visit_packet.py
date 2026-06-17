"""Visit Packet — user-controlled clinician packet, source-linked + scoped share.

Implements the approved decision docs/decisions/visit-packet-composition-gating.md
(WEL-30 / WEL-68):

- ``visit_packet.packets`` — a draft/shared packet scoped to selected threads.
- ``visit_packet.statements`` — the two-layer composed content (patient-prep +
  optional source-backed summary). Each statement carries a per-statement
  ``classification`` and ``source_refs`` (no orphan claims), explicit absence
  semantics (``absent`` + ``absence_reason``), and a deselection-visibility flag
  (``included`` — deselected statements are kept and marked, never silently
  dropped).
- ``visit_packet.share_links`` — a named-recipient, time-boxed, passcode-
  protected, revocable delivery link. Revocation flips status (future access
  only). The raw token is never stored — only its sha-256 hash.

Patient isolation is enforced in the C13 boundary (application layer), matching
the C7 ``thread`` tables, so the public share-link read can resolve a packet by
token without a patient session.

Revision ID: 017
Revises: 016
Create Date: 2026-06-18
"""

from alembic import op

# ruff: noqa: E501

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS visit_packet")

    op.execute(
        """
        CREATE TABLE visit_packet.packets (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          title text NOT NULL,
          status text NOT NULL DEFAULT 'draft',
          thread_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          time_window_start timestamp,
          time_window_end timestamp,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          updated_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          CONSTRAINT visit_packet_status_ck
            CHECK (status IN ('draft', 'shared'))
        )
        """
    )
    op.execute("CREATE INDEX ix_visit_packet_packets_patient ON visit_packet.packets (patient_id)")

    op.execute(
        """
        CREATE TABLE visit_packet.statements (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          packet_id uuid NOT NULL REFERENCES visit_packet.packets(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          layer text NOT NULL,
          section text NOT NULL,
          ordinal integer NOT NULL,
          text text NOT NULL,
          classification text NOT NULL,
          source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
          absent boolean NOT NULL DEFAULT false,
          absence_reason text,
          included boolean NOT NULL DEFAULT true,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          CONSTRAINT visit_packet_layer_ck
            CHECK (layer IN ('patient_prep', 'summary')),
          CONSTRAINT visit_packet_classification_ck
            CHECK (classification IN (
              'direct_source_fact', 'patient_reported', 'generated_synthesis',
              'generated_inference', 'source_record_diagnosis', 'new_ai_diagnosis'
            )),
          CONSTRAINT visit_packet_absence_reason_ck
            CHECK (absence_reason IS NULL OR absence_reason IN (
              'known_absent', 'not_asked', 'unavailable', 'masked'
            ))
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_visit_packet_statements_packet ON visit_packet.statements (packet_id, ordinal)"
    )

    op.execute(
        """
        CREATE TABLE visit_packet.share_links (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          packet_id uuid NOT NULL REFERENCES visit_packet.packets(id) ON DELETE CASCADE,
          patient_id uuid NOT NULL,
          grant_id uuid,
          token_hash text NOT NULL UNIQUE,
          passcode_hash text,
          recipient_name text NOT NULL,
          recipient_identifier_hash text,
          purpose text NOT NULL,
          info_scope text NOT NULL,
          c10_decision text,
          c10_render_token text,
          status text NOT NULL DEFAULT 'active',
          expires_at timestamp NOT NULL,
          created_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
          revoked_at timestamp,
          CONSTRAINT visit_packet_share_status_ck
            CHECK (status IN ('active', 'revoked', 'expired'))
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_visit_packet_share_links_packet ON visit_packet.share_links (packet_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS visit_packet.share_links")
    op.execute("DROP TABLE IF EXISTS visit_packet.statements")
    op.execute("DROP TABLE IF EXISTS visit_packet.packets")
    op.execute("DROP SCHEMA IF EXISTS visit_packet")
