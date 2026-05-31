"""C6 Knowledge Graph schema.

Revision ID: 006
Revises: 005
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

EDGE_TYPE_SEEDS = [
    {"code": "may_explain", "display_name": "May Explain", "category": "causal"},
    {"code": "associated_with", "display_name": "Associated With", "category": "correlation"},
    {"code": "temporal_sequence", "display_name": "Temporal Sequence", "category": "temporal"},
    {"code": "treats", "display_name": "Treats", "category": "therapeutic"},
    {"code": "worsens", "display_name": "Worsens", "category": "adverse"},
    {"code": "alleviates", "display_name": "Alleviates", "category": "therapeutic"},
    {"code": "co_occurs_with", "display_name": "Co-occurs With", "category": "correlation"},
    {"code": "contradicts", "display_name": "Contradicts", "category": "contradiction"},
    {"code": "refines", "display_name": "Refines", "category": "refinement"},
    {"code": "supersedes", "display_name": "Supersedes", "category": "refinement"},
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS age")
    op.execute("SELECT create_graph('wellbe')")

    op.execute("CREATE SCHEMA IF NOT EXISTS graph")

    op.create_table(
        "edge_types",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "category IN ('causal', 'correlation', 'temporal', 'therapeutic', 'adverse', 'contradiction', 'refinement')",
            name="ck_edge_type_category",
        ),
        schema="graph",
    )

    edge_types_table = sa.table(
        "edge_types",
        sa.column("code", sa.Text),
        sa.column("display_name", sa.Text),
        sa.column("category", sa.Text),
        schema="graph",
    )
    op.bulk_insert(edge_types_table, EDGE_TYPE_SEEDS)

    op.create_table(
        "kg_nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.Text(), nullable=False),
        sa.Column("display_label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "thread_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("embedding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "node_type IN ('ConditionHypothesis', 'Symptom', 'Medication', 'LabResult', 'Procedure', 'VitalSign', 'Allergy', 'Immunization', 'SocialFactor', 'FamilyHistory', 'Other')",
            name="ck_node_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'resolved', 'superseded', 'merged')",
            name="ck_node_status",
        ),
        schema="graph",
    )

    op.create_index(
        "ix_kg_nodes_patient_type",
        "kg_nodes",
        ["patient_id", "node_type"],
        schema="graph",
    )
    op.create_index(
        "ix_kg_nodes_patient_key",
        "kg_nodes",
        ["patient_id", "normalized_key"],
        schema="graph",
        unique=True,
    )

    op.create_table(
        "kg_edges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "from_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("graph.kg_nodes.id"),
            nullable=False,
        ),
        sa.Column(
            "to_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("graph.kg_nodes.id"),
            nullable=False,
        ),
        sa.Column(
            "edge_type",
            sa.Text(),
            sa.ForeignKey("graph.edge_types.code"),
            nullable=False,
        ),
        sa.Column("potential_score", sa.Float(), nullable=False),
        sa.Column("score_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "score_inputs",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column("needs_rescore", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "thread_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "potential_score >= 0 AND potential_score <= 1",
            name="ck_edge_potential_score",
        ),
        sa.CheckConstraint(
            "from_node_id != to_node_id",
            name="ck_no_self_edges",
        ),
        schema="graph",
    )

    op.create_index(
        "ix_kg_edges_patient_from_type_score",
        "kg_edges",
        ["patient_id", "from_node_id", "edge_type", sa.text("potential_score DESC")],
        schema="graph",
    )
    op.create_index(
        "ix_kg_edges_to_node",
        "kg_edges",
        ["to_node_id"],
        schema="graph",
    )
    op.create_index(
        "ix_kg_edges_needs_rescore",
        "kg_edges",
        ["needs_rescore"],
        schema="graph",
        postgresql_where=sa.text("needs_rescore = true"),
    )

    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wellbe_graph') THEN
            CREATE ROLE wellbe_graph LOGIN PASSWORD 'wellbe_dev';
          END IF;
        END $$;
        GRANT USAGE ON SCHEMA graph TO wellbe_graph;
        GRANT USAGE ON SCHEMA evidence TO wellbe_graph;
        GRANT USAGE ON SCHEMA processing TO wellbe_graph;
        GRANT SELECT ON evidence.evidence_links TO wellbe_graph;
        GRANT SELECT ON processing.extracted_facts TO wellbe_graph;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA graph TO wellbe_graph;
        ALTER DEFAULT PRIVILEGES IN SCHEMA graph
            GRANT SELECT, INSERT, UPDATE ON TABLES TO wellbe_graph;
    """)

    op.execute("""
        ALTER TABLE graph.kg_nodes ENABLE ROW LEVEL SECURITY;
        CREATE POLICY patient_isolation_nodes ON graph.kg_nodes
          USING (patient_id::text = current_setting('app.patient_id', true));

        ALTER TABLE graph.kg_edges ENABLE ROW LEVEL SECURITY;
        CREATE POLICY patient_isolation_edges ON graph.kg_edges
          USING (patient_id::text = current_setting('app.patient_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS patient_isolation_edges ON graph.kg_edges")
    op.execute("DROP POLICY IF EXISTS patient_isolation_nodes ON graph.kg_nodes")
    op.drop_index("ix_kg_edges_needs_rescore", table_name="kg_edges", schema="graph")
    op.drop_index("ix_kg_edges_to_node", table_name="kg_edges", schema="graph")
    op.drop_index("ix_kg_edges_patient_from_type_score", table_name="kg_edges", schema="graph")
    op.drop_table("kg_edges", schema="graph")
    op.drop_index("ix_kg_nodes_patient_key", table_name="kg_nodes", schema="graph")
    op.drop_index("ix_kg_nodes_patient_type", table_name="kg_nodes", schema="graph")
    op.drop_table("kg_nodes", schema="graph")
    op.drop_table("edge_types", schema="graph")
    op.execute("DROP SCHEMA IF EXISTS graph")
    op.execute("SELECT drop_graph('wellbe', true)")
    op.execute("DROP EXTENSION IF EXISTS age")
    op.execute("""
        REVOKE ALL ON SCHEMA graph FROM wellbe_graph;
    """)
