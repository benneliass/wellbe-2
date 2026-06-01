import type { CSSProperties } from "react";
import { STATE_TOKENS, type StateToken } from "../tokens";

const ICON: Record<StateToken, string> = {
  stable: "●",
  watch: "◐",
  needs_attention: "▲",
  urgent: "◆",
};

export interface StatePillProps {
  state: StateToken;
  /** Optional override label; defaults to the calm token label. */
  label?: string;
}

/**
 * A small state indicator. Carries meaning via icon + text, never color alone
 * (per the never-alarm rule). `urgent` styling should only be passed when a
 * C10-approved render decision authorized it.
 */
export function StatePill({ state, label }: StatePillProps) {
  const meta = STATE_TOKENS[state];
  const style: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--wb-space-1)",
    padding: "2px var(--wb-space-2)",
    borderRadius: "999px",
    fontSize: "var(--wb-text-xs)",
    fontWeight: 600,
    background: `var(${meta.tintVar})`,
    color: `var(${meta.fgVar})`,
  };
  return (
    <span style={style} role="status">
      <span aria-hidden="true">{ICON[state]}</span>
      <span>{label ?? meta.label}</span>
    </span>
  );
}
