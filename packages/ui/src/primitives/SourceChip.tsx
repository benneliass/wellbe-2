import { Icon } from "../Icon";
import type { Tone } from "./Chip";
import styles from "./SourceChip.module.css";

export type SourceType = "lab" | "note" | "doc" | "wearable" | "reported" | "research";

interface SourceMeta {
  icon: string;
  label: string;
  tone: Tone;
}

export const SOURCE_META: Record<SourceType, SourceMeta> = {
  lab: { icon: "flask-conical", label: "Lab result", tone: "teal" },
  note: { icon: "clipboard-list", label: "Clinical note", tone: "tealmid" },
  doc: { icon: "file-text", label: "Document", tone: "violet" },
  wearable: { icon: "heart-pulse", label: "Wearable", tone: "green" },
  reported: { icon: "message-circle", label: "You reported", tone: "amber" },
  research: { icon: "globe", label: "Research", tone: "neutral" },
};

export interface SourceChipProps {
  type?: SourceType;
}

/** Source-type pill used in evidence contexts. */
export function SourceChip({ type = "lab" }: SourceChipProps) {
  const meta = SOURCE_META[type] ?? SOURCE_META.lab;
  return (
    <span className={styles.source} data-tone={meta.tone}>
      <Icon name={meta.icon} size={14} />
      {meta.label}
    </span>
  );
}
