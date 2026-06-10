"use client";

import { useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import type { Thread } from "@/lib/types";
import styles from "./ShareSheet.module.css";

const SCOPES = [
  { id: "summary", label: "Summary only", hint: "Status, question, and what changed" },
  { id: "evidence", label: "Summary + evidence", hint: "Includes sources and confidence" },
  { id: "full", label: "Full thread", hint: "Everything, including your notes" },
];

export function ShareSheet({ thread, onClose }: { thread: Thread; onClose: () => void }) {
  const [scope, setScope] = useState("summary");

  const footer = (
    <>
      <span className={styles.note}>
        <Icon name="shield-check" size={13} />
        You can revoke this access anytime
      </span>
      <div className={styles.footBtns}>
        <Button variant="tertiary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" icon="share" onClick={onClose}>
          Grant access
        </Button>
      </div>
    </>
  );

  return (
    <Modal title="Share thread" icon="share" onClose={onClose} wide footer={footer}>
      <div className={styles.banner}>
        <Icon name="lock" size={16} />
        <span>
          You are the data controller. Sharing creates a <b>scoped, revocable grant</b> — the
          recipient sees only what you choose.
        </span>
      </div>

      <div className={styles.label}>Share &ldquo;{thread.title}&rdquo; with</div>
      <div className={`${styles.input} ${styles.inputLg}`}>
        <Icon name="circle-user" size={16} />
        <span>Dr. Jane Smith · City Health</span>
      </div>

      <div className={`${styles.label} ${styles.labelSpaced}`}>How much to share</div>
      <div className={styles.scopes}>
        {SCOPES.map((sc) => (
          <button
            key={sc.id}
            type="button"
            className={styles.scope}
            data-active={scope === sc.id || undefined}
            onClick={() => setScope(sc.id)}
          >
            <span className={styles.radio} data-on={scope === sc.id || undefined} />
            <span className={styles.scopeText}>
              <b>{sc.label}</b>
              <span>{sc.hint}</span>
            </span>
          </button>
        ))}
      </div>

      <div className={styles.fieldRow}>
        <div className={styles.field}>
          <label>Access expires</label>
          <div className={styles.input}>
            <Icon name="clock" size={15} />
            <span>In 30 days</span>
            <Icon name="chevron-down" size={15} className={styles.chev} />
          </div>
        </div>
        <div className={styles.field}>
          <label>Permission</label>
          <div className={styles.input}>
            <Icon name="eye" size={15} />
            <span>View only</span>
            <Icon name="chevron-down" size={15} className={styles.chev} />
          </div>
        </div>
      </div>
    </Modal>
  );
}
