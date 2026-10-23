"""Co-occurrence sees the brain's neighbours, not every nearby capture."""

from __future__ import annotations

import uuid

from wellbe_processing_worker.tasks import _rows_in_brain_view

_HERE = uuid.uuid4()
_NEAR = uuid.uuid4()
_OTHER = uuid.uuid4()


def test_a_nearby_capture_outside_the_brain_is_left_out() -> None:
    rows = [
        {"raw_context_event_id": _HERE, "normalized_key": "fever"},
        {"raw_context_event_id": _NEAR, "normalized_key": "chills"},
        {"raw_context_event_id": _OTHER, "normalized_key": "headache"},
    ]
    kept = _rows_in_brain_view(rows, _HERE, [str(_NEAR)])
    assert [row["normalized_key"] for row in kept] == ["fever", "chills"]
