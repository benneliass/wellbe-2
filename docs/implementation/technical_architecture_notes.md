# Technical architecture notes

## Event types

- raw_context.received
- raw_context.processed
- fact.extracted
- health_signal.created
- thread.created
- thread.link_suggested
- thread.link_confirmed
- thread.state_changed
- pending_item.created
- pending_item.due
- pending_item.closed
- result.imported
- result.status_changed
- referral.created
- referral.status_changed
- visit_packet.generated
- share_grant.created
- share_grant.revoked
- correction.submitted
- correction.applied_to_memory
- safety_flag.created
- ai_output.blocked

## Required services

- Raw Context Vault
- Processing Pipeline
- Evidence Traceability Service
- Health Thread Service
- Pending Item Service
- Referral/Result Tracker
- Visit Packet Generator
- Safety Engine
- Consent/Share Grant Service
- Notification Service
- Audit Service

## Important separation

Raw data, derived facts, user corrections, generated summaries, and shared views must be separate storage layers. Corrections do not mutate raw sources; they create a new linked correction object.
