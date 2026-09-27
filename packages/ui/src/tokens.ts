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
