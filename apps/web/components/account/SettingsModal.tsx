"use client";

import { useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import styles from "./AccountModals.module.css";

interface ToggleSetting {
  id: string;
  icon: string;
  main: string;
  sub: string;
  default: boolean;
}

interface SettingsSection {
  id: string;
  title: string;
  items: ToggleSetting[];
}

/**
 * SETTINGS — local-state prototype.
 *
 * Toggles hold UI state only; nothing is persisted yet. Defaults encode the
 * WellBe stance: sharing always needs the user's approval, and cross-patient
 * comparison stays OFF until the individual opts in.
 */
const SECTIONS: SettingsSection[] = [
  {
    id: "privacy",
    title: "Privacy & sharing",
    items: [
      {
        id: "approve-shares",
        icon: "shield-check",
        main: "Require my approval for every share",
        sub: "Nothing leaves your workspace without you confirming it.",
        default: true,
      },
      {
        id: "cross-patient",
        icon: "users",
        main: "Cross-patient comparison",
        sub: "Compare against others with similar conditions. Off until you turn it on.",
        default: false,
      },
    ],
  },
  {
    id: "notifications",
    title: "Notifications",
    items: [
      {
        id: "result-alerts",
        icon: "bell",
        main: "Result-ready alerts",
        sub: "Tell me when a new result lands or a thread needs attention.",
        default: true,
      },
      {
        id: "delta-digest",
        icon: "activity",
        main: "Weekly delta digest",
        sub: "A calm summary of what changed in your health this week.",
        default: true,
      },
    ],
  },
  {
    id: "display",
    title: "Display",
    items: [
      {
        id: "reduce-motion",
        icon: "sparkles",
        main: "Reduce motion",
        sub: "Minimize animations across the app.",
        default: false,
      },
    ],
  },
];

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const [values, setValues] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(SECTIONS.flatMap((s) => s.items.map((i) => [i.id, i.default]))),
  );

  const toggle = (id: string) => setValues((v) => ({ ...v, [id]: !v[id] }));

  const footer = (
    <>
      <span className={styles.note} style={{ border: "none", background: "none", padding: 0 }}>
        <Icon name="lock" size={13} />
        Saved to your workspace only
      </span>
      <Button variant="primary" icon="check" onClick={onClose}>
        Done
      </Button>
    </>
  );

  return (
    <Modal title="Settings" icon="settings" onClose={onClose} footer={footer}>
      {SECTIONS.map((section) => (
        <div key={section.id} className={styles.section}>
          <div className={styles.sectionTitle}>{section.title}</div>
          {section.items.map((item) => {
            const on = values[item.id];
            return (
              <div key={item.id} className={styles.row}>
                <span className={styles.rowIcon}>
                  <Icon name={item.icon} size={18} />
                </span>
                <span className={styles.rowText}>
                  <span className={styles.rowMain}>{item.main}</span>
                  <span className={styles.rowSub}>{item.sub}</span>
                </span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={on}
                  aria-label={item.main}
                  className={styles.toggle}
                  onClick={() => toggle(item.id)}
                >
                  <span className={styles.toggleKnob} />
                </button>
              </div>
            );
          })}
        </div>
      ))}
    </Modal>
  );
}
