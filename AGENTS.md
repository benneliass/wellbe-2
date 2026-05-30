# Agent Instructions

## Bible Files — Require Explicit User Approval to Modify

The following files are canonical truth documents. No agent may edit, rename, move, or delete them without explicit user approval. See `.cursor/rules/doc-governance.mdc` for the full doc re-eval protocol.

- `VISION.md`
- `docs/system-design/system_design.md`
- `docs/system-design/system_principles.md`
- `docs/system-design/platform_identity.md`
- `docs/safety/safety_model.md`
- `docs/safety/do_not_diagnose_rules.md`
- `.cursor/rules/wellbe-vision-guardrails.mdc`
- `.cursor/rules/audience-guardrails.mdc`

---

## Always Commit Work

After completing any meaningful change, always create a git commit. Never leave work uncommitted.

### When to Commit

- After completing a feature, fix, or refactor
- After creating or deleting files
- After updating configuration or dependencies
- Before switching to a different task

### Commit Message Format

Use the imperative mood and be specific:

```
# ✅ GOOD
git commit -m "Add user authentication flow"
git commit -m "Fix null pointer in payment handler"
git commit -m "Remove deprecated API endpoints"

# ❌ BAD
git commit -m "changes"
git commit -m "fix"
git commit -m "wip"
```

### Rules

- Stage all relevant files before committing (`git add`)
- Never use `--no-verify` to skip hooks unless explicitly asked
- Never force-push to `main`/`master`
- One logical change per commit — don't batch unrelated changes
