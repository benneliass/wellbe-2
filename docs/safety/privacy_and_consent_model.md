# Privacy and consent model

## Personal-first rule

The user is the primary controller of WellBe memory. Institutions may be integration endpoints or distribution partners, but they do not get default control over user data.

## Sharing primitives

- ShareGrant: scoped, revocable, time-limited access to selected thread context.
- Export: user-generated PDF/Markdown/structured packet.
- ImportGrant: user authorizes import from portal, device, file, lab, or manual source.
- CrossPatientOptIn: separate explicit opt-in for comparison features; off by default.

## Role / Grant model (workspaces)

The expanded vision adds role-specific workspaces (Individual, Clinician Case Investigation, Shared Health Thread, Institution Continuity, Research Sandbox). Access is always grant-based. Every Grant specifies:

- `recipient_role`: caregiver | clinician | care team | institution | researcher
- `purpose`: why access is granted
- `scope`: visit-packet-only | specific-thread | labs+symptoms | wearable-trends-only | full-investigation
- `duration` / expiry (time-limited; may auto-expire after a visit or date)
- `can_comment`, `can_export`, `can_invite`
- `contribution_becomes_permanent_record`: whether the recipient's contributions persist in the record
- `workspace_scope`: which workspace the grant applies to

Rules:
- The individual is always the data controller; a Role never confers control.
- Shared does not mean everyone sees everything — the user grants specific slices of a thread.
- Institution access is **aggregate-only and consented**; institutions never receive default individual-level data.
- Researcher access requires explicit research consent under protocol governance, and is opt-in per the cross-patient rule.

## Forbidden defaults

- institution-wide aggregate analytics without user opt-in
- clinician enabling cross-patient comparison on behalf of a user
- employer/payer access by default
- hidden secondary use of thread data
- irreversible sharing

## Audit

Every import, extraction, correction, summary generation, share, view, revocation, grant creation/expiry, workspace access, and external-evidence linkage should be auditable to the user.
