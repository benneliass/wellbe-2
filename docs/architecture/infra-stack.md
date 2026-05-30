# Infrastructure Stack

Deployment, runtime, observability, secrets, CI/CD, and security posture. Selection bias matches `tech-stack.md`: mature, privacy-friendly, self-hostable, and **compliance-aware** (PHI: HIPAA/GDPR posture by default).

Two deployment profiles are defined so the project does not over-build at MVP:

- **Profile A — Lean (MVP):** managed PaaS, smallest moving-part count.
- **Profile B — Platform (scale / regulated):** Kubernetes-based, the target for production at scale.

---

## 1. Containers & runtime

| Concern | Choice | Profile | Requirement served | Risk |
|---|---|---|---|---|
| Packaging | **Docker / OCI images**, multi-stage builds | A + B | Reproducible builds for API (C13), workers, safety gate (C10), OCR. | Low |
| Orchestration (Lean) | **Fly.io** or single-cloud managed containers + **managed Postgres** | A | Fast path to production with minimal ops; fine for early single-region. | Low |
| Orchestration (Platform) | **Kubernetes** (managed: EKS/GKE) + **CloudNativePG** operator for Postgres HA | B | HA Postgres (the whole datastore is Postgres-centric), autoscaling, multi-AZ. | Medium |
| Node autoscaling | **Karpenter** | B | Right-size compute for spiky OCR/LLM/engine workloads. | Low |
| Networking / zero-trust | **Cilium** (eBPF) + **Gateway API** | B | Per-service micro-segmentation; isolate PHI-handling services. | Medium |

Decision: **start on Profile A**; the architecture (stateless API + Temporal + Postgres) lifts to Profile B without redesign. Flag: do not adopt Kubernetes until traffic/compliance justify it.
Source: [cloud-native-ref](https://github.com/Smana/cloud-native-ref/blob/main/README.md).

---

## 2. Infrastructure as Code

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **OpenTofu** (+ **Terramate** for stacks) | OpenTofu 1.9+ | Declarative infra; **native state encryption at rest** (KMS) — important because state holds DB/connection secrets for a PHI system. | Terraform, Pulumi | Low |

Why OpenTofu over Terraform: open-source (MPL 2.0, Linux Foundation, no BSL licensing risk) and **state encryption at rest** is native — the single most relevant feature for a PHI system. HCL is identical, so this is a low-friction choice.
Sources: [OpenTofu vs Terraform 2026](https://tasrieit.com/blog/opentofu-vs-terraform-2026).

---

## 3. GitOps & CI/CD

| Concern | Choice | Requirement served | Risk |
|---|---|---|---|
| CI/CD | **GitHub Actions** | Build, test, scan, sign images; gate on the safety/eval suite for any change touching C10 or AI features. | Low |
| GitOps delivery (Platform) | **Flux** (or Argo CD) | Declarative cluster reconciliation; auditable deploys. | Low |
| Supply chain | Image signing (cosign/Sigstore) + SBOM + dependency/secret scanning in CI | No untrusted artifact reaches a PHI environment. | Low |

CI policy: any PR that modifies the Safety & Governance Gate (C10), do-not-diagnose rules, or an AI feature must pass the safety evaluation harness before merge. See `../safety/`.

---

## 4. Observability

| Signal | Choice | Requirement served | Risk |
|---|---|---|---|
| Instrumentation | **OpenTelemetry** (vendor-neutral) across API, workers, safety gate | One tracing/metrics standard; no vendor lock. | Low |
| Metrics | **Prometheus / Mimir** (or VictoriaMetrics) | Service health, queue depth, engine latency, **safety-gate block rate**. | Low |
| Logs | **Loki** (or VictoriaLogs) | Structured logs; **PHI scrubbing at the logging boundary**. | Medium |
| Traces | **Tempo** | End-to-end trace of capture → process → graph → thread → safety → render. | Low |
| Dashboards | **Grafana** | Unified LGTM view; on-call dashboards. | Low |

Product-specific SLOs to track: safety-gate availability (must be ~100% or output is blocked), `ai_output.blocked` rate, pending-item timer accuracy (Temporal), ingestion provenance completeness (every fact has a source). **No PHI in telemetry** — scrub at the OTel collector.
Sources: [DevOps tools by category 2026](https://medium.com/@h.stoychev87/devops-cloud-platform-tools-by-category-for-2026-68ed92103c17).

---

## 5. Secrets & key management

| Concern | Choice | Requirement served | Risk |
|---|---|---|---|
| Secrets store | **OpenBao** (open-source Vault fork) | Dynamic DB creds, API keys, FHIR/wearable OAuth client secrets, PKI. | Medium |
| K8s secret sync (Platform) | **External Secrets Operator** | Sync OpenBao → workloads without committing secrets. | Low |
| Encryption keys | Cloud **KMS** (envelope encryption) | At-rest encryption for Postgres, object storage, and OpenTofu state. | Low |
| Per-user data keys | Per-user / per-record envelope keys for the Raw Context Vault (C2) | Strong tenant isolation; supports user-initiated deletion (crypto-shred). | Medium |

Per-user envelope encryption supports the guardrail that each user's data is isolated and the user can revoke/delete; deleting a user's key effectively destroys their PHI.

---

## 6. Data storage & backup

| Concern | Choice | Requirement served | Risk |
|---|---|---|---|
| Relational/graph/vector/timeseries | **PostgreSQL 17** (single engine, see `tech-stack.md`) — managed (Profile A) or CloudNativePG (Profile B) | One backup/restore/HA playbook for all data models. | Low |
| Object storage | **S3-compatible** (versioned, encrypted) | Raw documents/images for the Vault (C2); immutability via object-lock. | Low |
| Backups | PITR (WAL archiving) + periodic encrypted snapshots; restore drills | Recoverability of immutable raw context + provenance. | Low |
| Cache / broker | **Redis** | Dramatiq broker, Redis Streams events, session/rate-limit. | Low |

Object-lock + versioning on the document bucket enforces "raw context immutability" at the storage layer (corrections never mutate originals — they create new linked objects, per C11).

---

## 7. Compliance & security posture (PHI)

| Control | Implementation |
|---|---|
| Encryption in transit | TLS everywhere; mTLS between services (Cilium, Platform). |
| Encryption at rest | KMS envelope keys for Postgres, object storage, OpenTofu state; per-user data keys. |
| Audit trail | Append-only Audit Service (C12); Temporal histories double as a workflow audit log. |
| Access control | OIDC (ZITADEL) + least-privilege RBAC; consent scopes enforced at C13 on every call. |
| Data residency | Region-pinned Postgres + object storage; configurable per jurisdiction (supports `Global by configuration`). |
| Third-party PHI | Self-host by default (OCR, wearable aggregator, LLM); BAA/DPA required before any PHI leaves the boundary. |
| Data deletion | Crypto-shred via per-user key destruction; revocation log (C1). |

These controls operationalize the vision guardrails: **the user is the data controller**, sharing is scoped and revocable, and **no cross-patient data path exists by default**.

---

## 8. Environments

| Env | Purpose | Data |
|---|---|---|
| dev | Local (docker-compose: Postgres+extensions, Redis, Temporal dev server, MinIO, mock IdP) | synthetic only |
| staging | Pre-prod, full stack | synthetic / de-identified only |
| prod | Live | real PHI, full compliance controls |

Hard rule: **no real PHI in dev or staging.** OCR/LLM/FHIR connectors run against sandboxes (e.g. SMART sandbox) outside prod.

---

## Infra summary (one line)

Containerized Python/TS services on **Fly.io → Kubernetes (CloudNativePG)**, provisioned with **OpenTofu**, delivered via **GitHub Actions (+ Flux)**, observed with **OpenTelemetry + Grafana LGTM**, secured with **OpenBao + KMS (per-user envelope keys)**, on a **PostgreSQL-centric** data plane — with PHI kept in-house by default.
