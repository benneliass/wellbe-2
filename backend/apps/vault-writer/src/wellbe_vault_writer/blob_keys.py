from __future__ import annotations

import hashlib
from uuid import UUID


def build_raw_blob_key(patient_id: UUID, event_id: UUID) -> str:
    patient_hash = hashlib.sha256(patient_id.bytes).hexdigest()
    return f"raw/patient/{patient_hash}/event/{event_id}/blob"
