/**
 * Typed token references for the WellBe design system.
 * The calm state token set is the contract from
 * docs/implementation/ui/health-adaptive-safety-language.md.
 *
 * `urgent` may ONLY be applied from a C10-approved render decision (route_urgent).
 * The client may never escalate to `urgent` on its own — fall back to `needs_attention`.
 */

export type StateToken = "stable" | "watch" | "needs_attention" | "urgent";

export interface StateTokenMeta {
  /** Plain, calm, non-diagnostic label. */
  label: string;
  /** CSS custom properties for tint + foreground. */
  tintVar: string;
  fgVar: string;
  /** Whether this token may be set only via a Safety Gate (C10) approval. */
  safetyGated: boolean;
}

export const STATE_TOKENS: Record<StateToken, StateTokenMeta> = {
  stable: {
    label: "Steady",
    tintVar: "--wb-state-stable-tint",
    fgVar: "--wb-state-stable-fg",
    safetyGated: false,
  },
  watch: {
    label: "Worth watching",
    tintVar: "--wb-state-watch-tint",
    fgVar: "--wb-state-watch-fg",
    safetyGated: false,
  },
  needs_attention: {
    label: "Needs attention",
    tintVar: "--wb-state-attention-tint",
    fgVar: "--wb-state-attention-fg",
    safetyGated: false,
  },
  urgent: {
    label: "Worth urgent attention",
    tintVar: "--wb-state-urgent-tint",
    fgVar: "--wb-state-urgent-fg",
    safetyGated: true,
  },
};

/** The disclosure levels from docs/implementation/ui/progressive-disclosure-contract.md. */
export type DisclosureLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

/** Evidence provenance tokens (`evidence.*` in ui_vision.md), defined in tokens.css. */
export type EvidenceToken = "patient_entered" | "ai_summarized" | "clinician_reviewed" | "corrected";

export interface EvidenceTokenMeta {
  label: string;
  tintVar: string;
  fgVar: string;
  borderVar: string;
}

export const EVIDENCE_TOKENS: Record<EvidenceToken, EvidenceTokenMeta> = {
  patient_entered: {
    label: "Your words",
    tintVar: "--wb-evidence-patient-entered-tint",
    fgVar: "--wb-evidence-patient-entered-fg",
    borderVar: "--wb-evidence-patient-entered-border",
  },
  ai_summarized: {
    label: "WellBe summary",
    tintVar: "--wb-evidence-ai-summarized-tint",
    fgVar: "--wb-evidence-ai-summarized-fg",
    borderVar: "--wb-evidence-ai-summarized-border",
  },
  clinician_reviewed: {
    label: "Clinician-reviewed",
    tintVar: "--wb-evidence-clinician-reviewed-tint",
    fgVar: "--wb-evidence-clinician-reviewed-fg",
    borderVar: "--wb-evidence-clinician-reviewed-border",
  },
  corrected: {
    label: "Corrected",
    tintVar: "--wb-evidence-corrected-tint",
    fgVar: "--wb-evidence-corrected-fg",
    borderVar: "--wb-evidence-corrected-border",
  },
};
