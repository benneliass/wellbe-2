# API and event model sketch

## Core API resources

- `/health-threads`
- `/health-threads/{id}/timeline`
- `/health-threads/{id}/evidence-links`
- `/health-threads/{id}/pending-items`
- `/health-threads/{id}/visit-packets`
- `/raw-context-events`
- `/source-documents`
- `/corrections`
- `/share-grants`
- `/safety-flags`

## Example HealthThread status values

- draft
- active_unresolved
- waiting_for_result
- referred
- watchful_waiting
- escalated
- explained
- chronic_monitoring
- closed
- reopened

## Evidence link reasons

- user_selected
- same_symptom
- same_body_region
- same_time_window
- result_for_order
- referral_for_thread
- medication_change_near_symptom_change
- repeat_visit_similarity
- manual_correction
- unknown
