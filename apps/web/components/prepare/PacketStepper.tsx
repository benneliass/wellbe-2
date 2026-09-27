"use client";

import { Icon } from "@wellbe/ui";
import styles from "./PacketStepper.module.css";

export type PacketStep = "choose" | "review" | "share";

export const PACKET_STEPS: ReadonlyArray<{ id: PacketStep; label: string; hint: string }> = [
  { id: "choose", label: "Choose", hint: "Concerns, questions, goals" },
  { id: "review", label: "Review", hint: "Check every item and its source" },
  { id: "share", label: "Share", hint: "Who, what they see, for how long" },
];

/**
 * Visible 3-step progress for the visit packet (ui_vision_implementation_prompt.md
 * "Visit Packet Builder"). Reached steps are revisitable; later steps unlock in order.
 */
export function PacketStepper({
  current,
  reachable,
  onSelect,
}: {
  current: PacketStep;
  /** Steps the person may jump to (already reached). */
  reachable: ReadonlySet<PacketStep>;
  onSelect: (step: PacketStep) => void;
}) {
  const currentIndex = PACKET_STEPS.findIndex((s) => s.id === current);
  return (
    <nav aria-label="Visit packet steps" className={styles.nav}>
      <ol className={styles.list}>
        {PACKET_STEPS.map((step, i) => {
          const state = i < currentIndex ? "done" : i === currentIndex ? "current" : "todo";
          const canGo = step.id !== current && reachable.has(step.id);
          const inner = (
            <>
              <span className={styles.dot} aria-hidden="true">
                {state === "done" ? <Icon name="check" size={12} /> : i + 1}
              </span>
              <span className={styles.text}>
                <b>
                  <span className={styles.srOnly}>Step {i + 1}: </span>
                  {step.label}
                </b>
                <span>{step.hint}</span>
              </span>
            </>
          );
          return (
            <li key={step.id} className={styles.item} data-state={state}>
              {canGo ? (
                <button type="button" className={styles.step} onClick={() => onSelect(step.id)}>
                  {inner}
                </button>
              ) : (
                <span
                  className={styles.step}
                  aria-current={state === "current" ? "step" : undefined}
                  aria-disabled={state === "todo" || undefined}
                >
                  {inner}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
