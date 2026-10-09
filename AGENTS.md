# Agent Instructions

## Bible Files — Require Explicit User Approval to Modify

**When the user says "bible", "bible file", or "the bible" in this project, they mean this list.**
Bible files are canonical truth documents. No agent may edit, rename, move, or delete them without explicit user approval. See `.cursor/rules/doc-governance.mdc` for the full doc re-eval protocol.

Quick reference by topic:
- "personal first / organization as channel" → `docs/system-design/platform_identity.md`
- "vision and scope" → `VISION.md`
- "design principles" → `docs/system-design/system_principles.md`
- "system architecture and operating loop" → `docs/system-design/system_design.md`
- "safety rules / no diagnosis" → `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`
- "audience guardrails" → `.cursor/rules/audience-guardrails.mdc`
- "vision guardrails (agent)" → `.cursor/rules/wellbe-vision-guardrails.mdc`
- "infrastructure constraints / K8s-native" → `.cursor/rules/infra-constraints.mdc`

Full list:
- `VISION.md`
- `docs/system-design/system_design.md`
- `docs/system-design/system_principles.md`
- `docs/system-design/platform_identity.md`
- `docs/safety/safety_model.md`
- `docs/safety/do_not_diagnose_rules.md`
- `.cursor/rules/wellbe-vision-guardrails.mdc`
- `.cursor/rules/audience-guardrails.mdc`
- `.cursor/rules/infra-constraints.mdc`

---

## Current behavior

What the code does today is [docs/current/capability-index.md](docs/current/capability-index.md). Intent, decisions, and the bible list above stay in their own files. The rule that tells an agent which file to read is `.cursor/rules/agent-context.mdc`.

