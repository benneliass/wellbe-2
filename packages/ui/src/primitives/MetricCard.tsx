import { Icon } from "../Icon";
import type { Tone } from "./Chip";
import styles from "./MetricCard.module.css";

export interface MetricDelta {
  /** Display text, e.g. "12.5%" or "+25m". */
  value: string;
  /** Arrow direction. */
  dir: "up" | "down";
  /**
   * Whether the change reads as positive/negative for the user. Defaults from
   * `dir` (up = positive, down = negative); set explicitly when the meaning is
   * inverted (e.g. a falling pain score is positive).
   */
  intent?: "positive" | "negative" | "neutral";
}

export interface MetricCardProps {
  /** Short metric name, e.g. "Avg sleep". */
  label: string;
  /** The value itself, e.g. "76%" or "1,248". */
  value: string;
  /** Optional unit appended next to the value, e.g. "mg/L". */
  unit?: string;
  /** Leading icon (kebab-case lucide name) in a tinted circle. */
  icon?: string;
  /** Icon tint tone. */
  tone?: Tone;
  delta?: MetricDelta;
  /** Calm context line beside the delta, e.g. "vs last 30 days". */
  deltaNote?: string;
}

/** Single metric tile: label, value (+unit), and an optional delta with calm context. */
export function MetricCard({ label, value, unit, icon, tone = "teal", delta, deltaNote }: MetricCardProps) {
  const intent = delta ? (delta.intent ?? (delta.dir === "up" ? "positive" : "negative")) : undefined;
  return (
    <div className={styles.metric}>
      {icon && (
        <span className={styles.icon} data-tone={tone}>
          <Icon name={icon} size={18} />
        </span>
      )}
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>
        {value}
        {unit && <em className={styles.unit}>{unit}</em>}
      </div>
      {delta && (
        <div className={styles.delta} data-intent={intent}>
          <Icon name={delta.dir === "up" ? "trending-up" : "trending-down"} size={13} />
          {delta.value}
          {deltaNote && <span className={styles.note}>{deltaNote}</span>}
        </div>
      )}
    </div>
  );
}
