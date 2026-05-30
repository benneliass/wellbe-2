# Health Thread state machine

## States

| State | Meaning | Allowed next states |
|---|---|---|
| Draft | user is collecting context but has not activated thread | active_unresolved, archived |
| Active unresolved | concern is current and not explained/closed | waiting_for_result, referred, watchful_waiting, escalated, explained, chronic_monitoring |
| Waiting for result | test/result is pending | active_unresolved, explained, escalated, chronic_monitoring |
| Referred | referral or specialist pathway is open | active_unresolved, waiting_for_result, explained, chronic_monitoring |
| Watchful waiting | plan is to monitor with explicit criteria | active_unresolved, escalated, explained, chronic_monitoring |
| Escalated | user needs timely care or has been advised to seek care | active_unresolved, waiting_for_result, referred, explained |
| Explained | a clinician/user-facing explanation exists and user marks it as adequate | closed, chronic_monitoring, active_unresolved |
| Chronic monitoring | ongoing condition or unresolved long-term pattern being tracked | active_unresolved, escalated, closed |
| Closed | user marks thread resolved or no longer active | reopened |
| Reopened | closed thread has recurrence/new evidence | active_unresolved |

## Closure criteria

A thread should not simply disappear. It can be closed only when one of these is true:

- user says the issue resolved
- clinician explanation is captured and accepted by the user
- monitoring plan exists with clear triggers
- referral/result/follow-up loops are closed or marked impossible/unknown
- user archives it knowingly

## Safety rules

- The system cannot close a thread because a single test is normal.
- The system cannot mark a diagnosis as final.
- If symptoms persist after a normal test, the thread remains active or watchful-waiting with explicit follow-up criteria.
- High-risk safety flags override convenience states.
- User correction can reopen or relabel a thread.
