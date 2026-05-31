# Implementation Status Review: WEL-72 (C1) and WEL-80 (C2)

**Date:** 2026-05-31  
**Purpose:** External review brief — contains all context needed to assess whether WEL-72 and WEL-80 can be marked Done.  
**Why this matters:** WEL-81 (C4 extraction pipeline — the next implementation story) carries an `is blocked by WEL-80` link in Jira. WEL-80 and WEL-72 are still "To Do" in Jira. Code for both components exists. This document is the full picture for deciding if they are truly complete or partially done.

---

## System context (read this first)

WellBe is a personal health intelligence platform built as a Python monorepo. The backend is structured as component packages (`backend/packages/`) consumed by service apps (`backend/apps/`). All components are numbered C1–C13, each with an approved architectural decision record.

The component relevant to this review:

```
C1  Trust & Consent Service       backend/packages/c1_consent/
C2  Raw Context Vault              backend/packages/c2_vault/
                                   backend/apps/vault-writer/
C3  Ingestion Layer                backend/packages/c3_ingestion/
                                   backend/apps/ingestion-worker/
──────────────────────────────────────────────────────
← C4 (next story) starts here and is blocked by C2 being "Done"
```

**C1 is the identity and consent gate.** Every read and write that touches patient data calls C1 first.  
**C2 is the immutable raw event store.** Every piece of patient input is written here once, forever. C4 (the extraction pipeline) reads from C2 and must not start until C2 is verified complete.

---

## WEL-72 — C1 Trust & Consent

**Jira key:** WEL-72  
**Jira title:** Implement OIDC/passkey authentication and scoped consent-share domain model (WB-DEV-001/002)  
**Jira status:** To Do  
**Phase:** mvp | Priority: P1-critical  
**Blocked by:** WEL-93 (Spike — Done ✅), WEL-99 (Scaffold — Done ✅)  
**Decision record:** `docs/decisions/` — see the C1 spike record for the consent scope model

### What is implemented

**File: `backend/packages/c1_consent/src/wellbe_c1_consent/models.py`**

Four SQLAlchemy models in the `consent` Postgres schema:

| Model | Table | What it stores |
|---|---|---|
| `ConsentScopeRow` | `consent.consent_scopes` | Per-actor permission grants: resource_type, action, data_category, validity window |
| `ShareGrantRow` | `consent.share_grants` | User-initiated shares to other users, clinicians, or orgs; with status lifecycle (pending/active/expired/revoked) |
| `RevocationLogRow` | `consent.revocation_log` | Append-only log of every revocation event |
| `PatientPrivacyPreferenceRow` | `consent.patient_privacy_preferences` | Per-patient capability flags (e.g. `cross_patient_analysis`) |

All models are complete and match the approved decision record schema.

---

**File: `backend/packages/c1_consent/src/wellbe_c1_consent/service.py`**

`ConsentService` class — three methods:

```python
async def check_scope(actor_id, resource_type, resource_id, action) -> bool
# Checks consent.consent_scopes with Redis cache (TTL 300s). Returns True if allowed.

async def create_share_grant(...) -> ShareGrantRow
# Creates a share grant row and emits share_grant.created outbox event.

async def revoke_grant(grant_id, revoked_by, reason) -> None
# Sets status=revoked, writes RevocationLogRow, invalidates Redis cache, emits share_grant.revoked.

async def authorized_population_scope(actor_id, purpose) -> bool
# Cross-patient gate: checks patient_privacy_preferences for cross_patient_analysis capability.
```

These methods cover the core consent enforcement surface.

---

**File: `backend/packages/c1_consent/src/wellbe_c1_consent/zitadel.py`**

`ZitadelTokenVerifier` — OIDC JWT verification using Zitadel:

```python
async def verify_token(token: str) -> dict
# Fetches JWKS from Zitadel /.well-known/openid-configuration, verifies RS256 JWT.
# JWKS cached for 3600s. Returns JWT claims.
```

This is a working OIDC token verifier integrated with Zitadel as the identity provider.

---

**File: `backend/packages/c1_consent/src/wellbe_c1_consent/middleware.py`**

FastAPI `auth_dependency`:

```python
async def auth_dependency(request: Request) -> dict
# Reads Bearer token from Authorization header.
# Calls ZitadelTokenVerifier.verify_token().
# Returns { actor_id, sub, scopes, claims }.
# Raises 401 if missing/invalid.
```

This is a FastAPI dependency that any route can use to enforce authentication.

---

### What is NOT visible in the code — open questions for C1

**Question 1: Are passkeys implemented?**

WEL-72's title says "OIDC/passkey authentication." The implementation shows Zitadel JWT (OIDC) verification only. There is no passkey/WebAuthn implementation visible in the codebase.

Passkeys in Zitadel's context: Zitadel can handle passkey enrollment and authentication server-side, after which it issues JWTs as normal. So "passkeys" may mean:
- (a) Zitadel is configured to allow passkey login methods (Zitadel admin config — no backend code needed) → passkey handling is Zitadel's job, `ZitadelTokenVerifier` is already the right integration
- (b) A custom WebAuthn/passkey flow is required in the WellBe backend → this is not implemented

**Needs clarification:** Is passkey support expected to be handled entirely by Zitadel (option a), or does WellBe need to build its own WebAuthn flow (option b)?

---

**Question 2: Are consent management API endpoints implemented?**

The `ConsentService` and models exist in the `c1_consent` package. But API endpoints to:
- Create/list/revoke share grants
- Read consent scope status
- Manage patient privacy preferences

These would live in `backend/apps/api/`. The current `api/main.py` is a stub — it only has a `/health` endpoint. So the consent API surface has no HTTP endpoints yet.

**Needs clarification:** Is the absence of consent API endpoints in scope for WEL-72, or does WEL-72 only cover the domain model and middleware (leaving API endpoints to a later story)?

---

**Question 3: Are database migrations written and verified?**

No migration files are visible in the `backend/packages/c1_consent/` directory. The `consent` schema with its four tables must exist in Postgres before the service works.

**Needs clarification:** Are Alembic migrations for `consent.consent_scopes`, `consent.share_grants`, `consent.revocation_log`, and `consent.patient_privacy_preferences` written and applied?

---

### C1 implementation summary

| Item | Status |
|---|---|
| DB models (4 tables) | ✅ Complete — match approved decision record |
| ConsentService (check_scope, create_share_grant, revoke_grant, cross-patient gate) | ✅ Complete |
| Zitadel OIDC JWT verifier | ✅ Complete |
| FastAPI auth_dependency middleware | ✅ Complete |
| Passkeys (WebAuthn in WellBe backend) | ❓ Unknown — may be Zitadel-only |
| Consent management API endpoints | ❌ Not visible — api/main.py is a stub |
| Database migrations | ❓ Not visible in file listing |

---

## WEL-80 — C2 Raw Context Vault

**Jira key:** WEL-80  
**Jira title:** Build immutable append-only Raw Context Event store with full provenance (WB-DEV-004)  
**Jira status:** To Do  
**Phase:** mvp | Priority: P1-critical  
**Blocked by:** WEL-94 (Spike — Done ✅), WEL-99 (Scaffold — Done ✅)  
**Blocks:** WEL-81 (C4 extraction — the next story)  
**Decision record:** `docs/decisions/raw-context-vault-immutability-enforcement.md` (Approved)

### The immutability requirement (from the approved decision record)

The approved design specifies **four-layer immutability enforcement** for the vault:

| Layer | Mechanism | Purpose |
|---|---|---|
| 1. Application | `VaultRepository` has no update/delete methods; Vault Writer is the only INSERT process | App-level enforcement |
| 2. Postgres role | Only `vault_writer` role has INSERT privilege on `raw_context_events`; no role has UPDATE or DELETE | DB role restriction |
| 3. Postgres trigger | `prevent_raw_context_mutation` trigger raises error on any UPDATE/DELETE at transaction time | Defensive DB constraint |
| 4. S3 object lock | `ObjectLockMode=COMPLIANCE` on every blob upload | Binary payload is physically immutable |

### What is implemented

**File: `backend/packages/c2_vault/src/wellbe_c2_vault/models.py`**

Two SQLAlchemy models in the `vault` Postgres schema:

| Model | Table | What it stores |
|---|---|---|
| `SourceTypeRow` | `vault.raw_context_source_types` | Lookup table of allowed source types |
| `RawContextEventRow` | `vault.raw_context_events` | One row per ingested event — full provenance metadata, content hash, blob reference, consent snapshot, adapter metadata |

The schema exactly matches the approved decision record. All required fields are present including: `content_hash`, `blob_version_id`, `duplicate_of_event_id`, `consent_snapshot_id`, `encryption_key_id`, `schema_version`.

---

**File: `backend/packages/c2_vault/src/wellbe_c2_vault/repository.py`**

`VaultRepository` — three methods only:

```python
async def insert_event(**kwargs) -> UUID     # INSERT only — no update/delete
async def get_event(event_id) -> Row | None  # read by PK
async def find_duplicate(patient_id, content_hash) -> UUID | None  # deduplication check
```

Layer 1 (application-level no-update/delete) is enforced: there are no `update_event` or `delete_event` methods.

---

**File: `backend/packages/c2_vault/src/wellbe_c2_vault/s3.py`**

`S3BlobStore` — two methods:

```python
async def upload_blob(key, data, content_hash) -> str  # PUT to S3
async def get_blob(key) -> bytes                        # GET from S3
```

The `upload_blob` implementation uses a standard `put_object` call:

```python
self._client.put_object(
    Bucket=self._bucket,
    Key=key,
    Body=data,
)
```

**S3 object lock is NOT configured in this call.** The approved decision record requires `ObjectLockMode=COMPLIANCE` on every upload. The current code does not pass `ObjectLockMode` or `ObjectLockRetainUntilDate` to `put_object`.

---

**File: `backend/apps/vault-writer/src/wellbe_vault_writer/main.py`**

The Vault Writer is a fully working FastAPI service:

- `POST /vault/events` — receives `VaultWriteRequest`, computes `SHA-256` content hash, deduplicates by `(patient_id, content_hash)`, uploads blob to S3, inserts `RawContextEventRow`, emits `raw_context.received` outbox event, commits in one transaction
- `GET /vault/events/{event_id}` — reads a raw event by ID
- `GET /health` — health check

The service correctly emits `raw_context.received` on the outbox, which is the event C4 subscribes to. The service structure is complete and correct.

---

### What is NOT visible in the code — open questions for C2

**Question 1 (Critical): Is S3 Object Lock configured?**

The approved decision record explicitly requires `ObjectLockMode=COMPLIANCE` per blob upload. The current `S3BlobStore.upload_blob` does a plain `put_object` with no lock parameters. Two possibilities:

- (a) The S3 bucket was created with default Object Lock enabled at the bucket level (via bucket creation config or Terraform/infra script), so all objects get locked automatically without per-put parameters
- (b) S3 Object Lock was not implemented — the blobs are mutable at the S3 level

If (b), this is an incomplete acceptance criterion. The immutability guarantee is weakened: a malicious or buggy process with S3 write access could overwrite or delete raw event blobs.

**Needs clarification:** Is the S3 bucket configured with bucket-level Object Lock? Or does `upload_blob` need to be updated to pass `ObjectLockMode=COMPLIANCE` and `ObjectLockRetainUntilDate`?

---

**Question 2 (Critical): Is the Postgres immutability trigger present?**

The approved decision record requires:

```sql
CREATE OR REPLACE FUNCTION prevent_raw_context_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'raw_context_events is append-only — mutation is not permitted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_raw_context_mutation
BEFORE UPDATE OR DELETE ON vault.raw_context_events
FOR EACH ROW EXECUTE FUNCTION prevent_raw_context_mutation();
```

This trigger is not visible in the Python codebase. It should be in an Alembic migration file. No migration files are visible in the current file listing.

**Needs clarification:** Is the `prevent_raw_context_mutation` trigger written in a migration and applied to the Postgres database?

---

**Question 3: Are database migrations written and verified?**

Similar to C1 — no Alembic migration files are visible in the file listing. The `vault` schema with its tables and indexes must exist.

**Needs clarification:** Are Alembic migrations for `vault.raw_context_events` and `vault.raw_context_source_types` written and applied? Does the migration include the immutability trigger?

---

**Question 4: Is the Postgres role restriction in place?**

The approved design specifies that only a `vault_writer` database role has INSERT on `vault.raw_context_events`, and no role has UPDATE or DELETE. This is a DB-level GRANT/REVOKE configuration — it would be in a migration or infrastructure script, not in Python code.

**Needs clarification:** Is the `vault_writer` role restriction applied? Or does the default application DB user still have UPDATE/DELETE on `vault.raw_context_events`?

---

### C2 implementation summary

| Item | Status |
|---|---|
| DB models (`RawContextEventRow`, `SourceTypeRow`) | ✅ Complete — match approved decision record |
| `VaultRepository` (insert, get, find_duplicate — no update/delete) | ✅ Complete |
| `S3BlobStore` (upload, get) | ✅ Application code complete |
| Vault Writer FastAPI service (POST, GET, /health) | ✅ Complete — deduplication, outbox event emission, single-transaction commit |
| Layer 1 (app-level no-mutation) | ✅ Complete — no update/delete on VaultRepository |
| Layer 2 (Postgres role restriction) | ❓ Not verifiable from Python code — needs migration/infra check |
| Layer 3 (Postgres immutability trigger) | ❓ Not visible — needs migration check |
| Layer 4 (S3 Object Lock) | ❌ `upload_blob` uses plain `put_object` — no lock parameters |
| Database migrations | ❓ Not visible in file listing |

---

## The question that needs a decision

Jira shows WEL-80 blocks WEL-81. For the next implementation story (WEL-81 — C4 Processing Pipeline) to begin:

### Decision A: Is WEL-80 Done?

- The application code for C2 is complete and correct.
- The missing items are all infrastructure/migration-level: S3 Object Lock, Postgres trigger, DB role restriction.

Choose one:

1. **WEL-80 is Done** — accept that infrastructure layers (S3 lock, trigger, role) will be applied before production deploy but are not required to mark the code story Done. WEL-81 can start.

2. **WEL-80 is partially Done** — the infrastructure constraints are part of the story's acceptance criteria and must be in a migration before WEL-80 is Done. Create sub-tasks for the missing items:
   - Add `ObjectLockMode=COMPLIANCE` to `S3BlobStore.upload_blob`
   - Write Alembic migration with `prevent_raw_context_mutation` trigger
   - Write Alembic migration with `vault_writer` role GRANT/REVOKE

3. **WEL-80 is Done but with a gap story** — mark WEL-80 Done for the application code, and create a new mvp story: "Apply C2 immutability constraints: S3 object lock, Postgres trigger, DB role restriction." WEL-81 can start in parallel.

---

### Decision B: Is WEL-72 Done?

- The application code for C1 is complete (models, service, OIDC verifier, auth middleware).
- Open items: passkey scope, consent API endpoints, migrations.

Choose one:

1. **WEL-72 is Done** — OIDC via Zitadel covers the auth requirement; passkeys are handled by Zitadel's own UI and login flow (no backend code needed); consent API endpoints belong to C13 (WEL-65), not C1; migrations are scripted elsewhere. WEL-72 can be closed.

2. **WEL-72 is partially Done** — passkeys require a dedicated passkey enrollment API in the WellBe backend; consent management endpoints are in scope for WEL-72, not C13. Need to define what remains.

3. **WEL-72 is Done but with a gap story** — mark WEL-72 Done for the domain model and OIDC auth, and create a new story for passkey enrollment if that is a distinct requirement.

---

## Why this decision is on the critical path

```
Decision needed:
  WEL-80 Done?  →  WEL-81 (C4) can start
                    WEL-81 → contracts/c4_processing populated
                    → WEL-83 (C5) can start
                    → WEL-64 (C7 Health Thread), WEL-70 (C8 Memories),
                      WEL-74 (C10 Safety Gate) all unblocked

  WEL-72 Done?  →  No direct Jira blocker on WEL-81 (WEL-81 is only blocked
                    by WEL-80), but C1 is a logical dependency of every
                    authenticated write in the system. If WEL-72 is incomplete,
                    end-to-end flows that require auth will fail in integration.
```

---

## Quick reference: file locations

| What | Where |
|---|---|
| C1 models | `backend/packages/c1_consent/src/wellbe_c1_consent/models.py` |
| C1 service | `backend/packages/c1_consent/src/wellbe_c1_consent/service.py` |
| C1 OIDC verifier | `backend/packages/c1_consent/src/wellbe_c1_consent/zitadel.py` |
| C1 auth middleware | `backend/packages/c1_consent/src/wellbe_c1_consent/middleware.py` |
| C1 contracts | `backend/packages/contracts/src/wellbe_contracts/c1_consent/scopes.py` |
| C2 models | `backend/packages/c2_vault/src/wellbe_c2_vault/models.py` |
| C2 repository | `backend/packages/c2_vault/src/wellbe_c2_vault/repository.py` |
| C2 S3 store | `backend/packages/c2_vault/src/wellbe_c2_vault/s3.py` |
| Vault Writer service | `backend/apps/vault-writer/src/wellbe_vault_writer/main.py` |
| C2 contracts | `backend/packages/contracts/src/wellbe_contracts/c2_vault/events.py` |
| C2 decision record | `docs/decisions/raw-context-vault-immutability-enforcement.md` |
| C1 decision record (spike) | Search `docs/decisions/` for `c1` or `consent` |
| WEL-72 Jira | https://belias.atlassian.net/browse/WEL-72 |
| WEL-80 Jira | https://belias.atlassian.net/browse/WEL-80 |
