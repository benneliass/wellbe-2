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

/** Solid `state.*` mark colors (rail, dot, icon, border) for each state token. */
export const STATE_MARK_VARS: Record<StateToken, string> = {
  stable: "--state-stable",
  watch: "--state-watch",
  needs_attention: "--state-needs-attention",
  urgent: "--state-urgent",
};

/** Font family CSS variables: Figtree headings, Noto Sans body, mono for code/ids only. */
export const FONT_VARS = {
  heading: "--font-heading",
  body: "--font-body",
  mono: "--font-mono",
} as const;

/** Type scale CSS variables. Body copy >= 16px; meta text >= 14px. */
export const TYPE_SCALE_VARS = {
  display: "--text-display",
  h1: "--text-h1",
  h2: "--text-h2",
  h3: "--text-h3",
  h4: "--text-h4",
  body: "--text-body",
  sm: "--text-sm",
  xs: "--text-xs",
  "2xs": "--text-2xs",
} as const;

/** Motion durations (150-300ms); all collapse to 0ms under prefers-reduced-motion. */
export const MOTION_VARS = {
  fast: "--wb-motion-fast",
  base: "--wb-motion-base",
  slow: "--wb-motion-slow",
  ease: "--wb-ease",
} as const;

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
