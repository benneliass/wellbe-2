from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field

PatientId = Annotated[UUID, Field(description="Unique identifier for a patient")]
ActorId = Annotated[UUID, Field(description="Unique identifier for the acting user or system")]
EventId = Annotated[UUID, Field(description="Unique identifier for a raw context event")]
GrantId = Annotated[UUID, Field(description="Unique identifier for a share grant")]
ConsentSnapshotId = Annotated[UUID, Field(description="Unique identifier for a consent snapshot")]
