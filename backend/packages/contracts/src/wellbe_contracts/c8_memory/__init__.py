"""C8 Six Memories Store contracts.

Hybrid store: one append-only ``c8.memory_entries`` base table + typed satellite
tables for pointers and type-specific constraints. C8 stores user-authored entries
and rebuildable derived POINTER projections, but NEVER stores derived clinical
facts as authoritative payload. Every visible entry is written through the C5 gate
and must have >=1 C5 evidence link. Displayed values are resolved at read time via
the shared C11 resolver + current C5/C6 state — C8 has no correction precedence
of its own.

Authoritative decision: docs/decisions/six-memories-store-structure.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event constants
# ---------------------------------------------------------------------------

C8_MEMORY_CREATED = "c8.memory.created"
C8_MEMORY_VISIBLE = "c8.memory.visible"
C8_MEMORY_CONFIRMED = "c8.memory.confirmed"
C8_MEMORY_PROJECTION_STALE = "c8.memory.projection_stale"
C8_MEMORY_READ = "c8.memory.read"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MemoryType(StrEnum):
    STORY = "story"
    CLINICAL = "clinical"
    PATTERN = "pattern"
    DECISION = "decision"
    RESPONSIBILITY = "responsibility"
    EQUITY_ACCESS = "equity_access"


class AuthorshipMode(StrEnum):
    CONTROLLER_AUTHORED = "controller_authored"
    CONTROLLER_CONFIRMED = "controller_confirmed"
    ROLE_AUTHORED_PENDING_ACCEPTANCE = "role_authored_pending_acceptance"
    SYSTEM_DERIVED = "system_derived"
    HYBRID = "hybrid"


class MemoryLifecycleState(StrEnum):
    DRAFT = "draft"
    VISIBLE = "visible"
    NOT_CURRENT = "not_current"
    SUPERSEDED_BY_CORRECTION = "superseded_by_correction"
    PROJECTION_STALE = "projection_stale"
    ARCHIVED = "archived"


class SourceRefType(StrEnum):
    C2_RAW_EVENT = "c2_raw_event"
    C4_EXTRACTED_FACT = "c4_extracted_fact"
    C5_EVIDENCE_LINK = "c5_evidence_link"
    C6_KG_NODE = "c6_kg_node"
    C6_KG_EDGE = "c6_kg_edge"
    C7_THREAD_TRANSITION = "c7_thread_transition"
    C9_PENDING_ITEM = "c9_pending_item"
    C14_INVESTIGATION = "c14_investigation"
    C15_THEORY = "c15_theory"
    C15_THEORY_EVALUATION = "c15_theory_evaluation"
    C10_GATE = "c10_gate"
    C11_CORRECTION = "c11_correction"


class LinkRole(StrEnum):
    PRIMARY = "primary"
    CORROBORATING = "corroborating"
    CONTEXTUAL = "contextual"
    CONTRADICTING = "contradicting"
    DISPLAY_ANCHOR = "display_anchor"


# Authored vs derived vs hybrid classification (decision table). Derived/hybrid
# entries require >=1 C5 evidence link before they can become visible. Authored
# entries are the controller's own words/confirmation.
DEFAULT_AUTHORSHIP: dict[MemoryType, AuthorshipMode] = {
    MemoryType.STORY: AuthorshipMode.CONTROLLER_AUTHORED,
    MemoryType.CLINICAL: AuthorshipMode.SYSTEM_DERIVED,
    MemoryType.PATTERN: AuthorshipMode.SYSTEM_DERIVED,
    MemoryType.DECISION: AuthorshipMode.HYBRID,
    MemoryType.RESPONSIBILITY: AuthorshipMode.HYBRID,
    MemoryType.EQUITY_ACCESS: AuthorshipMode.CONTROLLER_CONFIRMED,
}

# Memory types whose entries are derived (not the controller's own words) and so
# must carry C5 provenance before becoming visible.
DERIVED_MEMORY_TYPES = {MemoryType.CLINICAL, MemoryType.PATTERN}

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class MemorySourceRef(BaseModel):
    source_ref_id: UUID
    source_ref_type: SourceRefType
    link_role: LinkRole = LinkRole.PRIMARY
    field_path: str | None = None
    source_ref_version: str | None = None


class MemoryEntry(BaseModel):
    memory_entry_id: UUID
    patient_id: PatientId
    thread_id: UUID
    memory_type: MemoryType
    authorship_mode: AuthorshipMode
    lifecycle_state: MemoryLifecycleState
    title: str | None = None
    payload: dict = Field(default_factory=dict)  # non-authoritative metadata only
    c10_gate_id: UUID | None = None
    created_at: AwareDatetime | None = None
    visible_at: AwareDatetime | None = None
    source_refs: list[MemorySourceRef] = Field(default_factory=list)


class ResolvedMemoryEntry(BaseModel):
    """A memory entry resolved for read: pointers + C11-resolved overlay state."""

    memory_entry_id: UUID
    memory_type: MemoryType
    lifecycle_state: MemoryLifecycleState
    title: str | None
    source_refs: list[MemorySourceRef]
    # For each correctable source ref, the resolved overlay (from the C11 seam).
    resolved_overlays: list[dict] = Field(default_factory=list)
    projection_stale: bool = False


__all__ = [
    "C8_MEMORY_CREATED",
    "C8_MEMORY_VISIBLE",
    "C8_MEMORY_CONFIRMED",
    "C8_MEMORY_PROJECTION_STALE",
    "C8_MEMORY_READ",
    "MemoryType",
    "AuthorshipMode",
    "MemoryLifecycleState",
    "SourceRefType",
    "LinkRole",
    "DEFAULT_AUTHORSHIP",
    "DERIVED_MEMORY_TYPES",
    "MemorySourceRef",
    "MemoryEntry",
    "ResolvedMemoryEntry",
]
