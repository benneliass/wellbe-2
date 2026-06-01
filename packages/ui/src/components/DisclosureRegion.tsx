import { useId, useState, type CSSProperties, type ReactNode } from "react";
import type { DisclosureLevel } from "../tokens";

export interface DisclosureRegionProps {
  level: DisclosureLevel;
  /** Always-visible summary (the shallow disclosure level). */
  summary: ReactNode;
  /** Deeper content, revealed only on explicit user intent. */
  children?: ReactNode;
  /** Only L0–L2 should default to open. */
  defaultOpen?: boolean;
  expandLabel?: string;
}

/**
 * Shared progressive-disclosure primitive.
 * Implements docs/implementation/ui/progressive-disclosure-contract.md:
 * summary-first, deeper levels revealed by explicit affordance only.
 */
export function DisclosureRegion({
  level,
  summary,
  children,
  defaultOpen = false,
  expandLabel = "Show more",
}: DisclosureRegionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const hasMore = Boolean(children);

  const wrap: CSSProperties = {
    border: "1px solid var(--wb-border)",
    borderRadius: "var(--wb-radius)",
    background: "var(--wb-surface)",
    padding: "var(--wb-space-3)",
  };
  const button: CSSProperties = {
    marginTop: "var(--wb-space-2)",
    background: "transparent",
    border: "none",
    color: "var(--wb-accent)",
    font: "inherit",
    fontSize: "var(--wb-text-sm)",
    fontWeight: 600,
    cursor: "pointer",
    padding: 0,
  };
  const panel: CSSProperties = {
    marginTop: "var(--wb-space-3)",
    transition: `opacity var(--wb-motion-base) var(--wb-ease)`,
  };

  return (
    <section style={wrap} data-disclosure-level={level}>
      <div>{summary}</div>
      {hasMore && (
        <>
          <button
            type="button"
            style={button}
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Show less" : expandLabel}
          </button>
          {open && (
            <div id={panelId} style={panel}>
              {children}
            </div>
          )}
        </>
      )}
    </section>
  );
}
