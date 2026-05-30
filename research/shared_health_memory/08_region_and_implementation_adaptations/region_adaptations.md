# Region and Implementation Adaptations

## High-resource / EHR-heavy systems

- Integrate with FHIR/SMART APIs where available.
- Build clinician summaries and follow-up queues directly into workflow.
- Use safety governance, audit logs, and alert fatigue monitoring.

## Fragmented or multi-provider systems

- Use patient-held Health Threads and exportable summaries.
- Support document upload and source labeling.
- Make ownership explicit when clinical responsibility is unclear.

## Low-resource settings

- Support printable or SMS-based summaries.
- Prioritize referral tracking, follow-up reminders, and CHW handoffs.
- Avoid assuming continuous internet, complete EHR access, or rapid specialist availability.

## Cultural and access considerations

- Capture language preferences, caregiver involvement, disability needs, access barriers, and trust/safety concerns.
- Avoid designs that only serve digitally fluent patients.
