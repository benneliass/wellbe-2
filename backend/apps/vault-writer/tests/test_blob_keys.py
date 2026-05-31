from __future__ import annotations

from uuid import UUID

from wellbe_vault_writer.blob_keys import build_raw_blob_key


def test_raw_blob_key_uses_patient_hash_not_patient_id():
    patient_id = UUID("00000000-0000-0000-0000-000000000001")
    event_id = UUID("00000000-0000-0000-0000-000000000002")

    key = build_raw_blob_key(patient_id, event_id)

    assert key.startswith("raw/patient/")
    assert str(patient_id) not in key
    assert key.endswith(f"/event/{event_id}/blob")
