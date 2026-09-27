"""Stored document processing status + sanitised original filename (additive).

``/v2/documents`` previously inferred status from extracted facts plus a
30-minute window, and could only show a generic label because capture kept
just a hash of the filename.

- ``processing.document_processing_status`` — one mutable row per document
  capture: received -> processing -> processed | needs_ocr | failed. It lives
  in ``processing`` because ``vault.raw_context_events`` is immutable. The
  vault writer inserts 'received' in the same transaction as the capture; the
  processing worker moves it along.
- ``vault.raw_context_events.original_filename`` — nullable sanitised display
  name (basename only, never a path), written once at insert. Existing rows
  stay NULL and keep the current fallback label.

Backfill (existing document captures): 'processed' if any facts exist,
'received' if captured within the last 30 minutes (the old grace window),
otherwise 'needs_ocr'. Backfilled rows carry ``detail = 'backfill_027'``.

Revision ID: 027
Revises: 026
Create Date: 2026-09-27
"""

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE vault.raw_context_events ADD COLUMN original_filename text")

    op.execute(
        """
        CREATE TABLE processing.document_processing_status (
            raw_context_event_id uuid PRIMARY KEY
                REFERENCES vault.raw_context_events (id),
            patient_id uuid NOT NULL,
            status text NOT NULL,
            detail text,
            attempts integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_document_processing_status CHECK (
                status IN ('received', 'processing', 'processed', 'needs_ocr', 'failed')
            ),
            CONSTRAINT ck_document_processing_attempts CHECK (attempts >= 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_processing_status_patient "
        "ON processing.document_processing_status (patient_id)"
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE ON processing.document_processing_status
            TO wellbe_processing;
        GRANT USAGE ON SCHEMA processing TO wellbe_vault;
        GRANT INSERT ON processing.document_processing_status TO wellbe_vault;
        """
    )

    op.execute(
        """
        INSERT INTO processing.document_processing_status
            (raw_context_event_id, patient_id, status, detail, attempts)
        SELECT e.id,
               e.patient_id,
               CASE
                 WHEN EXISTS (
                   SELECT 1 FROM processing.extracted_facts f
                   WHERE f.raw_context_event_id = e.id
                 ) THEN 'processed'
                 WHEN e.captured_at > now() - interval '30 minutes' THEN 'received'
                 ELSE 'needs_ocr'
               END,
               'backfill_027',
               0
        FROM vault.raw_context_events e
        WHERE e.duplicate_of_event_id IS NULL
          AND (e.source_type IN ('pdf', 'photo')
               OR e.source_metadata ->> 'capture_type' = 'document')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS processing.document_processing_status")
    op.execute("REVOKE INSERT ON ALL TABLES IN SCHEMA processing FROM wellbe_vault")
    op.execute("REVOKE USAGE ON SCHEMA processing FROM wellbe_vault")
    op.execute("ALTER TABLE vault.raw_context_events DROP COLUMN IF EXISTS original_filename")
