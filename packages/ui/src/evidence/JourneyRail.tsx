import type { ReactNode } from "react";
import { Icon } from "../Icon";
import type { StateToken } from "../tokens";
import { cx } from "./format";
import shared from "./shared.module.css";
import styles from "./JourneyRail.module.css";

/** C7 HealthThreadStatus (mirrors the api-client contract). */
export type HealthThreadStatus =
  | "draft"
  | "active_unresolved"
  | "waiting_for_result"
  | "referred"
  | "watchful_waiting"
  | "escalated"
  | "explained"
  | "chronic_monitoring"
  | "closed"
  | "reopened"
  | "archived";

export type JourneyStage =
  | "started"
  | "open"
  | "in_motion"
  | "needs_attention"
  | "understood"
  | "ongoing"
  | "closed"
  | "archived";

const STATUS_TO_STAGE: Record<HealthThreadStatus, JourneyStage> = {
  draft: "started",
  active_unresolved: "open",
  reopened: "open",
  waiting_for_result: "in_motion",
  referred: "in_motion",
  watchful_waiting: "in_motion",
  escalated: "needs_attention",
  explained: "understood",
  chronic_monitoring: "ongoing",
  closed: "closed",
  archived: "archived",
};

/** Map a C7 thread status to its Journey Rail stage (WEL-139 mapping table). */
export function mapThreadStatusToStage(status: HealthThreadStatus): JourneyStage {
  return STATUS_TO_STAGE[status];
}

export const JOURNEY_STAGE_LABELS: Record<JourneyStage, string> = {
  started: "Started",
  open: "Open",
  in_motion: "In motion",
  needs_attention: "Needs attention",
  understood: "Understood",
  ongoing: "Ongoing",
  closed: "Closed",
  archived: "Archived",
};

/** Plain wording for the precise C7 status, kept one step away from the stage. */
export const THREAD_STATUS_LABELS: Record<HealthThreadStatus, string> = {
  draft: "Not saved yet",
  active_unresolved: "Open and unresolved",
  reopened: "Picked back up",
  waiting_for_result: "Waiting for a result",
  referred: "Referred",
  watchful_waiting: "Watching and waiting",
  escalated: "Worth following up",
  explained: "Understood for now",
  chronic_monitoring: "Monitored over time",
  closed: "Closed",
  archived: "Archived",
};

const STAGE_ICON: Record<JourneyStage, string> = {
  started: "circle-help",
  open: "folder",
  in_motion: "clock",
  needs_attention: "info",
  understood: "check-circle-2",
  ongoing: "activity",
  closed: "check-circle-2",
  archived: "folder",
};

/**
 * The calm state tone for a stage (health-adaptive-safety-language.md). Never
 * returns `urgent`: that tone is reserved for C10-approved guidance.
 */
export function stageTone(stage: JourneyStage, actionDue = false): StateToken | null {
  if (stage === "needs_attention") return "needs_attention";
  if (stage === "open" && actionDue) return "needs_attention";
  if (stage === "in_motion") return "watch";
  if (stage === "understood" || stage === "ongoing" || stage === "closed") return "stable";
  return null;
}

/**
 * Traveled stages from a transition history, oldest first: consecutive repeats
 * collapse and the trailing entry is dropped when it is the current stage.
 * Only stages the thread actually entered are returned.
 */
export function traveledStages(history: readonly HealthThreadStatus[], current: HealthThreadStatus): JourneyStage[] {
  const out: JourneyStage[] = [];
  for (const status of history) {
    const stage = STATUS_TO_STAGE[status];
    if (out[out.length - 1] !== stage) out.push(stage);
  }
  if (out[out.length - 1] === STATUS_TO_STAGE[current]) out.pop();
  return out;
}

export interface JourneyRailProps {
  /** Current C7 status. */
  status: HealthThreadStatus;
  /** Statuses the thread has entered, oldest first (from transition history). */
  history?: readonly HealthThreadStatus[];
  /** "compact" for Home (current stage only), "full" for Thread Detail. */
  variant?: "compact" | "full";
  /** One-line "what changed since you last looked". */
  whatChanged?: ReactNode;
  /** For in-motion stages: what the thread is waiting on. */
  waitingOn?: string;
  /** Quiet "likely next" hint. Only shown when provided; never inferred. */
  likelyNext?: JourneyStage;
  /** The single next action (disclosure L2). */
  nextAction?: ReactNode;
  /** An action is due on an open thread; raises tone to needs_attention. */
  actionDue?: boolean;
  /** Makes stages activatable, e.g. to jump to that point in the timeline. */
  onSelectStage?: (stage: JourneyStage) => void;
  className?: string;
}

interface RailItem {
  stage: JourneyStage;
  position: "traveled" | "current" | "next";
  key: string;
}

/**
 * Journey Rail (WEL-139): where a Health Thread has been, where it is, and a quiet
 * hint of what may come next. Presentation of C7 state only; no percentages.
 */
export function JourneyRail({
  status,
  history = [],
  variant = "full",
  whatChanged,
  waitingOn,
  likelyNext,
  nextAction,
  actionDue = false,
  onSelectStage,
  className,
}: JourneyRailProps) {
  const current = STATUS_TO_STAGE[status];
  const tone = stageTone(current, actionDue);
  const statusLabel = THREAD_STATUS_LABELS[status];

  const items: RailItem[] =
    variant === "compact"
      ? [{ stage: current, position: "current", key: "current" }]
      : [
          ...traveledStages(history, status).map((stage, i) => ({
            stage,
            position: "traveled" as const,
            key: `t${i}`,
          })),
          { stage: current, position: "current", key: "current" },
          ...(likelyNext && likelyNext !== current
            ? [{ stage: likelyNext, position: "next" as const, key: "next" }]
            : []),
        ];

  const describe = (item: RailItem): string => {
    const label = JOURNEY_STAGE_LABELS[item.stage];
    if (item.position === "traveled") return `${label}, visited`;
    if (item.position === "next") return `${label}, likely next`;
    const parts = [`${label}, current stage`, statusLabel];
    if (current === "in_motion" && waitingOn) parts.push(`waiting on ${waitingOn}`);
    if (typeof whatChanged === "string") parts.push(whatChanged);
    return parts.join(". ");
  };

  return (
    <nav
      className={cx(styles.rail, className)}
      data-variant={variant}
      data-stage={current}
      data-state={tone ?? undefined}
      aria-label="Thread journey"
    >
      <ol className={styles.stages}>
        {items.map((item) => {
          const isCurrent = item.position === "current";
          const icon = item.position === "traveled" ? "check" : STAGE_ICON[item.stage];
          const body = (
            <>
              <span className={styles.node} aria-hidden="true">
                <Icon name={icon} size={14} />
              </span>
              <span className={styles.text} aria-hidden="true">
                <span className={styles.stageLabel}>{JOURNEY_STAGE_LABELS[item.stage]}</span>
                {isCurrent && <span className={styles.status}>{statusLabel}</span>}
                {isCurrent && current === "in_motion" && waitingOn && (
                  <span className={styles.status}>Waiting on {waitingOn}</span>
                )}
                {item.position === "next" && <span className={styles.status}>Likely next</span>}
              </span>
              <span className={shared.srOnly}>{describe(item)}</span>
            </>
          );
          return (
            <li
              key={item.key}
              className={styles.stage}
              data-position={item.position}
              data-stage={item.stage}
              aria-current={isCurrent ? "step" : undefined}
            >
              {onSelectStage && item.position !== "next" ? (
                <button type="button" className={styles.stageButton} onClick={() => onSelectStage(item.stage)}>
                  {body}
                </button>
              ) : (
                <span className={cx(styles.stageButton, shared.focusable)} tabIndex={variant === "full" ? 0 : undefined}>
                  {body}
                </span>
              )}
            </li>
          );
        })}
      </ol>
      {(whatChanged || nextAction) && (
        <div className={styles.footer}>
          {whatChanged && (
            <div className={styles.whatChanged}>
              <span className={styles.footLabel}>What changed</span>
              <span>{whatChanged}</span>
            </div>
          )}
          {nextAction && <div className={styles.nextAction}>{nextAction}</div>}
        </div>
      )}
    </nav>
  );
}
