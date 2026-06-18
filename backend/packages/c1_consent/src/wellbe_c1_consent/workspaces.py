"""C17 workspace enumeration — personal-first, fail-closed.

Implements docs/decisions/workspace-switcher-scope-presentation.md (Spike WEL-184):

  * enumerate only contexts the actor can currently act in — never every workspace.
    The personal (``individual``) workspace is pinned first and always present.
  * membership is presence, not data access. The capability summary is a display-safe
    projection that defaults closed for non-personal contexts; only the controller's
    own personal workspace implies read/contribute on their own data.
  * the dev workspace is just one selectable ``individual`` workspace owned by the
    dev identity — never a default, never special-cased here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class WorkspaceSummary:
    workspace_id: uuid.UUID
    workspace_type: str
    display_name: str
    controller_subject_ref: str
    membership_state: str
    role_type: str
    is_personal: bool
    capability_summary: dict[str, bool] = field(default_factory=dict)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_actor(self, actor_id: uuid.UUID) -> list[WorkspaceSummary]:
        """Return the workspaces the actor can act in, personal pinned first.

        Fail-closed: only persisted memberships are returned. If the actor has no
        persisted personal workspace yet (e.g. pre-onboarding), the caller is
        responsible for synthesizing the personal entry — this method never leaks
        workspaces the actor is not a member of.
        """
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT w.id AS workspace_id,
                           w.workspace_type,
                           w.subject_user_id,
                           m.status AS membership_state,
                           rb.role_type
                    FROM workspace.workspace_memberships m
                    JOIN access.role_bindings rb ON rb.id = m.role_binding_id
                    JOIN workspace.workspaces w ON w.id = m.workspace_id
                    WHERE rb.actor_id = :actor_id
                      AND m.status = 'active'
                      AND w.status = 'active'
                    ORDER BY w.created_at ASC
                    """
                ),
                {"actor_id": actor_id},
            )
        ).mappings().all()

        summaries: list[WorkspaceSummary] = []
        for r in rows:
            is_personal = (
                r["workspace_type"] == "individual"
                and r["subject_user_id"] == actor_id
                and r["role_type"] == "individual_controller"
            )
            summaries.append(
                WorkspaceSummary(
                    workspace_id=r["workspace_id"],
                    workspace_type=r["workspace_type"],
                    display_name=(
                        "Your workspace" if is_personal else _display_for(r["workspace_type"])
                    ),
                    controller_subject_ref=str(r["subject_user_id"] or ""),
                    membership_state=r["membership_state"],
                    role_type=r["role_type"],
                    is_personal=is_personal,
                    # Controller sees their own data; every other context defaults
                    # closed — membership alone never implies data access.
                    capability_summary=(
                        {"can_read": True, "can_contribute": True}
                        if is_personal
                        else {"can_read": False, "can_contribute": False}
                    ),
                )
            )

        # Personal-first ordering.
        summaries.sort(key=lambda s: (not s.is_personal,))
        return summaries


def _display_for(workspace_type: str) -> str:
    return {
        "clinician_case_investigation": "Clinician case workspace",
        "shared_health_thread": "Shared thread workspace",
        "institution_continuity": "Institution workspace",
        "research_sandbox": "Research workspace",
    }.get(workspace_type, "Workspace")
