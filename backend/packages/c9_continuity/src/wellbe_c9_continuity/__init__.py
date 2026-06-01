"""C9 Continuity & Closure Engine.

Durable pending-item ledger (operational source of truth for follow-ups,
referrals, results) plus one Temporal workflow per active pending item. Consumes
C7 thread.state_changed in order, maintains the normal-test safety net, and
requests thread transitions only through C7 transition_thread with guard metadata.

The Temporal workflow/activities live in ``wellbe_c9_continuity.temporal`` and are
imported only by the continuity-worker (so core ledger logic has no temporalio
dependency).
"""

from wellbe_c9_continuity.errors import (
    ContinuityError,
    OutOfOrderThreadEventError,
    PendingItemNotFoundError,
)
from wellbe_c9_continuity.service import ContinuityService

__all__ = [
    "ContinuityService",
    "ContinuityError",
    "OutOfOrderThreadEventError",
    "PendingItemNotFoundError",
]
