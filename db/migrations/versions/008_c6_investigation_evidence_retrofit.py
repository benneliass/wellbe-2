"""C6 retrofit for the Health Investigation OS — Investigation/Theory nodes,
new edge types, and a SEPARATE external evidence graph with a patient-scoped
relevance-link bridge.

Implements the three approved decisions:
  - docs/decisions/external-evidence-graph-separation.md   (WEL-130)
  - docs/decisions/investigation-object-and-thread-coupling.md (WEL-128)
  - docs/decisions/theory-object-evaluation-and-safety.md  (WEL-129)

Additive only. Existing graph.kg_nodes / graph.kg_edges rows are preserved.
Hard safety invariants enforced at the schema layer:
  G2 — external knowledge is context, never fact about the user:
       * external sources live in external_kg.* (no patient_id as personal-fact provenance)
       * the ONLY personal<->external link is external_bridge.relevance_links
       * relevance_link is registered in graph.edge_types but FORBIDDEN in graph.kg_edges
  G6 — tenant isolation preserved: the bridge is patient-scoped + RLS, and a trigger
       asserts the personal endpoint belongs to the same patient.
  external_kg gets its own role (wellbe_external); wellbe_graph is NOT granted access.

Revision ID: 008
Revises: 007
Create Date: 2026-06-01
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. C6 node-type retrofit — keep PascalCase codes, add Investigation/Theory.
    #    Lowercase API aliases live in graph.node_type_aliases (no row renames).
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE graph.kg_nodes DROP CONSTRAINT IF EXISTS ck_node_type;
        ALTER TABLE graph.kg_nodes ADD CONSTRAINT ck_node_type CHECK (
          node_type IN (
            'ConditionHypothesis','Symptom','Medication','LabResult','Procedure',
            'VitalSign','Allergy','Immunization','SocialFactor','FamilyHistory','Other',
            'Investigation','Theory'
          )
        );
    """)

    op.execute("""
        CREATE TABLE graph.node_type_aliases (
          code           text PRIMARY KEY,
          canonical_code text NOT NULL,
          domain         text NOT NULL CHECK (domain IN ('clinical','process','hypothesis','other')),
          display_name   text NOT NULL
        );
        INSERT INTO graph.node_type_aliases (code, canonical_code, domain, display_name) VALUES
          ('investigation','Investigation','process','Investigation'),
          ('theory','Theory','hypothesis','Theory');
    """)

    # ------------------------------------------------------------------
    # 2. Edge vocabulary retrofit — new categories + new edge codes.
    #    may_explain remains the strongest causal edge; no diagnostic verbs added.
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE graph.edge_types DROP CONSTRAINT IF EXISTS ck_edge_type_category;
        ALTER TABLE graph.edge_types ADD CONSTRAINT ck_edge_type_category CHECK (
          category IN (
            'causal','correlation','temporal','therapeutic','adverse',
            'contradiction','refinement','evidential','process','external_context'
          )
        );
        INSERT INTO graph.edge_types (code, display_name, category) VALUES
          ('evidence_for',     'Evidence for',            'evidential'),
          ('evidence_against', 'Evidence against',        'evidential'),
          ('investigates',     'Investigates',            'process'),
          ('relevance_link',   'External relevance link', 'external_context')
        ON CONFLICT (code) DO NOTHING;
    """)

    # ------------------------------------------------------------------
    # 3. Guard: relevance_link is registered in the vocabulary but MUST NOT be
    #    stored in the personal graph. It lives only in external_bridge.relevance_links.
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE graph.kg_edges
          ADD CONSTRAINT ck_no_relevance_link_in_personal_graph
          CHECK (edge_type <> 'relevance_link');
    """)

    # ------------------------------------------------------------------
    # 4. Separate External Evidence Graph (C16) — external_kg schema. No patient_id.
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS external_kg")
    op.execute("CREATE SCHEMA IF NOT EXISTS external_bridge")

    op.execute("""
        CREATE TABLE external_kg.external_evidence_sources (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          source_type text NOT NULL CHECK (source_type IN (
            'clinical_guideline','official_body','systematic_review',
            'peer_reviewed_paper','case_report','early_research',
            'medical_blog','expert_explainer','forum_post','anecdote','social_post'
          )),
          source_quality_tier smallint NOT NULL CHECK (source_quality_tier BETWEEN 1 AND 5),
          tier_reason text NOT NULL,
          title text NOT NULL,
          citation_text text,
          url text,
          doi text,
          publisher text,
          publication_date date,
          version_label text,
          retraction_status text NOT NULL DEFAULT 'not_retracted'
            CHECK (retraction_status IN ('not_retracted','expression_of_concern','retracted','superseded')),
          assigned_by text NOT NULL,
          assigned_at timestamptz NOT NULL DEFAULT now(),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE external_kg.external_claims (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),
          claim_text text NOT NULL,
          claim_kind text NOT NULL CHECK (claim_kind IN (
            'association','risk_factor','mechanism','contraindication',
            'guideline_recommendation','educational_context','anecdote'
          )),
          population_context jsonb NOT NULL DEFAULT '{}'::jsonb,
          evidence_attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );

        -- Tier is editorial and auditable; usage can NEVER upgrade a tier.
        CREATE TABLE external_kg.source_quality_reviews (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),
          previous_tier smallint CHECK (previous_tier BETWEEN 1 AND 5),
          new_tier smallint NOT NULL CHECK (new_tier BETWEEN 1 AND 5),
          reason text NOT NULL,
          reviewer_actor_id uuid NOT NULL,
          reviewed_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX ix_external_claims_source ON external_kg.external_claims (source_id);
    """)

    # ------------------------------------------------------------------
    # 5. Relevance-link bridge — patient-scoped, RLS-protected, context-only.
    #    This is the ONLY connection between personal facts and external sources.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE external_bridge.relevance_links (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          patient_id uuid NOT NULL,
          personal_node_id uuid NOT NULL REFERENCES graph.kg_nodes(id),
          thread_id uuid,
          external_source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),
          external_claim_id uuid REFERENCES external_kg.external_claims(id),
          edge_type text NOT NULL DEFAULT 'relevance_link' CHECK (edge_type = 'relevance_link'),
          relevance_score numeric(5,4) NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 1),
          relevance_score_version text NOT NULL,
          relevance_inputs jsonb NOT NULL DEFAULT '{}'::jsonb,
          source_quality_tier_snapshot smallint NOT NULL CHECK (source_quality_tier_snapshot BETWEEN 1 AND 5),
          context_only boolean NOT NULL DEFAULT true CHECK (context_only IS TRUE),
          created_by_actor_id uuid,
          created_under_grant_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (patient_id, personal_node_id, external_source_id, external_claim_id)
        );

        CREATE INDEX ix_relevance_links_patient_node
          ON external_bridge.relevance_links (patient_id, personal_node_id);
    """)

    # Trigger: the personal endpoint must belong to the same patient as the link.
    op.execute("""
        CREATE OR REPLACE FUNCTION external_bridge.check_relevance_personal_endpoint()
        RETURNS TRIGGER AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM graph.kg_nodes n
            WHERE n.id = NEW.personal_node_id AND n.patient_id = NEW.patient_id
          ) THEN
            RAISE EXCEPTION
              'relevance_link tenant violation: personal_node_id % is not owned by patient %',
              NEW.personal_node_id, NEW.patient_id;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER enforce_relevance_personal_endpoint
          BEFORE INSERT OR UPDATE ON external_bridge.relevance_links
          FOR EACH ROW EXECUTE FUNCTION external_bridge.check_relevance_personal_endpoint();
    """)

    # RLS on the bridge (mirrors graph.kg_nodes default-deny pattern).
    op.execute("""
        ALTER TABLE external_bridge.relevance_links ENABLE ROW LEVEL SECURITY;
        CREATE POLICY patient_isolation_relevance_links ON external_bridge.relevance_links
          USING (patient_id::text = current_setting('app.patient_id', true))
          WITH CHECK (patient_id::text = current_setting('app.patient_id', true));
    """)

    # ------------------------------------------------------------------
    # 6. C5 provenance: personal evidence links are personal-source ONLY.
    #    External context never enters evidence.evidence_links / PotentialScoreComputer.
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE evidence.evidence_links
          ADD COLUMN source_scope text NOT NULL DEFAULT 'personal'
          CHECK (source_scope = 'personal');
    """)

    # ------------------------------------------------------------------
    # 7. Separate role for C16. wellbe_graph is intentionally NOT granted access
    #    to external_kg / external_bridge (structural isolation).
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_external') THEN
            CREATE ROLE wellbe_external LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;
        GRANT USAGE ON SCHEMA external_kg TO wellbe_external;
        GRANT USAGE ON SCHEMA external_bridge TO wellbe_external;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA external_kg TO wellbe_external;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA external_bridge TO wellbe_external;
        ALTER DEFAULT PRIVILEGES IN SCHEMA external_kg
            GRANT SELECT, INSERT, UPDATE ON TABLES TO wellbe_external;
        ALTER DEFAULT PRIVILEGES IN SCHEMA external_bridge
            GRANT SELECT, INSERT, UPDATE ON TABLES TO wellbe_external;
        -- bridge needs to validate the personal endpoint exists (FK + trigger)
        GRANT USAGE ON SCHEMA graph TO wellbe_external;
        GRANT SELECT (id, patient_id) ON graph.kg_nodes TO wellbe_external;
    """)


def downgrade() -> None:
    op.execute("""
        REVOKE ALL ON SCHEMA external_kg FROM wellbe_external;
        REVOKE ALL ON SCHEMA external_bridge FROM wellbe_external;
    """)
    op.execute("ALTER TABLE evidence.evidence_links DROP COLUMN IF EXISTS source_scope")
    op.execute("DROP TRIGGER IF EXISTS enforce_relevance_personal_endpoint ON external_bridge.relevance_links")
    op.execute("DROP FUNCTION IF EXISTS external_bridge.check_relevance_personal_endpoint()")
    op.execute("DROP SCHEMA IF EXISTS external_bridge CASCADE")
    op.execute("DROP SCHEMA IF EXISTS external_kg CASCADE")

    op.execute("ALTER TABLE graph.kg_edges DROP CONSTRAINT IF EXISTS ck_no_relevance_link_in_personal_graph")
    op.execute("""
        DELETE FROM graph.edge_types
          WHERE code IN ('evidence_for','evidence_against','investigates','relevance_link');
        ALTER TABLE graph.edge_types DROP CONSTRAINT IF EXISTS ck_edge_type_category;
        ALTER TABLE graph.edge_types ADD CONSTRAINT ck_edge_type_category CHECK (
          category IN (
            'causal','correlation','temporal','therapeutic','adverse',
            'contradiction','refinement'
          )
        );
    """)

    op.execute("DROP TABLE IF EXISTS graph.node_type_aliases")
    op.execute("""
        ALTER TABLE graph.kg_nodes DROP CONSTRAINT IF EXISTS ck_node_type;
        ALTER TABLE graph.kg_nodes ADD CONSTRAINT ck_node_type CHECK (
          node_type IN (
            'ConditionHypothesis','Symptom','Medication','LabResult','Procedure',
            'VitalSign','Allergy','Immunization','SocialFactor','FamilyHistory','Other'
          )
        );
    """)
