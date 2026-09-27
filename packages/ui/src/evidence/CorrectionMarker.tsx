import { Icon } from "../Icon";
import { cx, formatEvidenceDate } from "./format";
import shared from "./shared.module.css";
import styles from "./CorrectionMarker.module.css";
import type { CorrectionInfo } from "./types";

export interface CorrectionMarkerProps extends Partial<CorrectionInfo> {
  /** Opens correction history when there is no `priorVersionHref`. */
  onOpenHistory?: () => void;
  className?: string;
}

const STATE_LABEL = {
  corrected: "Corrected",
  superseded: "Replaced by a correction",
} as const;

/**
 * Marks a claim that carries a C11 correction overlay (WEL-144 §4). The original
 * is always preserved, so the marker says so and links to the earlier version.
 * Renders nothing when there is no correction state.
 */
export function CorrectionMarker({
  state,
  correctedBy,
  correctedAt,
  priorVersionHref,
  onOpenHistory,
  className,
}: CorrectionMarkerProps) {
  if (!state) return null;
  const when = formatEvidenceDate(correctedAt);
  const by = correctedBy?.trim();

  return (
    <span className={cx(styles.wrap, className)} data-correction={state}>
      <span className={shared.marker} data-evidence="corrected">
        <Icon name={state === "corrected" ? "pencil" : "rotate-ccw"} size={14} />
        <span>{STATE_LABEL[state]}</span>
        {by && <span className={shared.meta}>by {by}</span>}
        {when && (
          <time className={shared.meta} dateTime={when.iso}>
            <span aria-hidden="true">· </span>
            {when.label}
          </time>
        )}
        <span className={shared.meta}>
          <span aria-hidden="true">· </span>original kept
        </span>
      </span>
      {priorVersionHref ? (
        <a className={shared.link} href={priorVersionHref}>
          View earlier version
        </a>
      ) : onOpenHistory ? (
        <button type="button" className={shared.link} onClick={onOpenHistory}>
          View earlier version
        </button>
      ) : null}
    </span>
  );
}
