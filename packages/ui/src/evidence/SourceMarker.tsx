import { Icon } from "../Icon";
import { SOURCE_META } from "../primitives/SourceChip";
import {
  SOURCE_COMPONENT_ICON,
  SOURCE_COMPONENT_LABEL,
  cx,
  formatEvidenceDate,
  resolveDisplayLabel,
} from "./format";
import shared from "./shared.module.css";
import styles from "./SourceMarker.module.css";
import type { SourceComponent, SourceKind } from "./types";

export interface SourceMarkerProps {
  /** SourceRefV2.display_label. Raw ids are replaced by the component label. */
  displayLabel: string;
  /** SourceRefV2.component of the strongest source. */
  component?: SourceComponent;
  /** Chooses the kind icon; defaults to an icon for the component. */
  kind?: SourceKind;
  date?: string | Date;
  /** Total number of backing sources; extras show as "+N". */
  count?: number;
  /** Opens the EvidenceDrawer. When omitted the marker is static. */
  onOpen?: () => void;
  className?: string;
}

/**
 * Compact source indicator (WEL-144 §1). Shows the human display label, a kind
 * icon and an optional date; activates the evidence drawer when `onOpen` is set.
 */
export function SourceMarker({
  displayLabel,
  component = "c5",
  kind,
  date,
  count = 1,
  onOpen,
  className,
}: SourceMarkerProps) {
  const label = resolveDisplayLabel(displayLabel, component);
  const when = formatEvidenceDate(date);
  const icon = kind ? SOURCE_META[kind].icon : SOURCE_COMPONENT_ICON[component];
  const extra = Math.max(0, Math.floor(count) - 1);
  const external = component === "c16";

  const content = (
    <>
      <Icon name={icon} size={14} />
      <span className={shared.srOnly}>Source: </span>
      {external && (
        <span className={styles.external} aria-hidden="true">
          External
        </span>
      )}
      <span className={shared.label}>{label}</span>
      {when && (
        <>
          <span className={styles.sep} aria-hidden="true">
            ·
          </span>
          <time className={shared.meta} dateTime={when.iso}>
            {when.label}
          </time>
        </>
      )}
      {extra > 0 && (
        <span className={shared.meta}>
          +{extra}
          <span className={shared.srOnly}> more</span>
        </span>
      )}
      <span className={shared.srOnly}>, {SOURCE_COMPONENT_LABEL[component]}</span>
    </>
  );

  const classes = cx(shared.marker, styles.source, onOpen && shared.interactive, className);

  if (onOpen) {
    return (
      <button
        type="button"
        className={classes}
        data-component={component}
        aria-haspopup="dialog"
        onClick={onOpen}
      >
        {content}
        <span className={shared.srOnly}>. Open evidence</span>
      </button>
    );
  }

  return (
    <span className={classes} data-component={component}>
      {content}
    </span>
  );
}
