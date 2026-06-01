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
