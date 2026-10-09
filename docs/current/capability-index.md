# Capability index

last_full_review: 2026-10-09

Current behavior in code. Not identity, not intent, and not a decision record. Contract: [README.md](README.md).

## Product capabilities

| id | status | does | evidence | gap | intent |
|---|---|---|---|---|---|
| auth | shipped | The person signs in with ZITADEL or the local demo login and gets a session. | `apps/web/app/login`, `backend/apps/api/src/wellbe_api/main.py` | | C1 |
| grants | shipped | The person can grant scoped, revocable access to their own data. | `backend/packages/c1_consent` | | C1, C17 |
| evidence | shipped | Derived facts stay linked to the raw source they came from. | `backend/packages/c5_evidence` | | C5, WB2-F004 |
| onboarding | shipped | The person starts, edits, and finalizes onboarding before using the workspace. | `apps/web/app/onboarding/page.tsx` | | C1 |
| home | shipped | Home shows the person's threads, open loops, what changed, and things noticed. | `apps/web/app/(workspace)/workspace/page.tsx` | | C7, C9 |
| capture | shipped | The person adds symptom or context text and it is written through the capture API. | `apps/web/components/capture/CaptureModal.tsx` | | C3, WB2-F001 |
| thread-detail | partial | A real thread shows its timeline, theories, graph slice, memories, and next actions. | `apps/web/app/(workspace)/threads/[id]/page.tsx` | Demo thread ids still render from mock data. | C7 |
| ask | shipped | Ask answers from the person's own closed corpus through a deterministic engine, with the safety gate in front. | `apps/web/app/(workspace)/ask/page.tsx` | | C10, C13 |
| patterns | shipped | Patterns shows non-diagnostic observations drawn from the person's graph. | `apps/web/app/(workspace)/patterns/page.tsx` | | C6 |
| delta | shipped | Delta shows what changed in the person's own record over a window. | `apps/web/app/(workspace)/delta/page.tsx` | | C9 |
| graph | shipped | The graph page maps the person's concerns, events, and evidence, with a labelled sample preview kept separate. | `apps/web/app/(workspace)/graph/page.tsx` | | C6, WB2-F033 |
| records | shipped | Results, documents, and memory hubs read the person's records from the API. | `apps/web/app/(workspace)/results`, `apps/web/app/(workspace)/memory` | | C5, C8 |
| appointments | partial | Appointments lists open loops from the continuity ledger. | `apps/web/app/(workspace)/appointments/page.tsx` | There is no calendar or appointment scheduler. | C9, WB2-F007 |
| visit-packet | shipped | The person composes a visit packet, reviews it, and shares it by a token they control. | `apps/web/app/(workspace)/prepare`, `apps/web/app/shared/[token]` | | C13, WB2-F011 |
| triage | shipped | Check-in evaluates urgency with the safety rules and does not diagnose. | `apps/web/app/(workspace)/triage` | | C10 |
| investigations | shipped | The person can open and update an investigation tied to a thread. | `backend/packages/c14_investigation` | | C14 |
| theories | shipped | A theory can be recorded and evaluated against the person's evidence, and it is never a diagnosis. | `backend/packages/c15_theory` | | C15, WB2-F035 |
| corrections | shipped | A correction is stored as a new source-linked layer and does not overwrite raw input. | `backend/packages/c11_correction` | | C11, WB2-F010 |
| notifications | shipped | In-app notifications can be listed and marked read. | `backend/apps/notification-worker` | | C12 |

## Operations

| id | status | does | evidence | gap | intent |
|---|---|---|---|---|---|
| api | shipped | One FastAPI app is the external boundary for auth, capture, threads, and the v2 read surfaces. | `backend/apps/api/src/wellbe_api/main.py` | | C13 |
| vault-writer | shipped | Raw context is appended to the vault, with blobs in object storage. | `backend/apps/vault-writer` | | C2 |
| ingestion | partial | Manual text and documents are ingested into the vault. | `backend/apps/ingestion-worker` | SMS and other source adapters are not implemented. | C3 |
| processing | partial | A worker extracts facts with keyword rules and runs local Tesseract OCR for images and PDFs. | `backend/apps/processing-worker` | Extraction is not a model-based NER pipeline. | C4 |
| continuity-worker | shipped | Due pending items are swept on a timer. | `backend/apps/continuity-worker` | | C9 |
| safety-gate | partial | User-facing model output is checked by a fail-closed deterministic safety service. | `backend/apps/safety-gate` | NeMo Guardrails and Llama Guard are not in the gate. | C10 |
| audit-service | partial | The audit service exposes the audit and notification derive endpoints. | `backend/apps/audit-service` | The ledger used by the standalone service is in memory. | C12 |
| local-stack | shipped | Local Postgres and the app can be brought up with the repo's compose, kind, and Helm chart. | `infra/local` | | |
| migrations | shipped | Alembic migrations through the current component schemas are in the repo. | `db/migrations` | | |

## Known non-capabilities

| id | status | does | evidence | gap | intent |
|---|---|---|---|---|---|
| mobile | partial | The mobile package is an Expo shell with no screens. | `apps/mobile/index.ts` | No mobile UI is built. | |
| temporal-ocr | partial | A Temporal worker is registered for durable OCR. | `backend/apps/temporal-worker` | Its OCR activities return placeholder text. | C4 |
| webauthn | designed | Passkey login is specified for trust and consent and is not in the sign-in flow. | | Passkeys are not implemented. | C1 |
| cross-patient | deferred | Comparing this person's record with other people is specified as opt-in and is not a running feature. | | | WB2-F032 |
| fhir-import | deferred | Pulling records from a care institution is specified as user-initiated and is not built. | | | WB2-F041 |
| wearables | deferred | Wearable ingestion is specified and is not built. | | | WB2-F039 |
