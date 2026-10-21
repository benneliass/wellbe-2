-- One person's pointer graph. Vault text stays on the event row.
-- Accepted edges store ids only.

CREATE TABLE rcb_vault_event (
  id text PRIMARY KEY,
  person_id text NOT NULL,
  note_text text NOT NULL,
  source_type text NOT NULL,
  captured_at text NOT NULL,
  lineage_id text NOT NULL,
  document_id text,
  content_hash text NOT NULL
);

CREATE TABLE rcb_link_advertisement (
  id text PRIMARY KEY,
  sequence bigint NOT NULL,
  person_id text NOT NULL,
  origin text NOT NULL,
  digest text NOT NULL,
  model_version text,
  prompt_version text,
  policy_version text NOT NULL,
  evidence_ids jsonb NOT NULL,
  from_id text NOT NULL,
  to_id text NOT NULL,
  judgment text NOT NULL,
  reason_code text NOT NULL,
  relation text NOT NULL,
  proposed_confidence double precision NOT NULL,
  confidence double precision NOT NULL,
  created_at text NOT NULL,
  supersedes_id text,
  withdrawn boolean NOT NULL
);

CREATE TABLE rcb_pointer_edge (
  person_id text NOT NULL,
  src_id text NOT NULL,
  dst_id text NOT NULL,
  ad_id text NOT NULL,
  confidence double precision NOT NULL,
  reason_code text NOT NULL,
  relation text NOT NULL,
  PRIMARY KEY (person_id, src_id, dst_id)
);

CREATE INDEX rcb_pointer_edge_src ON rcb_pointer_edge (person_id, src_id);
