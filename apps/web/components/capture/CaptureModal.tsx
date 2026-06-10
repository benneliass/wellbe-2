"use client";

import { useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import { CAPTURE_TYPES } from "@/lib/meta";
import styles from "./CaptureModal.module.css";

export function CaptureModal({ onClose }: { onClose: () => void }) {
  const [type, setType] = useState("reported");

  const footer = (
    <>
      <span className={styles.note}>
        <Icon name="lock" size={13} />
        Saved privately to your memory
      </span>
      <div className={styles.footBtns}>
        <Button variant="tertiary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" icon="check" onClick={onClose}>
          Add to memory
        </Button>
      </div>
    </>
  );

  return (
    <Modal title="Capture" icon="plus-circle" onClose={onClose} footer={footer}>
      <div className={styles.label}>What are you capturing?</div>
      <div className={styles.types}>
        {CAPTURE_TYPES.map((t) => (
          <button
            key={t.id}
            type="button"
            className={styles.type}
            data-active={type === t.id || undefined}
            onClick={() => setType(t.id)}
          >
            <span className={styles.typeIcon}>
              <Icon name={t.icon} size={18} />
            </span>
            <span className={styles.typeText}>
              <b>{t.label}</b>
              <span>{t.hint}</span>
            </span>
            {type === t.id && <Icon name="check-circle-2" size={16} className={styles.check} />}
          </button>
        ))}
      </div>

      <div className={styles.field}>
        <label htmlFor="capture-desc">Description</label>
        <textarea id="capture-desc" placeholder="Describe what you noticed, in your own words…" rows={3} />
      </div>
      <div className={styles.fieldRow}>
        <div className={styles.field}>
          <label>When</label>
          <div className={styles.input}>
            <Icon name="calendar" size={15} />
            <span>Today, 9:24 AM</span>
          </div>
        </div>
        <div className={styles.field}>
          <label>Attach to thread</label>
          <div className={styles.input}>
            <Icon name="list" size={15} />
            <span>Lower back pain</span>
            <Icon name="chevron-down" size={15} className={styles.chev} />
          </div>
        </div>
      </div>
    </Modal>
  );
}
